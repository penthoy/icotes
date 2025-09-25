"""
File System Service for icpy Backend

Handles all file operations including read, write, delete, list, and search.
Implements file watching using watchdog for external changes.
Supports file type detection, content analysis, and search indexing.
Provides file permissions and access control.
Publishes real-time file change events.

This service follows Google-style docstrings and integrates with the message broker
for event-driven architecture.
"""

import asyncio
import aiofiles
import hashlib
import json
import logging
import mimetypes
import os
import pathlib
import re
import shutil
import stat
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..core.message_broker import get_message_broker
from ..core.connection_manager import get_connection_manager

logger = logging.getLogger(__name__)


class FileType(Enum):
    """File type enumeration for classification."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    DOCUMENT = "document"
    BINARY = "binary"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    UNKNOWN = "unknown"


class FilePermission(Enum):
    """File permission enumeration."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    CREATE = "create"


class FileOperation(Enum):
    """File operation enumeration for tracking."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    CREATE = "create"
    MOVE = "move"
    COPY = "copy"
    WATCH = "watch"


@dataclass
class FileInfo:
    """Information about a file or directory.
    
    Attributes:
        path: Absolute file path
        name: File name
        size: File size in bytes
        type: File type classification
        mime_type: MIME type
        created_at: Creation timestamp
        modified_at: Last modification timestamp
        accessed_at: Last access timestamp
        permissions: File permissions
        owner: File owner
        group: File group
        is_directory: Whether this is a directory
        is_symlink: Whether this is a symbolic link
        is_hidden: Whether this is a hidden file
        extension: File extension
        content_hash: Hash of file content for change detection
        metadata: Additional metadata
    """
    path: str
    name: str
    size: int = 0
    type: FileType = FileType.UNKNOWN
    mime_type: str = "application/octet-stream"
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    permissions: List[FilePermission] = field(default_factory=list)
    owner: str = ""
    group: str = ""
    is_directory: bool = False
    is_symlink: bool = False
    is_hidden: bool = False
    extension: str = ""
    content_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert FileInfo to dictionary for serialization.
        
        Returns:
            Dictionary representation of FileInfo
        """
        return {
            'path': self.path,
            'name': self.name,
            'size': self.size,
            'type': self.type.value,
            'mime_type': self.mime_type,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'accessed_at': self.accessed_at,
            'permissions': [p.value for p in self.permissions],
            'owner': self.owner,
            'group': self.group,
            'is_directory': self.is_directory,
            'is_symlink': self.is_symlink,
            'is_hidden': self.is_hidden,
            'extension': self.extension,
            'content_hash': self.content_hash,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileInfo':
        """Create FileInfo from dictionary.
        
        Args:
            data: Dictionary containing FileInfo data
            
        Returns:
            FileInfo instance
        """
        return cls(
            path=data['path'],
            name=data['name'],
            size=data.get('size', 0),
            type=FileType(data.get('type', FileType.UNKNOWN.value)),
            mime_type=data.get('mime_type', 'application/octet-stream'),
            created_at=data.get('created_at', time.time()),
            modified_at=data.get('modified_at', time.time()),
            accessed_at=data.get('accessed_at', time.time()),
            permissions=[FilePermission(p) for p in data.get('permissions', [])],
            owner=data.get('owner', ''),
            group=data.get('group', ''),
            is_directory=data.get('is_directory', False),
            is_symlink=data.get('is_symlink', False),
            is_hidden=data.get('is_hidden', False),
            extension=data.get('extension', ''),
            content_hash=data.get('content_hash', ''),
            metadata=data.get('metadata', {})
        )


@dataclass
class SearchResult:
    """Search result for file search operations.
    
    Attributes:
        file_info: Information about the found file
        matches: List of matching lines or content
        score: Relevance score
        context: Additional context information
    """
    file_info: FileInfo
    matches: List[str] = field(default_factory=list)
    score: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert SearchResult to dictionary.
        
        Returns:
            Dictionary representation of SearchResult
        """
        return {
            'file_info': self.file_info.to_dict(),
            'matches': self.matches,
            'score': self.score,
            'context': self.context
        }


class FileSystemEventHandler(FileSystemEventHandler):
    """Custom file system event handler for watchdog integration.
    
    This handler processes file system events and publishes them
    through the message broker for real-time updates.
    """

    def __init__(self, filesystem_service: 'FileSystemService'):
        """Initialize the event handler.
        
        Args:
            filesystem_service: Reference to the filesystem service
        """
        super().__init__()
        self.filesystem_service = filesystem_service
        self.logger = logging.getLogger(__name__ + '.EventHandler')

    def on_created(self, event):
        """Handle file creation events.
        
        Args:
            event: Watchdog file system event
        """
        try:
            # Keep creation events at info for visibility
            self.logger.info(f"[FS] on_created path={event.src_path} is_dir={event.is_directory}")
        except Exception:
            pass
        if event.is_directory:
            # Suppress duplicate event if we just published from create_directory
            try:
                full_path = os.path.abspath(event.src_path)
                now = time.time()
                # Purge old entries
                stale_cutoff = now - 5
                self.filesystem_service._recent_created_dirs = {
                    k: v for k, v in self.filesystem_service._recent_created_dirs.items() if v >= stale_cutoff
                }
                recent_ts = self.filesystem_service._recent_created_dirs.get(full_path)
                if recent_ts is not None and now - recent_ts < 2:
                    self.logger.debug(f"[FS] Suppressing duplicate directory_created for {full_path}")
                    return
            except Exception as e:
                self.logger.debug(f"[FS] duplicate suppression error: {e}")
            # Publish directory created (async wrapper for consistency)
            self._schedule_async_task(self._handle_directory_created(event.src_path))
        else:
            self._schedule_async_task(self._handle_file_created(event.src_path))

    def on_modified(self, event):
        """Handle file modification events.
        
        Args:
            event: Watchdog file system event
        """
        try:
            # Modification events can be very noisy; keep at debug
            self.logger.debug(f"[FS] on_modified path={event.src_path} is_dir={event.is_directory}")
        except Exception:
            pass
        if not event.is_directory:
            self._schedule_async_task(self._handle_file_modified(event.src_path))

    def on_deleted(self, event):
        """Handle file deletion events.
        
        Args:
            event: Watchdog file system event
        """
        try:
            self.logger.info(f"[FS] on_deleted path={event.src_path} is_dir={event.is_directory}")
        except Exception:
            pass
        self._schedule_async_task(self._handle_file_deleted(event.src_path, event.is_directory))

    def on_moved(self, event):
        """Handle file move/rename events.
        
        Args:
            event: Watchdog file system event
        """
        try:
            self.logger.info(f"[FS] on_moved src={event.src_path} dest={event.dest_path} is_dir={event.is_directory}")
        except Exception:
            pass
        self._schedule_async_task(self._handle_file_moved(event.src_path, event.dest_path, event.is_directory))

    def _schedule_async_task(self, coro):
        """Schedule an async task from a synchronous context.
        
        Args:
            coro: Coroutine to schedule
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            # No running event loop, try to create one
            try:
                asyncio.run(coro)
            except Exception as e:
                self.logger.error(f"Failed to schedule async task: {e}")

    async def _handle_file_created(self, file_path: str):
        """Handle file creation asynchronously.
        
        Args:
            file_path: Path to the created file
        """
        try:
            file_info = await self.filesystem_service.get_file_info(file_path)
            if file_info:
                # Publish created event (no pre-publish info to reduce duplication)
                await self.filesystem_service.message_broker.publish('fs.file_created', {
                    'file_path': file_path,
                    'file_info': file_info.to_dict(),
                    'timestamp': time.time()
                })
                self.logger.debug(f"[FS] published fs.file_created: {file_path}")
        except Exception as e:
            self.logger.error(f"[FS] Error handling file creation {file_path}: {e}")

    async def _handle_directory_created(self, dir_path: str):
        """Handle directory creation asynchronously (external mkdir, etc.)."""
        try:
            await self.filesystem_service.message_broker.publish('fs.directory_created', {
                'dir_path': os.path.abspath(dir_path),
                'timestamp': time.time(),
                'external': True
            })
            self.logger.debug(f"[FS] published fs.directory_created (watchdog): {dir_path}")
        except Exception as e:
            self.logger.error(f"[FS] Error handling directory creation {dir_path}: {e}")

    async def _handle_file_modified(self, file_path: str):
        """Handle file modification asynchronously.
        
        Args:
            file_path: Path to the modified file
        """
        try:
            file_info = await self.filesystem_service.get_file_info(file_path)
            if file_info:
                await self.filesystem_service.message_broker.publish('fs.file_modified', {
                    'file_path': file_path,
                    'file_info': file_info.to_dict(),
                    'timestamp': time.time()
                })
                self.logger.debug(f"[FS] published fs.file_modified: {file_path}")
        except Exception as e:
            self.logger.error(f"[FS] Error handling file modification {file_path}: {e}")

    async def _handle_file_deleted(self, file_path: str, is_directory: bool):
        """Handle file deletion asynchronously.
        
        Args:
            file_path: Path to the deleted file
            is_directory: Whether the deleted item was a directory
        """
        try:
            await self.filesystem_service.message_broker.publish('fs.file_deleted', {
                'file_path': file_path,
                'is_directory': is_directory,
                'timestamp': time.time()
            })
            self.logger.debug(f"[FS] published fs.file_deleted: {file_path}")
        except Exception as e:
            self.logger.error(f"[FS] Error handling file deletion {file_path}: {e}")

    async def _handle_file_moved(self, src_path: str, dest_path: str, is_directory: bool):
        """Handle file move/rename asynchronously.
        
        Args:
            src_path: Original file path
            dest_path: New file path
            is_directory: Whether the moved item is a directory
        """
        try:
            file_info = await self.filesystem_service.get_file_info(dest_path)
            await self.filesystem_service.message_broker.publish('fs.file_moved', {
                'src_path': src_path,
                'dest_path': dest_path,
                'file_info': file_info.to_dict() if file_info else None,
                'is_directory': is_directory,
                'timestamp': time.time()
            })
            self.logger.debug(f"[FS] published fs.file_moved: {src_path} -> {dest_path}")
        except Exception as e:
            self.logger.error(f"[FS] Error handling file move {src_path} -> {dest_path}: {e}")


class FileSystemService:
    """File System Service for comprehensive file operations.
    
    This service provides a complete file system abstraction with support for:
    - File CRUD operations (create, read, update, delete)
    - Directory operations and traversal
    - File watching and real-time change detection
    - File search and indexing
    - File type detection and content analysis
    - Permission management and access control
    - Event-driven architecture with message broker integration
    """

    def __init__(self, root_path: str = None, max_file_size: int = 100 * 1024 * 1024):
        """Initialize the File System Service.
        
        Args:
            root_path: Root directory path for file operations (default: current working directory)
            max_file_size: Maximum file size to handle (default: 100MB)
        """
        self.root_path = os.path.abspath(root_path if root_path is not None else '.')
        self.max_file_size = max_file_size
        self.message_broker = None
        self.connection_manager = None
        
        # File watching
        self.observer = Observer()
        self.event_handler = FileSystemEventHandler(self)
        self.watched_paths: Set[str] = set()
        
        # File indexing
        self.file_index: Dict[str, FileInfo] = {}
        self.search_index: Dict[str, Set[str]] = defaultdict(set)  # word -> file_paths
        
        # Statistics
        self.stats = {
            'files_read': 0,
            'files_written': 0,
            'files_deleted': 0,
            'files_created': 0,
            'files_moved': 0,
            'files_copied': 0,
            'searches_performed': 0,
            'total_bytes_read': 0,
            'total_bytes_written': 0
        }

        # Track directories explicitly created via service to suppress duplicate
        # watchdog-created events (API create -> publish + watchdog on_created)
        self._recent_created_dirs: Dict[str, float] = {}
        
        # File type mappings
        self.code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.cc', '.cxx',
            '.h', '.hpp', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.clj', '.hs', '.ml', '.fs', '.pl', '.r', '.m', '.mm', '.sh', '.bash', '.zsh',
            '.ps1', '.bat', '.cmd', '.vbs', '.lua', '.dart', '.elm', '.ex', '.exs', '.jl',
            '.nim', '.cr', '.zig', '.v', '.pas', '.dpr', '.pp', '.inc', '.f', '.f90',
            '.f95', '.f03', '.f08', '.for', '.ftn', '.fpp', '.asm', '.s', '.S', '.nasm',
            '.masm', '.yasm', '.sql', '.mysql', '.pgsql', '.plsql', '.tsql', '.cql'
        }
        
        self.text_extensions = {
            '.txt', '.md', '.markdown', '.rst', '.org', '.tex', '.latex', '.rtf',
            '.log', '.cfg', '.conf', '.ini', '.toml', '.yaml', '.yml', '.json',
            '.xml', '.html', '.htm', '.xhtml', '.css', '.scss', '.sass', '.less',
            '.csv', '.tsv', '.properties', '.env', '.gitignore', '.dockerignore',
            '.editorconfig', '.eslintrc', '.prettierrc', '.babelrc', '.browserslistrc'
        }
        
        self.archive_extensions = {
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.z', '.lz', '.lzma',
            '.tgz', '.tbz2', '.txz', '.jar', '.war', '.ear', '.apk', '.deb', '.rpm',
            '.dmg', '.iso', '.img', '.msi', '.exe', '.cab', '.ace', '.arj', '.lha',
            '.lzh', '.pak', '.pk3', '.pk4', '.vpk', '.wad', '.zoo'
        }
        
        logger.info(f"FileSystemService initialized with root_path: {self.root_path}")

    async def initialize(self):
        """Initialize the file system service.
        
        Sets up message broker connection, connection manager, and starts file watching.
        """
        self.message_broker = await get_message_broker()
        self.connection_manager = await get_connection_manager()
        
        # Start file watching
        await self._start_file_watching()
        
        # Build initial file index
        await self._build_file_index()
        
        logger.info("[FS] FileSystemService initialized successfully")

    async def shutdown(self):
        """Shutdown the file system service.
        
        Stops file watching and cleans up resources.
        """
        # Stop file watching
        await self._stop_file_watching()
        
        # Clear indices
        self.file_index.clear()
        self.search_index.clear()
        
        logger.info("[FS] FileSystemService shutdown complete")

    async def _start_file_watching(self):
        """Start file system watching for the root path."""
        try:
            self.observer.schedule(self.event_handler, self.root_path, recursive=True)
            self.observer.start()
            self.watched_paths.add(self.root_path)
            logger.info(f"[FS] Started watching root: {self.root_path}")
        except Exception as e:
            logger.error(f"[FS] Failed to start file watching: {e}")

    async def _stop_file_watching(self):
        """Stop file system watching."""
        try:
            self.observer.stop()
            self.observer.join()
            self.watched_paths.clear()
            logger.info("[FS] Stopped file watching")
        except Exception as e:
            logger.error(f"[FS] Error stopping file watching: {e}")

    async def rebuild_index(self):
        """Rebuild the file index.
        
        This method clears the current index and rebuilds it by scanning
        the root directory. Useful for testing or when the file system
        has changed significantly.
        """
        logger.info("[FS] Rebuilding file index...")
        
        # Clear existing indices
        self.file_index.clear()
        self.search_index.clear()
        
        # Rebuild the index
        await self._build_file_index()
        
        logger.info(f"[FS] File index rebuilt with {len(self.file_index)} files")

    async def _build_file_index(self):
        """Build initial file index by scanning the root directory."""
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file_name in files:
                    if file_name.startswith('.'):
                        continue  # Skip hidden files
                    
                    file_path = os.path.join(root, file_name)
                    file_info = await self.get_file_info(file_path)
                    if file_info:
                        self.file_index[file_path] = file_info
                        
                        # Add to search index if it's a text file
                        if file_info.type in [FileType.TEXT, FileType.CODE]:
                            await self._index_file_content(file_path)
            
            
            logger.info(f"[FS] Built file index with {len(self.file_index)} files")
        except Exception as e:
            logger.error(f"[FS] Error building file index: {e}")

    async def _index_file_content(self, file_path: str):
        """Index file content for search functionality.
        
        Args:
            file_path: Path to the file to index
        """
        try:
            if os.path.getsize(file_path) > self.max_file_size:
                return  # Skip large files
            
            content = await self.read_file(file_path)
            if content:
                words = self._extract_words(content)
                for word in words:
                    self.search_index[word.lower()].add(file_path)
        except Exception as e:
            logger.error(f"Error indexing file content {file_path}: {e}")

    def _extract_words(self, content: str) -> List[str]:
        """Extract words from content for search indexing.
        
        Args:
            content: File content to extract words from
            
        Returns:
            List of extracted words
        """
        # Simple word extraction - can be enhanced with more sophisticated tokenization
        words = re.findall(r'\b\w+\b', content)
        return [word for word in words if len(word) > 2]  # Filter out short words

    def _classify_file_type(self, file_path: str) -> FileType:
        """Classify file type based on extension and content.
        
        Args:
            file_path: Path to the file to classify
            
        Returns:
            FileType enum value
        """
        if os.path.isdir(file_path):
            return FileType.DIRECTORY
        
        if os.path.islink(file_path):
            return FileType.SYMLINK
        
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext in self.code_extensions:
            return FileType.CODE
        elif ext in self.text_extensions:
            return FileType.TEXT
        elif ext in self.archive_extensions:
            return FileType.ARCHIVE
        elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp', '.ico'}:
            return FileType.IMAGE
        elif ext in {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'}:
            return FileType.AUDIO
        elif ext in {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}:
            return FileType.VIDEO
        elif ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp'}:
            return FileType.DOCUMENT
        else:
            return FileType.BINARY

    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """Get comprehensive information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileInfo object with file details or None if file doesn't exist
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            stat_info = os.stat(file_path)
            file_name = os.path.basename(file_path)
            file_type = self._classify_file_type(file_path)
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"
            
            # Get file permissions
            permissions = []
            if stat_info.st_mode & stat.S_IRUSR:
                permissions.append(FilePermission.READ)
            if stat_info.st_mode & stat.S_IWUSR:
                permissions.append(FilePermission.WRITE)
            if stat_info.st_mode & stat.S_IXUSR:
                permissions.append(FilePermission.EXECUTE)
            
            # Get content hash for change detection
            content_hash = ""
            if file_type in [FileType.TEXT, FileType.CODE] and stat_info.st_size < self.max_file_size:
                try:
                    async with aiofiles.open(file_path, 'rb') as f:
                        content = await f.read()
                        # Use SHA-256 for integrity/change detection (non-crypto auth)
                        content_hash = hashlib.sha256(content).hexdigest()
                except Exception:
                    pass  # Ignore hash calculation errors
            
            return FileInfo(
                path=file_path,
                name=file_name,
                size=stat_info.st_size,
                type=file_type,
                mime_type=mime_type,
                created_at=stat_info.st_ctime,
                modified_at=stat_info.st_mtime,
                accessed_at=stat_info.st_atime,
                permissions=permissions,
                owner=str(stat_info.st_uid),
                group=str(stat_info.st_gid),
                is_directory=os.path.isdir(file_path),
                is_symlink=os.path.islink(file_path),
                is_hidden=file_name.startswith('.'),
                extension=os.path.splitext(file_name)[1].lower(),
                content_hash=content_hash
            )
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None

    async def read_file(self, file_path: str, encoding: str = 'utf-8') -> Optional[str]:
        """Read file content.
        
        Args:
            file_path: Path to the file to read
            encoding: File encoding (default: utf-8)
            
        Returns:
            File content as string or None if error
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            # Check file size
            if os.path.getsize(file_path) > self.max_file_size:
                logger.warning(f"File too large to read: {file_path}")
                return None
            
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                content = await f.read()
                
                self.stats['files_read'] += 1
                self.stats['total_bytes_read'] += len(content.encode(encoding))
                
                # Publish event
                await self.message_broker.publish('fs.file_read', {
                    'file_path': file_path,
                    'size': len(content),
                    'encoding': encoding,
                    'timestamp': time.time()
                })
                
                return content
                
        except UnicodeDecodeError:
            logger.error(f"Encoding error reading file: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    async def write_file(self, file_path: str, content: str, encoding: str = 'utf-8', create_dirs: bool = True) -> bool:
        """Write content to file.
        
        Args:
            file_path: Path to the file to write
            content: Content to write
            encoding: File encoding (default: utf-8)
            create_dirs: Whether to create parent directories if they don't exist
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create parent directories if needed
            if create_dirs:
                dir_path = os.path.dirname(file_path)
                if dir_path:  # Only create directory if path is not empty
                    os.makedirs(dir_path, exist_ok=True)
            
            # Check if file exists for operation tracking
            file_exists = os.path.exists(file_path)
            
            async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            # Update file index
            file_info = await self.get_file_info(file_path)
            if file_info:
                self.file_index[file_path] = file_info
                
                # Update search index
                if file_info.type in [FileType.TEXT, FileType.CODE]:
                    await self._index_file_content(file_path)
            
            # Update statistics
            if file_exists:
                self.stats['files_written'] += 1
            else:
                self.stats['files_created'] += 1
            
            self.stats['total_bytes_written'] += len(content.encode(encoding))
            
            # Publish event
            await self.message_broker.publish('fs.file_written', {
                'file_path': file_path,
                'size': len(content),
                'encoding': encoding,
                'created': not file_exists,
                'timestamp': time.time()
            })
            
            logger.info(f"File written successfully: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False

    async def create_directory(self, dir_path: str, parents: bool = True) -> bool:
        """Create a directory.
        
        Args:
            dir_path: Path to the directory to create
            parents: Whether to create parent directories if they don't exist
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize path
            full_path = os.path.abspath(dir_path)
            
            # Check if directory already exists
            if os.path.exists(full_path):
                if os.path.isdir(full_path):
                    logger.info(f"Directory already exists: {full_path}")
                    return True
                else:
                    logger.error(f"Path exists but is not a directory: {full_path}")
                    return False
            
            # Create directory
            os.makedirs(full_path, exist_ok=True) if parents else os.mkdir(full_path)
            
            # Update statistics
            self.stats['files_created'] += 1

            # Note directory so watchdog on_created can suppress duplicate event
            self._recent_created_dirs[full_path] = time.time()
            
            # Publish event
            await self.message_broker.publish('fs.directory_created', {
                'dir_path': full_path,
                'parents': parents,
                'timestamp': time.time()
            })
            
            logger.info(f"Directory created successfully: {full_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            return False

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file or directory.
        
        Args:
            file_path: Path to the file or directory to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            is_directory = os.path.isdir(file_path)
            
            if is_directory:
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            
            # Update file index
            if file_path in self.file_index:
                del self.file_index[file_path]
            
            # Remove from search index
            for word_set in self.search_index.values():
                word_set.discard(file_path)
            
            self.stats['files_deleted'] += 1
            
            # Publish event
            await self.message_broker.publish('fs.file_deleted', {
                'file_path': file_path,
                'is_directory': is_directory,
                'timestamp': time.time()
            })
            
            logger.info(f"File deleted successfully: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False

    async def move_file(self, src_path: str, dest_path: str, overwrite: bool = False) -> bool:
        """Move or rename a file.
        
        Args:
            src_path: Source file path
            dest_path: Destination file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(src_path):
                return False

            # Normalize paths to avoid duplicate slashes when comparing
            src_path = os.path.normpath(src_path)
            dest_path = os.path.normpath(dest_path)

            if src_path == dest_path:
                return False

            # Prevent moving a directory into itself or one of its descendants
            if os.path.isdir(src_path) and dest_path.startswith(f"{src_path}{os.sep}"):
                return False

            if os.path.exists(dest_path):
                if not overwrite:
                    return False
                # If overwrite is permitted, remove the existing destination first
                if os.path.isdir(dest_path):
                    shutil.rmtree(dest_path)
                else:
                    os.remove(dest_path)
            
            # Create destination directory if needed
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            shutil.move(src_path, dest_path)
            
            # Update indices
            if src_path in self.file_index:
                file_info = self.file_index.pop(src_path)
                file_info.path = dest_path
                file_info.name = os.path.basename(dest_path)
                self.file_index[dest_path] = file_info
            
            # Update search index
            for word_set in self.search_index.values():
                if src_path in word_set:
                    word_set.remove(src_path)
                    word_set.add(dest_path)
            
            self.stats['files_moved'] += 1
            
            # Publish event
            await self.message_broker.publish('fs.file_moved', {
                'src_path': src_path,
                'dest_path': dest_path,
                'timestamp': time.time()
            })
            
            logger.info(f"File moved successfully: {src_path} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving file {src_path} -> {dest_path}: {e}")
            return False

    async def copy_file(self, src_path: str, dest_path: str) -> bool:
        """Copy a file.
        
        Args:
            src_path: Source file path
            dest_path: Destination file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(src_path):
                return False
            
            # Create destination directory if needed
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)
            
            # Update file index
            file_info = await self.get_file_info(dest_path)
            if file_info:
                self.file_index[dest_path] = file_info
                
                # Update search index
                if file_info.type in [FileType.TEXT, FileType.CODE]:
                    await self._index_file_content(dest_path)
            
            self.stats['files_copied'] += 1
            
            # Publish event
            await self.message_broker.publish('fs.file_copied', {
                'src_path': src_path,
                'dest_path': dest_path,
                'timestamp': time.time()
            })
            
            logger.info(f"File copied successfully: {src_path} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying file {src_path} -> {dest_path}: {e}")
            return False

    async def list_directory(self, dir_path: str, include_hidden: bool = False, recursive: bool = False) -> List[FileInfo]:
        """List contents of a directory.
        
        Args:
            dir_path: Directory path to list
            include_hidden: Whether to include hidden files
            recursive: Whether to list recursively
            
        Returns:
            List of FileInfo objects
        """
        try:
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return []
            
            result = []
            
            if recursive:
                for root, dirs, files in os.walk(dir_path):
                    # Filter hidden directories
                    if not include_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    # Add directories
                    for dir_name in dirs:
                        if include_hidden or not dir_name.startswith('.'):
                            full_path = os.path.join(root, dir_name)
                            file_info = await self.get_file_info(full_path)
                            if file_info:
                                result.append(file_info)
                    
                    # Add files
                    for file_name in files:
                        if include_hidden or not file_name.startswith('.'):
                            full_path = os.path.join(root, file_name)
                            file_info = await self.get_file_info(full_path)
                            if file_info:
                                result.append(file_info)
            else:
                for item in os.listdir(dir_path):
                    if include_hidden or not item.startswith('.'):
                        full_path = os.path.join(dir_path, item)
                        file_info = await self.get_file_info(full_path)
                        if file_info:
                            result.append(file_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing directory {dir_path}: {e}")
            return []

    async def search_files(self, query: str, search_content: bool = True, file_types: Optional[List[FileType]] = None,
                          max_results: int = 100) -> List[SearchResult]:
        """Search for files by name and optionally content.
        
        Args:
            query: Search query
            search_content: Whether to search file content
            file_types: List of file types to search (None for all)
            max_results: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        try:
            results = []
            query_lower = query.lower()
            
            # Search by filename
            for file_path, file_info in self.file_index.items():
                if file_types and file_info.type not in file_types:
                    continue
                
                score = 0.0
                matches = []
                
                # Check filename match
                if query_lower in file_info.name.lower():
                    score += 1.0
                    matches.append(f"Filename: {file_info.name}")
                
                # Check content match if requested
                if search_content and file_info.type in [FileType.TEXT, FileType.CODE]:
                    content_matches = await self._search_file_content(file_path, query)
                    if content_matches:
                        score += 0.5 * len(content_matches)
                        matches.extend(content_matches)
                
                if score > 0:
                    results.append(SearchResult(
                        file_info=file_info,
                        matches=matches,
                        score=score
                    ))
            
            # Sort by score (descending)
            results.sort(key=lambda x: x.score, reverse=True)
            
            # Limit results
            results = results[:max_results]
            
            self.stats['searches_performed'] += 1
            
            # Publish event
            await self.message_broker.publish('fs.search_performed', {
                'query': query,
                'search_content': search_content,
                'file_types': [ft.value for ft in file_types] if file_types else None,
                'result_count': len(results),
                'timestamp': time.time()
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []

    async def _search_file_content(self, file_path: str, query: str) -> List[str]:
        """Search for query in file content.
        
        Args:
            file_path: Path to the file to search
            query: Search query
            
        Returns:
            List of matching lines
        """
        try:
            content = await self.read_file(file_path)
            if not content:
                return []
            
            matches = []
            lines = content.split('\n')
            query_lower = query.lower()
            
            for line_num, line in enumerate(lines, 1):
                if query_lower in line.lower():
                    matches.append(f"Line {line_num}: {line.strip()}")
            
            return matches
            
        except Exception as e:
            logger.error(f"Error searching file content {file_path}: {e}")
            return []

    async def watch_path(self, path: str) -> bool:
        """Add a path to file watching.
        
        Args:
            path: Path to watch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if path not in self.watched_paths:
                self.observer.schedule(self.event_handler, path, recursive=True)
                self.watched_paths.add(path)
                logger.info(f"Added path to watching: {path}")
                
                # Publish event
                await self.message_broker.publish('fs.path_watched', {
                    'path': path,
                    'timestamp': time.time()
                })
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error watching path {path}: {e}")
            return False

    async def unwatch_path(self, path: str) -> bool:
        """Remove a path from file watching.
        
        Args:
            path: Path to unwatch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if path in self.watched_paths:
                # Note: watchdog doesn't provide a direct way to remove individual watches
                # This would require restarting the observer with updated paths
                self.watched_paths.remove(path)
                logger.info(f"Removed path from watching: {path}")
                
                # Publish event
                await self.message_broker.publish('fs.path_unwatched', {
                    'path': path,
                    'timestamp': time.time()
                })
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error unwatching path {path}: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get file system service statistics.
        
        Returns:
            Dictionary containing service statistics
        """
        return {
            **self.stats,
            'indexed_files': len(self.file_index),
            'watched_paths': len(self.watched_paths),
            'search_index_size': len(self.search_index),
            'root_path': self.root_path,
            'max_file_size': self.max_file_size,
            'timestamp': time.time()
        }



    async def validate_path(self, path: str) -> bool:
        """Validate if a path is safe to access.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Resolve path and check if it's within root
            resolved_path = os.path.abspath(path)
            return resolved_path.startswith(self.root_path)
        except Exception:
            return False


# Global filesystem service instance
_filesystem_service: Optional[FileSystemService] = None


async def get_filesystem_service() -> FileSystemService:
    """Get the global filesystem service instance.
    
    Returns:
        FileSystemService instance
    """
    global _filesystem_service
    if _filesystem_service is None:
        # Resolve WORKSPACE_ROOT robustly and consistently across environments
        import os
        from pathlib import Path

        # 1) Respect explicit env vars if set
        workspace_root = (
            os.environ.get('WORKSPACE_ROOT')
            or os.environ.get('ICOTES_WORKSPACE_PATH')
        )

        # 2) If not provided, search upwards from this file for a parent that contains a 'workspace' dir
        if not workspace_root:
            current = Path(__file__).resolve()
            for parent in list(current.parents):
                candidate = parent / 'workspace'
                if candidate.is_dir():
                    workspace_root = str(candidate)
                    break

        # 3) Fallbacks commonly used in Docker/dev
        if not workspace_root:
            if Path('/app/workspace').exists():
                workspace_root = '/app/workspace'
            else:
                # Last resort: project cwd workspace
                workspace_root = str(Path.cwd() / 'workspace')

        # Ensure the directory exists to allow watchdog to attach
        try:
            Path(workspace_root).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to ensure workspace directory exists at {workspace_root}: {e}")

        # Export for other modules started later in the process
        os.environ['WORKSPACE_ROOT'] = workspace_root
        logger.info(f"[FS] Using WORKSPACE_ROOT: {workspace_root}")

        _filesystem_service = FileSystemService(root_path=workspace_root)
        await _filesystem_service.initialize()
    return _filesystem_service


async def shutdown_filesystem_service():
    """Shutdown the global filesystem service instance."""
    global _filesystem_service
    if _filesystem_service:
        await _filesystem_service.shutdown()
        _filesystem_service = None
