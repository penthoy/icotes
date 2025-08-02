"""
Workspace Service for icpy Backend
Manages application state including open files, active terminals, panels, and user preferences
Provides workspace initialization, persistence, and switching capabilities
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import aiofiles
from collections import defaultdict

# Internal imports
from ..core.message_broker import MessageBroker, get_message_broker
from ..core.connection_manager import ConnectionManager, get_connection_manager

logger = logging.getLogger(__name__)


class PanelType(Enum):
    """Types of panels in the workspace"""
    EDITOR = "editor"
    TERMINAL = "terminal"
    FILE_EXPLORER = "file_explorer"
    OUTPUT = "output"
    SEARCH = "search"
    EXTENSION = "extension"
    CUSTOM = "custom"


class PanelState(Enum):
    """States of a panel"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    CLOSED = "closed"


@dataclass
class PanelInfo:
    """Information about a workspace panel"""
    panel_id: str
    panel_type: PanelType
    title: str
    state: PanelState = PanelState.INACTIVE
    position: Dict[str, Any] = field(default_factory=dict)
    size: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'panel_id': self.panel_id,
            'panel_type': self.panel_type.value,
            'title': self.title,
            'state': self.state.value,
            'position': self.position,
            'size': self.size,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PanelInfo':
        """Create from dictionary"""
        return cls(
            panel_id=data['panel_id'],
            panel_type=PanelType(data['panel_type']),
            title=data['title'],
            state=PanelState(data['state']),
            position=data.get('position', {}),
            size=data.get('size', {}),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at', time.time()),
            last_accessed=data.get('last_accessed', time.time())
        )


@dataclass
class FileInfo:
    """Information about an open file"""
    file_path: str
    file_name: str
    is_dirty: bool = False
    is_temporary: bool = False
    cursor_position: Dict[str, Any] = field(default_factory=dict)
    selection: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    opened_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'file_path': self.file_path,
            'file_name': self.file_name,
            'is_dirty': self.is_dirty,
            'is_temporary': self.is_temporary,
            'cursor_position': self.cursor_position,
            'selection': self.selection,
            'metadata': self.metadata,
            'opened_at': self.opened_at,
            'last_accessed': self.last_accessed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileInfo':
        """Create from dictionary"""
        return cls(
            file_path=data['file_path'],
            file_name=data['file_name'],
            is_dirty=data.get('is_dirty', False),
            is_temporary=data.get('is_temporary', False),
            cursor_position=data.get('cursor_position', {}),
            selection=data.get('selection', {}),
            metadata=data.get('metadata', {}),
            opened_at=data.get('opened_at', time.time()),
            last_accessed=data.get('last_accessed', time.time())
        )


@dataclass
class TerminalInfo:
    """Information about a terminal session"""
    terminal_id: str
    title: str
    working_directory: str
    shell: str = "/bin/bash"
    environment: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'terminal_id': self.terminal_id,
            'title': self.title,
            'working_directory': self.working_directory,
            'shell': self.shell,
            'environment': self.environment,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TerminalInfo':
        """Create from dictionary"""
        return cls(
            terminal_id=data['terminal_id'],
            title=data['title'],
            working_directory=data['working_directory'],
            shell=data.get('shell', '/bin/bash'),
            environment=data.get('environment', {}),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at', time.time()),
            last_accessed=data.get('last_accessed', time.time())
        )


@dataclass
class WorkspaceLayout:
    """Layout configuration for the workspace"""
    layout_id: str
    name: str
    panels: List[PanelInfo] = field(default_factory=list)
    active_panel_id: Optional[str] = None
    layout_config: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'layout_id': self.layout_id,
            'name': self.name,
            'panels': [panel.to_dict() for panel in self.panels],
            'active_panel_id': self.active_panel_id,
            'layout_config': self.layout_config,
            'created_at': self.created_at,
            'last_used': self.last_used
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkspaceLayout':
        """Create from dictionary"""
        return cls(
            layout_id=data['layout_id'],
            name=data['name'],
            panels=[PanelInfo.from_dict(panel_data) for panel_data in data.get('panels', [])],
            active_panel_id=data.get('active_panel_id'),
            layout_config=data.get('layout_config', {}),
            created_at=data.get('created_at', time.time()),
            last_used=data.get('last_used', time.time())
        )


