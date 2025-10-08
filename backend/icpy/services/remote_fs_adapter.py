"""
Remote FileSystem Adapter (SFTP)

Phase 5: Provide a filesystem implementation backed by an active SSH hop via
AsyncSSH SFTP client. This adapter mirrors the methods used by REST endpoints
so the Explorer can transparently operate on the remote host when connected.

Notes:
- Emits fs.* events via the message broker similar to the local service.
- Path handling: absolute paths are treated as remote absolute; relative paths
  are resolved against the hop session cwd if available, else '/'.
- No watchdog support remotely; events are only emitted on API mutations.
"""

from __future__ import annotations

import asyncio
import logging
import os
import posixpath
import stat
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple, AsyncIterator, Coroutine, TypeVar
from types import SimpleNamespace

from .hop_service import get_hop_service, ASYNCSSH_AVAILABLE, OPERATION_TIMEOUT
from .filesystem_service import FileInfo, FileType, FilePermission
from ..core.message_broker import get_message_broker

logger = logging.getLogger(__name__)

T = TypeVar('T')

async def _with_timeout(coro: Coroutine[Any, Any, T], timeout: float = None, operation: str = "operation") -> T:
    """Phase 8: Wrap async operations with timeout and better error messages."""
    if timeout is None:
        timeout = OPERATION_TIMEOUT
    
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Remote {operation} timed out after {timeout}s")


