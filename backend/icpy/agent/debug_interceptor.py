"""
Debug Interceptor for OpenAI API Calls

Creates session_xxxx.debug.jsonl sidecar files that log all OpenAI API interactions
including request/response, context router state, and tool executions in human-readable format.
"""

import json
import logging
import os
import pprint
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class DebugInterceptor:
    """Intercepts and logs OpenAI API calls and context to debug.jsonl files"""
    
    def __init__(self, session_id: str, workspace_path: Optional[str] = None):
        """
        Initialize the debug interceptor
        
        Args:
            session_id: The session ID for the current chat session
            workspace_path: Path to the workspace (defaults to WORKSPACE_ROOT env var)
        """
        self.session_id = session_id
        self.workspace_path = workspace_path or os.getenv('WORKSPACE_ROOT', '/tmp')
        self.debug_file_path = self._get_debug_file_path()
        settings = get_debug_settings(session_id)
        env_enabled = os.getenv('ICOTES_DEBUG_AGENT', '').lower() in ('1', 'true', 'yes')
        self.enabled = settings.get('enabled', env_enabled)
        self.mode = settings.get('mode', 'minimal')
        
        if self.enabled:
            logger.info(f"[DebugInterceptor] Enabled for session {session_id} -> {self.debug_file_path}")
            self._write_header()
    
    def _get_debug_file_path(self) -> Path:
        """Construct the path for the debug.jsonl file"""
        # Store in .icotes/debug/ directory
        debug_dir = Path(self.workspace_path) / '.icotes' / 'debug'
        debug_dir.mkdir(parents=True, exist_ok=True)
        return debug_dir / f"session_{self.session_id}.debug.jsonl"
    
    def _write_header(self):
        """Write header information to the debug file"""
        header = {
            "type": "debug_session_start",
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "workspace": self.workspace_path,
            "note": "This is a debug sidecar file. All content is human-readable with pprint formatting."
        }
        self._write_entry(header)
    
    def _write_entry(self, entry: Dict[str, Any]):
        """Write a single entry to the debug file"""
        if not self.enabled:
            return
        
        try:
            with open(self.debug_file_path, 'a', encoding='utf-8') as f:
                # Write compact JSON for the entry itself
                json.dump(entry, f, ensure_ascii=False)
                f.write('\n')
                
                # Write human-readable version as comment
                f.write(f"# Human-readable version:\n")
                for line in pprint.pformat(entry, width=120, depth=10).split('\n'):
                    f.write(f"# {line}\n")
                f.write(f"# {'-' * 80}\n\n")
        except Exception as e:
            logger.error(f"[DebugInterceptor] Failed to write entry: {e}")
    
    async def log_openai_request(self, api_params: Dict[str, Any], context_info: Optional[Dict[str, Any]] = None):
        """
        Log an OpenAI API request
        
        Args:
            api_params: The parameters being sent to OpenAI API
            context_info: Optional context information (router state, hop info, etc.)
        """
        if not self.enabled:
            return
        
        if self.mode == 'minimal':
            entry = {
                "type": "openai_request",
                "timestamp": datetime.now().isoformat(),
                "api_params": {
                    "model": api_params.get('model'),
                    "message_count": len(api_params.get('messages', [])),
                    "tools": [t.get('function', {}).get('name') for t in api_params.get('tools', [])],
                    "temperature": api_params.get('temperature'),
                    "max_tokens": api_params.get('max_tokens') or api_params.get('max_completion_tokens'),
                    "stream": api_params.get('stream'),
                },
                "context": context_info or {}
            }
        else:
            entry = {
                "type": "openai_request",
                "timestamp": datetime.now().isoformat(),
                "api_params": {
                    "model": api_params.get('model'),
                    "messages": api_params.get('messages', []),
                    "tools": [
                        {
                            "type": t.get('type'),
                            "function": {
                                "name": t.get('function', {}).get('name'),
                                "description": t.get('function', {}).get('description', '')[:100] + '...'
                            }
                        }
                        for t in api_params.get('tools', [])
                    ],
                    "temperature": api_params.get('temperature'),
                    "max_tokens": api_params.get('max_tokens') or api_params.get('max_completion_tokens'),
                    "stream": api_params.get('stream'),
                    "other_params": {k: v for k, v in api_params.items() 
                                   if k not in ['model', 'messages', 'tools', 'temperature', 'max_tokens', 'max_completion_tokens', 'stream']}
                },
                "context": context_info or {}
            }
        self._write_entry(entry)
    
    async def log_openai_response(self, response_data: Any, finish_reason: Optional[str] = None):
        """
        Log an OpenAI API response
        
        Args:
            response_data: The response from OpenAI (collected chunks or final message)
            finish_reason: The finish reason from OpenAI
        """
        if not self.enabled:
            return
        
        if self.mode == 'minimal':
            entry = {
                "type": "openai_response",
                "timestamp": datetime.now().isoformat(),
                "finish_reason": finish_reason,
                "response_preview": str(response_data)[:500] if response_data else None
            }
        else:
            entry = {
                "type": "openai_response",
                "timestamp": datetime.now().isoformat(),
                "finish_reason": finish_reason,
                "response": str(response_data)[:5000] if response_data else None  # Truncate long responses
            }
        self._write_entry(entry)
    
    async def log_tool_execution(self, tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]):
        """
        Log a tool execution
        
        Args:
            tool_name: Name of the tool executed
            arguments: Arguments passed to the tool
            result: Result returned by the tool
        """
        if not self.enabled:
            return
        
        if self.mode == 'minimal':
            entry = {
                "type": "tool_execution",
                "timestamp": datetime.now().isoformat(),
                "tool_name": tool_name,
                "arguments": {"keys": list(arguments.keys()) if isinstance(arguments, dict) else None},
                "result": {
                    "success": result.get('success'),
                    "error": result.get('error'),
                }
            }
        else:
            entry = {
                "type": "tool_execution",
                "timestamp": datetime.now().isoformat(),
                "tool_name": tool_name,
                "arguments": arguments,
                "result": {
                    "success": result.get('success'),
                    "error": result.get('error'),
                    "data_preview": str(result.get('data'))[:1000] if result.get('data') else None
                }
            }
        self._write_entry(entry)
    
    async def log_context_state(self, context_info: Dict[str, Any]):
        """
        Log the current context router state
        
        Args:
            context_info: Full context information including hop state, workspace paths, etc.
        """
        if not self.enabled:
            return
        
        entry = {
            "type": "context_state",
            "timestamp": datetime.now().isoformat(),
            "context": context_info
        }
        self._write_entry(entry)

    async def log_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Log a generic debug event for the current session.

        This is used for chat/session lifecycle events that are not specific to
        OpenAI API calls (e.g., stream start/end, cancellations, stop reasons).
        """
        if not self.enabled:
            return

        entry = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "mode": self.mode,
            "data": data or {},
        }
        self._write_entry(entry)
    
    def log_error(self, error_type: str, error_message: str, stack_trace: Optional[str] = None):
        """
        Log an error
        
        Args:
            error_type: Type/category of error
            error_message: Error message
            stack_trace: Optional stack trace
        """
        if not self.enabled:
            return
        
        entry = {
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": error_message,
            "stack_trace": stack_trace
        }
        self._write_entry(entry)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if self.enabled and not self.debug_file_path.exists():
            self._write_header()

    def set_mode(self, mode: str) -> None:
        if mode in ("minimal", "verbose"):
            self.mode = mode


# Global registry of interceptors per session
_interceptors: Dict[str, DebugInterceptor] = {}
_debug_settings: Dict[str, Dict[str, Any]] = {}

def get_debug_settings(session_id: str) -> Dict[str, Any]:
    """Get debug settings for a session with env defaults."""
    env_enabled = os.getenv('ICOTES_DEBUG_AGENT', '').lower() in ('1', 'true', 'yes')
    settings = _debug_settings.get(session_id, {})

    # Load persisted settings from session meta if available
    try:
        workspace = os.getenv('WORKSPACE_ROOT', '/tmp')
        meta_path = Path(workspace) / '.icotes' / 'chat_history' / f"{session_id}.meta.json"
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as mf:
                meta = json.load(mf)
            debug_cfg = (meta or {}).get('debug') or {}
            settings = {**settings, **debug_cfg}
    except Exception:
        pass
    return {
        "enabled": settings.get('enabled', env_enabled),
        "mode": settings.get('mode', 'minimal')
    }

def set_debug_settings(session_id: str, enabled: bool, mode: str = "minimal") -> None:
    """Set debug settings for a session and update live interceptors."""
    _debug_settings[session_id] = {
        "enabled": bool(enabled),
        "mode": mode if mode in ("minimal", "verbose") else "minimal",
    }
    if session_id in _interceptors:
        interceptor = _interceptors[session_id]
        interceptor.set_enabled(bool(enabled))
        interceptor.set_mode(_debug_settings[session_id]["mode"])

def get_interceptor(session_id: str, workspace_path: Optional[str] = None) -> DebugInterceptor:
    """Get or create a debug interceptor for a session"""
    if session_id not in _interceptors:
        _interceptors[session_id] = DebugInterceptor(session_id, workspace_path)
    return _interceptors[session_id]

def clear_interceptor(session_id: str):
    """Clear an interceptor from the registry"""
    if session_id in _interceptors:
        del _interceptors[session_id]

def _get_debug_file_path(session_id: str, workspace_path: Optional[str] = None) -> Path:
    """Resolve debug file path for a session."""
    workspace = workspace_path or os.getenv('WORKSPACE_ROOT', '/tmp')
    debug_dir = Path(workspace) / '.icotes' / 'debug'
    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir / f"session_{session_id}.debug.jsonl"

def read_debug_entries(session_id: str, workspace_path: Optional[str] = None) -> list[Dict[str, Any]]:
    """Read debug entries for a session, skipping comment lines."""
    path = _get_debug_file_path(session_id, workspace_path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    entries: list[Dict[str, Any]] = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries


async def get_context_snapshot() -> Dict[str, Any]:
    """
    Get a snapshot of the current context router state
    
    Returns a dictionary with all relevant context information including:
    - Active context ID
    - Hop session details
    - Workspace paths
    - Connection status
    """
    context_snapshot = {
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        from icpy.services.context_router import get_context_router
        router = await get_context_router()
        context = await router.get_context()
        
        context_snapshot.update({
            "context_id": context.contextId,
            "status": context.status,
            "friendly_name": context.credentialName,
            "cwd": context.cwd,
            "host": context.host,
            "username": context.username,
            "is_remote": context.contextId != "local"
        })
        
        # Get workspace info
        try:
            from icpy.services.workspace_service import get_workspace_service
            workspace = await get_workspace_service()
            context_snapshot["workspace_root"] = workspace.root_path
        except Exception as e:
            logger.debug(f"Failed to get workspace info: {e}")
    
    except Exception as e:
        logger.error(f"Failed to get context snapshot: {e}")
        context_snapshot["error"] = str(e)
    
    return context_snapshot