@dataclass
class WorkspaceState:
    """Complete workspace state"""
    workspace_id: str
    name: str
    root_path: str
    
    # Files and panels
    open_files: Dict[str, FileInfo] = field(default_factory=dict)
    panels: Dict[str, PanelInfo] = field(default_factory=dict)
    terminals: Dict[str, TerminalInfo] = field(default_factory=dict)
    
    # Layout and UI state
    current_layout: Optional[WorkspaceLayout] = None
    saved_layouts: Dict[str, WorkspaceLayout] = field(default_factory=dict)
    active_file_path: Optional[str] = None
    active_panel_id: Optional[str] = None
    
    # Configuration
    preferences: Dict[str, Any] = field(default_factory=dict)
    recent_files: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workspace_id': self.workspace_id,
            'name': self.name,
            'root_path': self.root_path,
            'open_files': {path: file_info.to_dict() for path, file_info in self.open_files.items()},
            'panels': {panel_id: panel.to_dict() for panel_id, panel in self.panels.items()},
            'terminals': {term_id: term.to_dict() for term_id, term in self.terminals.items()},
            'current_layout': self.current_layout.to_dict() if self.current_layout else None,
            'saved_layouts': {layout_id: layout.to_dict() for layout_id, layout in self.saved_layouts.items()},
            'active_file_path': self.active_file_path,
            'active_panel_id': self.active_panel_id,
            'preferences': self.preferences,
            'recent_files': self.recent_files,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkspaceState':
        """Create from dictionary"""
        return cls(
            workspace_id=data['workspace_id'],
            name=data['name'],
            root_path=data['root_path'],
            open_files={path: FileInfo.from_dict(file_data) for path, file_data in data.get('open_files', {}).items()},
            panels={panel_id: PanelInfo.from_dict(panel_data) for panel_id, panel_data in data.get('panels', {}).items()},
            terminals={term_id: TerminalInfo.from_dict(term_data) for term_id, term_data in data.get('terminals', {}).items()},
            current_layout=WorkspaceLayout.from_dict(data['current_layout']) if data.get('current_layout') else None,
            saved_layouts={layout_id: WorkspaceLayout.from_dict(layout_data) for layout_id, layout_data in data.get('saved_layouts', {}).items()},
            active_file_path=data.get('active_file_path'),
            active_panel_id=data.get('active_panel_id'),
            preferences=data.get('preferences', {}),
            recent_files=data.get('recent_files', []),
            created_at=data.get('created_at', time.time()),
            last_accessed=data.get('last_accessed', time.time()),
            metadata=data.get('metadata', {})
        )