class RemoteFileSystemAdapter:
    """SFTP-backed filesystem adapter implementing a subset of FileSystemService.

    Only the methods used by the REST API and Explorer UI are implemented.
    """

    def __init__(self) -> None:
        self._hop = None
        self._message_broker = None
        # Expose a root concept for REST helpers; use '/' as remote root
        self.root_path: str = "/"
        self.is_remote: bool = True

    async def initialize(self):
        self._hop = await get_hop_service()
        self._message_broker = await get_message_broker()
        return self

    # ------------- helpers -------------
    def _resolve(self, path: str) -> str:
        """Resolve path against remote cwd if relative."""
        if not path:
            return self._get_cwd()
        if path.startswith('/'):
            return posixpath.normpath(path)
        base = self._get_cwd()
        return posixpath.normpath(posixpath.join(base, path))

    def _get_cwd(self) -> str:
        try:
            session = self._hop.status() if self._hop else None
            if session and session.cwd:
                return session.cwd
        except Exception:
            pass
        return "/"

    def _sftp(self):
        if not ASYNCSSH_AVAILABLE:
            return None
        if not self._hop:
            return None
        # Access the live SFTP client; HopService ensures lifecycle
        # Use method call instead of getattr to ensure it works correctly in Docker
        return self._hop.get_active_sftp()

    async def _publish(self, topic: str, payload: Dict[str, Any]):
        try:
            if self._message_broker is None:
                self._message_broker = await get_message_broker()
            await self._message_broker.publish(topic, payload)
        except Exception as e:
            logger.debug(f"[RemoteFS] publish error {topic}: {e}")

    @staticmethod
    def _is_dot_entry(name: str) -> bool:
        return name in ('.', '..')

    async def _to_file_info(self, sftp, path: str, st) -> Optional[FileInfo]:
        try:
            name = posixpath.basename(path)
            # AsyncSSH SFTPAttrs may expose permissions/size/mtime/atime/uid/gid
            mode = getattr(st, 'st_mode', None)
            if mode is None:
                mode = getattr(st, 'permissions', 0)
            is_dir = stat.S_ISDIR(mode)
            is_lnk = stat.S_ISLNK(mode)
            ftype = FileType.DIRECTORY if is_dir else FileType.CODE if name.endswith(('.py','.js','.ts','.tsx','.jsx','.md','.txt','.json','.yaml','.yml','.toml','.html','.css','.sh','.bash','.zsh')) else FileType.BINARY
            perms: List[FilePermission] = []
            if mode & stat.S_IRUSR:
                perms.append(FilePermission.READ)
            if mode & stat.S_IWUSR:
                perms.append(FilePermission.WRITE)
            if mode & stat.S_IXUSR:
                perms.append(FilePermission.EXECUTE)
            size = getattr(st, 'st_size', None)
            if size is None:
                size = getattr(st, 'size', 0) or 0
            return FileInfo(
                path=path,
                name=name,
                size=size,
                type=ftype,
                mime_type="application/octet-stream",
                created_at=getattr(st, 'st_ctime', None) or getattr(st, 'ctime', None) or time.time(),
                modified_at=getattr(st, 'st_mtime', None) or getattr(st, 'mtime', None) or time.time(),
                accessed_at=getattr(st, 'st_atime', None) or getattr(st, 'atime', None) or time.time(),
                permissions=perms,
                owner=str(getattr(st, 'st_uid', None) or getattr(st, 'uid', 0)),
                group=str(getattr(st, 'st_gid', None) or getattr(st, 'gid', 0)),
                is_directory=is_dir,
                is_symlink=is_lnk,
                is_hidden=name.startswith('.'),
                extension=posixpath.splitext(name)[1].lower(),
                content_hash="",
                metadata={"remote": True}
            )
        except Exception as e:
            logger.debug(f"[RemoteFS] to_file_info error for {path}: {e}")
            return None

    # ------------- core API -------------
    async def list_directory(self, dir_path: str, include_hidden: bool = False, recursive: bool = False) -> List[FileInfo]:
        sftp = self._sftp()
        logger.info("[RemoteFS] list_directory dir=%s sftp_available=%s", dir_path, bool(sftp))
        if not sftp:
            return []
        path = self._resolve(dir_path)
        try:
            result: List[FileInfo] = []
            async def iter_dir(p: str):
                # Prefer readdir which returns SFTPName entries with attrs
                try:
                    entries = await sftp.readdir(p)
                    for entry in entries:
                        yield entry.filename, getattr(entry, 'attrs', None)
                except Exception:
                    # Fallback to list names and stat each
                    names = await sftp.listdir(p)
                    for nm in names:
                        fullp = posixpath.join(p, nm)
                        try:
                            attrs = await sftp.stat(fullp)
                        except Exception:
                            attrs = None
                        yield nm, attrs

            if recursive:
                # Walk recursively using manual stack
                stack = [path]
                visited = set()
                while stack:
                    cur = stack.pop()
                    if cur in visited:
                        continue
                    visited.add(cur)
                    try:
                        async for name, attrs in _async_generator_wrapper(iter_dir(cur)):
                            if self._is_dot_entry(name):
                                continue
                            if not include_hidden and name.startswith('.'):
                                continue
                            full = posixpath.join(cur, name)
                            # Ensure attrs available
                            if attrs is None:
                                try:
                                    attrs = await sftp.stat(full)
                                except Exception:
                                    attrs = None
                            fi = await self._to_file_info(sftp, full, attrs or SimpleNamespace())
                            if fi:
                                result.append(fi)
                                # Avoid following symlinks to prevent loops
                                if fi.is_directory and not fi.is_symlink:
                                    stack.append(full)
                    except Exception:
                        continue
            else:
                async for name, attrs in _async_generator_wrapper(iter_dir(path)):
                    if self._is_dot_entry(name):
                        continue
                    if not include_hidden and name.startswith('.'):
                        continue
                    full = posixpath.join(path, name)
                    if attrs is None:
                        try:
                            attrs = await sftp.stat(full)
                        except Exception:
                            attrs = None
                    fi = await self._to_file_info(sftp, full, attrs or SimpleNamespace())
                    if fi:
                        result.append(fi)
            return result
        except Exception as e:
            logger.error(f"[RemoteFS] list_directory error {path}: {e}")
            return []

    async def read_file(self, file_path: str, encoding: str = 'utf-8') -> Optional[str]:
        sftp = self._sftp()
        logger.info("[RemoteFS] read_file path=%s sftp_available=%s", file_path, bool(sftp))
        if not sftp:
            return None
        path = self._resolve(file_path)
        try:
            # Phase 8: Add timeout protection
            async with sftp.open(path, 'rb') as f:
                data = await _with_timeout(f.read(), operation=f"read file {path}")
            try:
                text = data.decode(encoding)
            except Exception:
                text = data.decode('utf-8', errors='replace')
            await self._publish('fs.file_read', {'file_path': path, 'size': len(text), 'encoding': encoding, 'timestamp': time.time()})
            return text
        except TimeoutError as e:
            logger.error(f"[RemoteFS] read_file timeout {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"[RemoteFS] read_file error {path}: {e}")
            return None

    async def write_file(self, file_path: str, content: str, encoding: str = 'utf-8', create_dirs: bool = True) -> bool:
        sftp = self._sftp()
        if not sftp:
            return False
        path = self._resolve(file_path)
        try:
            if create_dirs:
                dirp = posixpath.dirname(path)
                await _with_timeout(self._mkdirs(sftp, dirp), operation="create directories")
            data = content.encode(encoding)
            # Phase 8: Add timeout protection
            async with sftp.open(path, 'wb') as f:
                await _with_timeout(f.write(data), operation=f"write file {path}")
            await self._publish('fs.file_written', {'file_path': path, 'size': len(data), 'encoding': encoding, 'created': False, 'timestamp': time.time()})
            return True
        except Exception as e:
            logger.error(f"[RemoteFS] write_file error {path}: {e}")
            return False

    async def create_directory(self, dir_path: str, parents: bool = True) -> bool:
        sftp = self._sftp()
        if not sftp:
            return False
        path = self._resolve(dir_path)
        try:
            if parents:
                await self._mkdirs(sftp, path)
            else:
                await sftp.mkdir(path)
            await self._publish('fs.directory_created', {'dir_path': path, 'parents': parents, 'timestamp': time.time()})
            return True
        except Exception as e:
            logger.error(f"[RemoteFS] create_directory error {path}: {e}")
            return False

    async def delete_file(self, file_path: str) -> bool:
        sftp = self._sftp()
        if not sftp:
            return False
        path = self._resolve(file_path)
        try:
            # Determine if directory
            st = await sftp.stat(path)
            mode = getattr(st, 'st_mode', None)
            if mode is None:
                mode = getattr(st, 'permissions', 0)
            if stat.S_ISDIR(mode):
                await self._rmtree(sftp, path)
            else:
                await sftp.remove(path)
            await self._publish('fs.file_deleted', {'file_path': path, 'is_directory': stat.S_ISDIR(mode), 'timestamp': time.time()})
            return True
        except Exception as e:
            logger.error(f"[RemoteFS] delete_file error {path}: {e}")
            return False

    async def move_file(self, src_path: str, dest_path: str, overwrite: bool = False) -> bool:
        sftp = self._sftp()
        if not sftp:
            return False
        src = self._resolve(src_path)
        dst = self._resolve(dest_path)
        try:
            if overwrite:
                try:
                    st = await sftp.stat(dst)
                    # SFTP attrs might expose st_mode or permissions
                    mode = getattr(st, 'st_mode', None)
                    if mode is None:
                        mode = getattr(st, 'permissions', 0)
                    if stat.S_ISDIR(mode):
                        await self._rmtree(sftp, dst)
                    else:
                        await sftp.remove(dst)
                except Exception:
                    pass
            await sftp.rename(src, dst)
            await self._publish('fs.file_moved', {'src_path': src, 'dest_path': dst, 'timestamp': time.time()})
            return True
        except Exception as e:
            logger.error(f"[RemoteFS] move_file error {src} -> {dst}: {e}")
            return False

    async def copy_file(self, src_path: str, dest_path: str) -> bool:
        """Naive remote copy (same host): read then write. Directories copied recursively."""
        sftp = self._sftp()
        if not sftp:
            return False
        src = self._resolve(src_path)
        dst = self._resolve(dest_path)
        try:
            st = await sftp.stat(src)
            mode = getattr(st, 'st_mode', None)
            if mode is None:
                mode = getattr(st, 'permissions', 0)
            if stat.S_ISDIR(mode):
                await self._copytree(sftp, src, dst)
            else:
                await self._mkdirs(sftp, posixpath.dirname(dst))
                async with sftp.open(src, 'rb') as rf:
                    data = await rf.read()
                async with sftp.open(dst, 'wb') as wf:
                    await wf.write(data)
            await self._publish('fs.file_copied', {'src_path': src, 'dest_path': dst, 'timestamp': time.time()})
            return True
        except Exception as e:
            logger.error(f"[RemoteFS] copy_file error {src} -> {dst}: {e}")
            return False

    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        sftp = self._sftp()
        if not sftp:
            return None
        path = self._resolve(file_path)
        try:
            st = await sftp.stat(path)
            return await self._to_file_info(sftp, path, st)
        except Exception as e:
            logger.error(f"[RemoteFS] get_file_info error {path}: {e}")
            return None

    async def search_files(self, query: str, search_content: bool = True, file_types: Optional[List[FileType]] = None,
                           max_results: int = 100) -> List[Dict[str, Any]]:
        """Simple remote search by filename; optional shallow content search for small files."""
        try:
            sftp = self._sftp()
            if not sftp:
                return []
            root = self._get_cwd()
            results: List[Dict[str, Any]] = []
            stack = [root]
            q = query.lower()
            while stack and len(results) < max_results:
                cur = stack.pop()
                try:
                    try:
                        entries = await sftp.readdir(cur)
                        iterable = [(e.filename, getattr(e, 'attrs', None)) for e in entries]
                    except Exception:
                        names = await sftp.listdir(cur)
                        iterable = []
                        for nm in names:
                            fullp = posixpath.join(cur, nm)
                            try:
                                attrs = await sftp.stat(fullp)
                            except Exception:
                                attrs = None
                            iterable.append((nm, attrs))
                    for name, attrs in iterable:
                        if self._is_dot_entry(name):
                            continue
                        full = posixpath.join(cur, name)
                        mode = getattr(attrs, 'st_mode', None) if attrs else None
                        if mode is None:
                            mode = getattr(attrs, 'permissions', 0) if attrs else 0
                        is_dir = stat.S_ISDIR(mode)
                        if q in name.lower():
                            fi = await self._to_file_info(sftp, full, attrs or SimpleNamespace())
                            if fi:
                                results.append({'file_info': fi.to_dict(), 'matches': [f"Filename: {name}"], 'score': 1.0, 'context': {}})
                        if is_dir:
                            stack.append(full)
                except Exception:
                    continue
            await self._publish('fs.search_performed', {'query': query, 'search_content': search_content, 'result_count': len(results), 'timestamp': time.time()})
            return results
        except Exception as e:
            logger.error(f"[RemoteFS] search_files error: {e}")
            return []

    # -------- streaming helpers for downloads --------
    async def stream_file(self, path: str, chunk_size: int = 1024 * 1024) -> AsyncIterator[bytes]:
        sftp = self._sftp()
        if not sftp:
            return
        abs_path = self._resolve(path)
        async with sftp.open(abs_path, 'rb') as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    # ------------- internal ops -------------
    async def _mkdirs(self, sftp, path: str):
        if not path or path == '/':
            return
        parts = []
        p = path
        while p and p != '/':
            parts.append(p)
            p = posixpath.dirname(p)
        for d in reversed(parts):
            try:
                await sftp.mkdir(d)
            except Exception:
                # exists or race
                pass

    async def _rmtree(self, sftp, path: str):
        try:
            try:
                entries = await sftp.readdir(path)
                iterable = [(e.filename, getattr(e, 'attrs', None)) for e in entries]
            except Exception:
                names = await sftp.listdir(path)
                iterable = []
                for nm in names:
                    fullp = posixpath.join(path, nm)
                    try:
                        attrs = await sftp.stat(fullp)
                    except Exception:
                        attrs = None
                    iterable.append((nm, attrs))
            for name, attrs in iterable:
                if self._is_dot_entry(name):
                    continue
                full = posixpath.join(path, name)
                mode = getattr(attrs, 'st_mode', None) if attrs else None
                if mode is None:
                    mode = getattr(attrs, 'permissions', 0) if attrs else 0
                if stat.S_ISDIR(mode):
                    await self._rmtree(sftp, full)
                else:
                    try:
                        await sftp.remove(full)
                    except Exception:
                        pass
            try:
                await sftp.rmdir(path)
            except Exception:
                pass
        except Exception:
            # fall back: attempt remove
            try:
                await sftp.remove(path)
            except Exception:
                pass

    async def _copytree(self, sftp, src: str, dst: str):
        await self._mkdirs(sftp, dst)
        try:
            entries = await sftp.readdir(src)
            iterable = [(e.filename, getattr(e, 'attrs', None)) for e in entries]
        except Exception:
            names = await sftp.listdir(src)
            iterable = []
            for nm in names:
                sp = posixpath.join(src, nm)
                try:
                    attrs = await sftp.stat(sp)
                except Exception:
                    attrs = None
                iterable.append((nm, attrs))
        for name, attrs in iterable:
            if self._is_dot_entry(name):
                continue
            s = posixpath.join(src, name)
            d = posixpath.join(dst, name)
            mode = getattr(attrs, 'st_mode', None) if attrs else None
            if mode is None:
                mode = getattr(attrs, 'permissions', 0) if attrs else 0
            if stat.S_ISDIR(mode):
                await self._copytree(sftp, s, d)
            else:
                async with sftp.open(s, 'rb') as rf:
                    data = await rf.read()
                async with sftp.open(d, 'wb') as wf:
                    await wf.write(data)


# Helper to iterate over async generator from nested function
async def _async_generator_wrapper(agen_factory):
    agen = agen_factory
    # If agen_factory is a coroutine function returning an iterable, await it
    if asyncio.iscoroutinefunction(agen_factory):
        agen = await agen_factory()
    else:
        agen = agen_factory
    # If agen is a coroutine (awaitable), await to get iterable
    if asyncio.iscoroutine(agen):
        agen = await agen
    # Try async iteration
    try:
        async for item in agen:
            yield item
        return
    except TypeError:
        # Not an async iterator, treat as sync iterable
        for item in agen:
            yield item


async def get_remote_filesystem_adapter() -> RemoteFileSystemAdapter:
    adapter = RemoteFileSystemAdapter()
    return await adapter.initialize()