class WorkspaceService:
    """
    Workspace Service manages application state including open files, terminals, panels, and user preferences
    Provides workspace initialization, persistence, and switching capabilities
    """
    
    def __init__(self, 
                 message_broker: Optional[MessageBroker] = None,
                 connection_manager: Optional[ConnectionManager] = None,
                 workspace_dir: Optional[str] = None):
        self.message_broker = message_broker
        self.connection_manager = connection_manager
        self.workspace_dir = workspace_dir or os.path.expanduser("~/.icpy/workspaces")
        
        # Current workspace state
        self.current_workspace: Optional[WorkspaceState] = None
        self.workspace_cache: Dict[str, WorkspaceState] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Statistics
        self.stats = {
            'workspace_switches': 0,
            'files_opened': 0,
            'files_closed': 0,
            'panels_created': 0,
            'panels_closed': 0,
            'terminals_created': 0,
            'terminals_closed': 0,
            'layout_saves': 0,
            'state_saves': 0
        }
        
        # Ensure workspace directory exists
        os.makedirs(self.workspace_dir, exist_ok=True)
    
    async def initialize(self):
        """Initialize the workspace service"""
        if self.message_broker is None:
            self.message_broker = await get_message_broker()
        
        if self.connection_manager is None:
            self.connection_manager = await get_connection_manager()
        
        # Subscribe to relevant events
        await self.message_broker.subscribe('workspace.*', self._handle_workspace_event)
        await self.message_broker.subscribe('file.*', self._handle_file_event)
        await self.message_broker.subscribe('terminal.*', self._handle_terminal_event)
        await self.message_broker.subscribe('panel.*', self._handle_panel_event)
        
        logger.info("Workspace service initialized")
    
    async def shutdown(self):
        """Shutdown the workspace service"""
        # Save current workspace state
        if self.current_workspace:
            await self.save_workspace_state()
        
        # Unsubscribe from events
        await self.message_broker.unsubscribe('workspace.*', self._handle_workspace_event)
        await self.message_broker.unsubscribe('file.*', self._handle_file_event)
        await self.message_broker.unsubscribe('terminal.*', self._handle_terminal_event)
        await self.message_broker.unsubscribe('panel.*', self._handle_panel_event)
        
        logger.info("Workspace service shutdown")
    
    # Workspace Management
    async def create_workspace(self, name: str, root_path: str, 
                             workspace_id: Optional[str] = None) -> WorkspaceState:
        """Create a new workspace"""
        if workspace_id is None:
            workspace_id = str(uuid.uuid4())
        
        # Create default layout
        default_layout = WorkspaceLayout(
            layout_id=str(uuid.uuid4()),
            name="Default Layout",
            panels=[],
            layout_config={
                "type": "default",
                "split": "horizontal",
                "sizes": [50, 50]
            }
        )
        
        workspace = WorkspaceState(
            workspace_id=workspace_id,
            name=name,
            root_path=root_path,
            current_layout=default_layout,
            saved_layouts={default_layout.layout_id: default_layout},
            preferences={
                "theme": "dark",
                "font_size": 14,
                "word_wrap": True,
                "auto_save": True,
                "tab_size": 2
            }
        )
        
        # Save to disk
        await self._save_workspace_to_disk(workspace)
        
        # Cache the workspace
        self.workspace_cache[workspace_id] = workspace
        
        # Publish event
        await self.message_broker.publish('workspace.created', {
            'workspace_id': workspace_id,
            'name': name,
            'root_path': root_path
        })
        
        self.stats['workspace_switches'] += 1
        logger.info(f"Created workspace: {name} ({workspace_id})")
        
        return workspace
    
    async def load_workspace(self, workspace_id: str) -> Optional[WorkspaceState]:
        """Load a workspace by ID"""
        # Check cache first
        if workspace_id in self.workspace_cache:
            return self.workspace_cache[workspace_id]
        
        # Load from disk
        workspace_file = os.path.join(self.workspace_dir, f"{workspace_id}.json")
        if not os.path.exists(workspace_file):
            return None
        
        try:
            async with aiofiles.open(workspace_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                workspace = WorkspaceState.from_dict(data)
                
                # Cache the workspace
                self.workspace_cache[workspace_id] = workspace
                
                logger.info(f"Loaded workspace: {workspace.name} ({workspace_id})")
                return workspace
                
        except Exception as e:
            logger.error(f"Error loading workspace {workspace_id}: {e}")
            return None
    
    async def switch_workspace(self, workspace_id: str) -> bool:
        """Switch to a different workspace"""
        # Save current workspace state
        if self.current_workspace:
            await self.save_workspace_state()
        
        # Load new workspace
        workspace = await self.load_workspace(workspace_id)
        if not workspace:
            return False
        
        # Update current workspace
        self.current_workspace = workspace
        workspace.last_accessed = time.time()
        
        # Publish event
        await self.message_broker.publish('workspace.switched', {
            'workspace_id': workspace_id,
            'workspace_name': workspace.name,
            'root_path': workspace.root_path
        })
        
        self.stats['workspace_switches'] += 1
        logger.info(f"Switched to workspace: {workspace.name} ({workspace_id})")
        
        return True
    
    async def get_workspace_list(self) -> List[Dict[str, Any]]:
        """Get list of all workspaces"""
        workspaces = []
        
        if not os.path.exists(self.workspace_dir):
            return workspaces
        
        for filename in os.listdir(self.workspace_dir):
            if filename.endswith('.json'):
                workspace_id = filename[:-5]  # Remove .json extension
                workspace = await self.load_workspace(workspace_id)
                if workspace:
                    workspaces.append({
                        'workspace_id': workspace_id,
                        'name': workspace.name,
                        'root_path': workspace.root_path,
                        'last_accessed': workspace.last_accessed,
                        'created_at': workspace.created_at
                    })
        
        # Sort by last accessed
        workspaces.sort(key=lambda x: x['last_accessed'], reverse=True)
        return workspaces
    
    async def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace"""
        workspace_file = os.path.join(self.workspace_dir, f"{workspace_id}.json")
        
        try:
            if os.path.exists(workspace_file):
                os.remove(workspace_file)
            
            # Remove from cache
            if workspace_id in self.workspace_cache:
                del self.workspace_cache[workspace_id]
            
            # If this was the current workspace, clear it
            if self.current_workspace and self.current_workspace.workspace_id == workspace_id:
                self.current_workspace = None
            
            # Publish event
            await self.message_broker.publish('workspace.deleted', {
                'workspace_id': workspace_id
            })
            
            logger.info(f"Deleted workspace: {workspace_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting workspace {workspace_id}: {e}")
            return False
    
    async def save_workspace_state(self) -> bool:
        """Save current workspace state to disk"""
        if not self.current_workspace:
            return False
        
        self.current_workspace.last_accessed = time.time()
        
        try:
            await self._save_workspace_to_disk(self.current_workspace)
            
            # Publish event
            await self.message_broker.publish('workspace.state_saved', {
                'workspace_id': self.current_workspace.workspace_id,
                'timestamp': time.time()
            })
            
            self.stats['state_saves'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error saving workspace state: {e}")
            return False
    
    async def _save_workspace_to_disk(self, workspace: WorkspaceState):
        """Save workspace to disk"""
        workspace_file = os.path.join(self.workspace_dir, f"{workspace.workspace_id}.json")
        
        async with aiofiles.open(workspace_file, 'w') as f:
            await f.write(json.dumps(workspace.to_dict(), indent=2))
    
    # File Management
    async def open_file(self, file_path: str, panel_id: Optional[str] = None) -> bool:
        """Open a file in the workspace"""
        if not self.current_workspace:
            return False
        
        # For testing, create file if it doesn't exist
        if not os.path.exists(file_path):
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write("")
            except Exception as e:
                logger.error(f"Failed to create file {file_path}: {e}")
                return False
        
        file_name = os.path.basename(file_path)
        
        # Create file info
        file_info = FileInfo(
            file_path=file_path,
            file_name=file_name,
            metadata={'panel_id': panel_id} if panel_id else {}
        )
        
        # Add to workspace
        self.current_workspace.open_files[file_path] = file_info
        self.current_workspace.active_file_path = file_path
        
        # Add to recent files
        if file_path in self.current_workspace.recent_files:
            self.current_workspace.recent_files.remove(file_path)
        self.current_workspace.recent_files.insert(0, file_path)
        
        # Keep only 20 recent files
        self.current_workspace.recent_files = self.current_workspace.recent_files[:20]
        
        # Publish event
        await self.message_broker.publish('workspace.file_opened', {
            'workspace_id': self.current_workspace.workspace_id,
            'file_path': file_path,
            'file_name': file_name,
            'panel_id': panel_id
        })
        
        self.stats['files_opened'] += 1
        return True
    
    async def close_file(self, file_path: str) -> bool:
        """Close a file"""
        if not self.current_workspace or file_path not in self.current_workspace.open_files:
            return False
        
        file_info = self.current_workspace.open_files[file_path]
        
        # Remove from workspace
        del self.current_workspace.open_files[file_path]
        
        # If this was the active file, clear it
        if self.current_workspace.active_file_path == file_path:
            # Set to the most recent file if available
            if self.current_workspace.recent_files:
                for recent_file in self.current_workspace.recent_files:
                    if recent_file in self.current_workspace.open_files:
                        self.current_workspace.active_file_path = recent_file
                        break
                else:
                    self.current_workspace.active_file_path = None
            else:
                self.current_workspace.active_file_path = None
        
        # Publish event
        await self.message_broker.publish('workspace.file_closed', {
            'workspace_id': self.current_workspace.workspace_id,
            'file_path': file_path,
            'file_name': file_info.file_name
        })
        
        self.stats['files_closed'] += 1
        return True
    
    async def set_active_file(self, file_path: str) -> bool:
        """Set the active file"""
        if not self.current_workspace or file_path not in self.current_workspace.open_files:
            return False
        
        self.current_workspace.active_file_path = file_path
        self.current_workspace.open_files[file_path].last_accessed = time.time()
        
        # Publish event
        await self.message_broker.publish('workspace.active_file_changed', {
            'workspace_id': self.current_workspace.workspace_id,
            'file_path': file_path,
            'file_name': self.current_workspace.open_files[file_path].file_name
        })
        
        return True
    
    async def update_file_state(self, file_path: str, 
                               is_dirty: Optional[bool] = None,
                               cursor_position: Optional[Dict[str, Any]] = None,
                               selection: Optional[Dict[str, Any]] = None) -> bool:
        """Update file state"""
        if not self.current_workspace or file_path not in self.current_workspace.open_files:
            return False
        
        file_info = self.current_workspace.open_files[file_path]
        
        if is_dirty is not None:
            file_info.is_dirty = is_dirty
        
        if cursor_position is not None:
            file_info.cursor_position = cursor_position
        
        if selection is not None:
            file_info.selection = selection
        
        file_info.last_accessed = time.time()
        
        # Publish event
        await self.message_broker.publish('workspace.file_state_changed', {
            'workspace_id': self.current_workspace.workspace_id,
            'file_path': file_path,
            'is_dirty': file_info.is_dirty,
            'cursor_position': file_info.cursor_position,
            'selection': file_info.selection
        })
        
        return True
    
    # Panel Management
    async def create_panel(self, panel_type: PanelType, title: str, 
                          position: Optional[Dict[str, Any]] = None,
                          size: Optional[Dict[str, Any]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new panel"""
        if not self.current_workspace:
            return ""
        
        panel_id = str(uuid.uuid4())
        
        panel_info = PanelInfo(
            panel_id=panel_id,
            panel_type=panel_type,
            title=title,
            position=position or {},
            size=size or {},
            metadata=metadata or {}
        )
        
        # Add to workspace
        self.current_workspace.panels[panel_id] = panel_info
        
        # Add to current layout if available
        if self.current_workspace.current_layout:
            self.current_workspace.current_layout.panels.append(panel_info)
        
        # Publish event
        await self.message_broker.publish('workspace.panel_created', {
            'workspace_id': self.current_workspace.workspace_id,
            'panel_id': panel_id,
            'panel_type': panel_type.value,
            'title': title
        })
        
        self.stats['panels_created'] += 1
        return panel_id
    
    async def close_panel(self, panel_id: str) -> bool:
        """Close a panel"""
        if not self.current_workspace or panel_id not in self.current_workspace.panels:
            return False
        
        panel_info = self.current_workspace.panels[panel_id]
        
        # Remove from workspace
        del self.current_workspace.panels[panel_id]
        
        # Remove from current layout
        if self.current_workspace.current_layout:
            self.current_workspace.current_layout.panels = [
                p for p in self.current_workspace.current_layout.panels 
                if p.panel_id != panel_id
            ]
        
        # If this was the active panel, clear it
        if self.current_workspace.active_panel_id == panel_id:
            self.current_workspace.active_panel_id = None
        
        # Publish event
        await self.message_broker.publish('workspace.panel_closed', {
            'workspace_id': self.current_workspace.workspace_id,
            'panel_id': panel_id,
            'panel_type': panel_info.panel_type.value
        })
        
        self.stats['panels_closed'] += 1
        return True
    
    async def set_active_panel(self, panel_id: str) -> bool:
        """Set the active panel"""
        if not self.current_workspace or panel_id not in self.current_workspace.panels:
            return False
        
        self.current_workspace.active_panel_id = panel_id
        self.current_workspace.panels[panel_id].last_accessed = time.time()
        self.current_workspace.panels[panel_id].state = PanelState.ACTIVE
        
        # Publish event
        await self.message_broker.publish('workspace.active_panel_changed', {
            'workspace_id': self.current_workspace.workspace_id,
            'panel_id': panel_id,
            'panel_type': self.current_workspace.panels[panel_id].panel_type.value
        })
        
        return True
    
    async def update_panel_state(self, panel_id: str, 
                                state: Optional[PanelState] = None,
                                position: Optional[Dict[str, Any]] = None,
                                size: Optional[Dict[str, Any]] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update panel state"""
        if not self.current_workspace or panel_id not in self.current_workspace.panels:
            return False
        
        panel_info = self.current_workspace.panels[panel_id]
        
        if state is not None:
            panel_info.state = state
        
        if position is not None:
            panel_info.position = position
        
        if size is not None:
            panel_info.size = size
        
        if metadata is not None:
            panel_info.metadata.update(metadata)
        
        panel_info.last_accessed = time.time()
        
        # Publish event
        await self.message_broker.publish('workspace.panel_state_changed', {
            'workspace_id': self.current_workspace.workspace_id,
            'panel_id': panel_id,
            'state': panel_info.state.value,
            'position': panel_info.position,
            'size': panel_info.size
        })
        
        return True
    
    # Terminal Management
    async def create_terminal(self, title: str, 
                            working_directory: Optional[str] = None,
                            shell: Optional[str] = None,
                            environment: Optional[Dict[str, str]] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new terminal"""
        if not self.current_workspace:
            return ""
        
        terminal_id = str(uuid.uuid4())
        
        terminal_info = TerminalInfo(
            terminal_id=terminal_id,
            title=title,
            working_directory=working_directory or self.current_workspace.root_path,
            shell=shell or "/bin/bash",
            environment=environment or {},
            metadata=metadata or {}
        )
        
        # Add to workspace
        self.current_workspace.terminals[terminal_id] = terminal_info
        
        # Publish event
        await self.message_broker.publish('workspace.terminal_created', {
            'workspace_id': self.current_workspace.workspace_id,
            'terminal_id': terminal_id,
            'title': title,
            'working_directory': terminal_info.working_directory
        })
        
        self.stats['terminals_created'] += 1
        return terminal_id
    
    async def close_terminal(self, terminal_id: str) -> bool:
        """Close a terminal"""
        if not self.current_workspace or terminal_id not in self.current_workspace.terminals:
            return False
        
        terminal_info = self.current_workspace.terminals[terminal_id]
        
        # Remove from workspace
        del self.current_workspace.terminals[terminal_id]
        
        # Publish event
        await self.message_broker.publish('workspace.terminal_closed', {
            'workspace_id': self.current_workspace.workspace_id,
            'terminal_id': terminal_id,
            'title': terminal_info.title
        })
        
        self.stats['terminals_closed'] += 1
        return True
    
    # Layout Management
    async def save_layout(self, name: str, layout_id: Optional[str] = None) -> str:
        """Save current layout"""
        if not self.current_workspace:
            return ""
        
        if layout_id is None:
            layout_id = str(uuid.uuid4())
        
        # Create layout from current state
        layout = WorkspaceLayout(
            layout_id=layout_id,
            name=name,
            panels=list(self.current_workspace.panels.values()),
            active_panel_id=self.current_workspace.active_panel_id,
            layout_config=self.current_workspace.current_layout.layout_config.copy() if self.current_workspace.current_layout else {}
        )
        
        # Save to workspace
        self.current_workspace.saved_layouts[layout_id] = layout
        
        # Publish event
        await self.message_broker.publish('workspace.layout_saved', {
            'workspace_id': self.current_workspace.workspace_id,
            'layout_id': layout_id,
            'name': name
        })
        
        self.stats['layout_saves'] += 1
        return layout_id
    
    async def load_layout(self, layout_id: str) -> bool:
        """Load a saved layout"""
        if not self.current_workspace or layout_id not in self.current_workspace.saved_layouts:
            return False
        
        layout = self.current_workspace.saved_layouts[layout_id]
        
        # Apply layout to current workspace
        self.current_workspace.current_layout = layout
        self.current_workspace.active_panel_id = layout.active_panel_id
        layout.last_used = time.time()
        
        # Publish event
        await self.message_broker.publish('workspace.layout_loaded', {
            'workspace_id': self.current_workspace.workspace_id,
            'layout_id': layout_id,
            'name': layout.name
        })
        
        return True
    
    async def delete_layout(self, layout_id: str) -> bool:
        """Delete a saved layout"""
        if not self.current_workspace or layout_id not in self.current_workspace.saved_layouts:
            return False
        
        layout = self.current_workspace.saved_layouts[layout_id]
        
        # Remove from workspace
        del self.current_workspace.saved_layouts[layout_id]
        
        # Publish event
        await self.message_broker.publish('workspace.layout_deleted', {
            'workspace_id': self.current_workspace.workspace_id,
            'layout_id': layout_id,
            'name': layout.name
        })
        
        return True
    
    # Preferences Management
    async def update_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Update workspace preferences"""
        if not self.current_workspace:
            return False
        
        self.current_workspace.preferences.update(preferences)
        
        # Publish event
        await self.message_broker.publish('workspace.preferences_updated', {
            'workspace_id': self.current_workspace.workspace_id,
            'preferences': self.current_workspace.preferences
        })
        
        return True
    
    async def get_preferences(self) -> Dict[str, Any]:
        """Get workspace preferences"""
        if not self.current_workspace:
            return {}
        
        return self.current_workspace.preferences.copy()
    
    # State Access
    async def get_workspace_state(self) -> Optional[Dict[str, Any]]:
        """Get complete workspace state"""
        if not self.current_workspace:
            return None
        
        return self.current_workspace.to_dict()
    
    async def get_open_files(self) -> List[Dict[str, Any]]:
        """Get list of open files"""
        if not self.current_workspace:
            return []
        
        return [file_info.to_dict() for file_info in self.current_workspace.open_files.values()]
    
    async def get_panels(self) -> List[Dict[str, Any]]:
        """Get list of panels"""
        if not self.current_workspace:
            return []
        
        return [panel.to_dict() for panel in self.current_workspace.panels.values()]
    
    async def get_terminals(self) -> List[Dict[str, Any]]:
        """Get list of terminals"""
        if not self.current_workspace:
            return []
        
        return [terminal.to_dict() for terminal in self.current_workspace.terminals.values()]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get workspace service statistics"""
        stats = self.stats.copy()
        stats['current_workspace'] = self.current_workspace.workspace_id if self.current_workspace else None
        stats['cached_workspaces'] = len(self.workspace_cache)
        stats['timestamp'] = time.time()
        return stats
    
    # Event Handlers
    async def _handle_workspace_event(self, message):
        """Handle workspace events"""
        # Custom event handling can be added here
        pass
    
    async def _handle_file_event(self, message):
        """Handle file events"""
        # Custom event handling can be added here
        pass
    
    async def _handle_terminal_event(self, message):
        """Handle terminal events"""
        # Custom event handling can be added here
        pass
    
    async def _handle_panel_event(self, message):
        """Handle panel events"""
        # Custom event handling can be added here
        pass
    
    # Event Hook Registration
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        self.event_handlers[event_type].append(handler)
    
    def unregister_event_handler(self, event_type: str, handler: Callable):
        """Unregister an event handler"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].remove(handler)


# Global workspace service instance
_workspace_service: Optional[WorkspaceService] = None


async def get_workspace_service() -> WorkspaceService:
    """Get the global workspace service instance"""
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
        await _workspace_service.initialize()
    return _workspace_service


async def shutdown_workspace_service():
    """Shutdown the global workspace service"""
    global _workspace_service
    if _workspace_service:
        await _workspace_service.shutdown()
        _workspace_service = None
