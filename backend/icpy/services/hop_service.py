"""
Hop Service: Manage SSH credentials, keys, and active hop session.

Security:
- Passwords and passphrases are treated as write-only and never persisted or returned
- Private keys are stored under workspace/.icotes/ssh/keys with 0600 permissions
- No secrets are logged
- Workspace-based storage ensures Docker container persistence
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import stat
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

from ..utils.logging import sanitize_log_message, mask_credential_value
from ..utils.ssh_config_parser import parse_ssh_config, SSHConfigEntry
from ..utils.ssh_config_writer import generate_ssh_config, credential_to_config_entry
from ..scripts.migrate_hop_config import should_migrate, migrate_credentials_to_config

try:
    import asyncssh  # Phase 2: real connectivity
    ASYNCSSH_AVAILABLE = True
except Exception:  # pragma: no cover - dependency issues handled by tests
    asyncssh = None
    ASYNCSSH_AVAILABLE = False


logger = logging.getLogger(__name__)

# Phase 8: Configuration for timeouts and reconnection
CONNECTION_TIMEOUT = int(os.environ.get('HOP_CONNECTION_TIMEOUT', '30'))
OPERATION_TIMEOUT = int(os.environ.get('HOP_OPERATION_TIMEOUT', '60'))
RECONNECT_MAX_RETRIES = int(os.environ.get('HOP_RECONNECT_MAX_RETRIES', '3'))
RECONNECT_BACKOFF_BASE = float(os.environ.get('HOP_RECONNECT_BACKOFF_BASE', '2'))
DEBUG_MODE = os.environ.get('HOP_DEBUG_MODE', 'false').lower() == 'true'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _workspace_root() -> Path:
    """Get the workspace root directory."""
    workspace_root = os.environ.get('WORKSPACE_ROOT')
    if not workspace_root:
        # Fallback: search upwards for workspace dir
        current = Path(__file__).resolve()
        for parent in list(current.parents):
            candidate = parent / 'workspace'
            if candidate.is_dir():
                workspace_root = str(candidate)
                break
    
    if not workspace_root:
        # Docker fallback
        if Path('/app/workspace').exists():
            workspace_root = '/app/workspace'
        else:
            workspace_root = str(Path.cwd() / 'workspace')
    
    return Path(workspace_root)


def _app_data_dir() -> Path:
    """Return the base directory for icotes SSH data in the workspace.

    We keep hop-related files under workspace/.icotes/ssh for Docker persistence.
    This ensures credentials survive container restarts when workspace is mounted as a volume.
    """
    base = _workspace_root() / '.icotes' / 'ssh'
    base.mkdir(parents=True, exist_ok=True)
    # Set safe dir perms (700) if possible
    try:
        os.chmod(base, 0o700)
    except Exception:
        pass
    return base


def _keys_dir() -> Path:
    d = _app_data_dir() / "keys"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except Exception:
        pass
    return d


def _creds_file() -> Path:
    return _app_data_dir() / "credentials.json"


def _hop_dir() -> Path:
    """Return the hop directory for config file storage."""
    hop = _workspace_root() / '.icotes' / 'hop'
    hop.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(hop, 0o700)
    except Exception:
        pass
    return hop


def _config_file() -> Path:
    """Return the SSH config file path."""
    return _hop_dir() / "config"


@dataclass
class SSHCredential:
    id: str
    name: str
    host: str
    port: int = 22
    username: str = ""
    auth: str = "password"  # "password" | "privateKey" | "agent"
    # write-only fields (never persisted/returned)
    password: Optional[str] = field(default=None, repr=False)
    passphrase: Optional[str] = field(default=None, repr=False)
    privateKeyId: Optional[str] = None
    defaultPath: Optional[str] = None
    createdAt: str = field(default_factory=_now_iso)
    updatedAt: str = field(default_factory=_now_iso)

    def to_public_dict(self) -> Dict:
        d = asdict(self)
        # Remove secrets
        d.pop("password", None)
        d.pop("passphrase", None)
        return d


@dataclass
class HopSession:
    contextId: str = "local"  # "local" or credential id
    credentialId: Optional[str] = None
    credentialName: Optional[str] = None  # Friendly display name
    status: str = "disconnected"  # disconnected|connecting|connected|error|reconnecting
    cwd: str = "/"
    lastError: Optional[str] = None
    # Helpful fields for UI/telemetry (non-secret)
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    # Phase 8: Reconnection tracking
    reconnectAttempt: int = 0
    lastConnectedAt: Optional[str] = None
    connectionQuality: str = "unknown"  # unknown|good|degraded|poor


class HopService:
    """Manage credentials & multiple simultaneous hop sessions with active context switching."""

    def __init__(self) -> None:
        self._creds: Dict[str, SSHCredential] = {}
        
        # Multi-session support: Map of context_id -> session data
        self._sessions: Dict[str, HopSession] = {}
        self._connections: Dict[str, any] = {}  # context_id -> asyncssh connection
        self._sftp_clients: Dict[str, any] = {}  # context_id -> SFTP client
        
        # Active context tracking
        self._active_context_id: str = "local"
        
        # Initialize local session
        self._sessions["local"] = HopSession(contextId="local", status="connected")
        
        self._lock = asyncio.Lock()
        
        # Phase 8: Reconnection state (per-session)
        self._reconnect_tasks: Dict[str, asyncio.Task] = {}
        self._last_credentials: Dict[str, Dict] = {}  # context_id -> credential data
        self._connection_start_times: Dict[str, float] = {}
        self._loop = None  # event loop where connection/sftp were created
        
        # Phase 2: Config format tracking
        self._config_format: str = "json"  # "json" or "config"
        
        # Phase 3: Auto-migrate on startup if needed
        self._run_auto_migration()
        
        self._load_credentials()

    def _run_auto_migration(self) -> None:
        """Run automatic migration from JSON to config format if needed."""
        workspace = _workspace_root()
        if should_migrate(workspace):
            logger.info("[HopService] Auto-migrating credentials from JSON to SSH config format...")
            try:
                result = migrate_credentials_to_config(workspace)
                logger.info(
                    f"[HopService] Migration completed: {result.credentials_migrated} credentials, "
                    f"{result.keys_renamed} keys renamed"
                )
                if result.warnings:
                    for warning in result.warnings:
                        logger.warning(f"[HopService] Migration warning: {warning}")
            except Exception as e:
                logger.error(f"[HopService] Migration failed: {e}", exc_info=True)
                # Don't fail startup if migration fails - old JSON will still work

    # -------------------- Persistence --------------------
    def _load_credentials(self) -> None:
        """Load credentials from config file (preferred) or JSON (fallback)."""
        config_path = _config_file()
        json_path = _creds_file()
        
        # Phase 2: Prefer config format if it exists
        if config_path.exists():
            self._load_from_config()
        elif json_path.exists():
            self._load_from_json()
        else:
            # No credentials yet
            self._creds = {}
            self._config_format = "json"
            logger.info("[HopService] No credentials found (will use JSON format)")
    
    def _load_from_config(self) -> None:
        """Load credentials from SSH config file."""
        try:
            config_path = _config_file()
            config_text = config_path.read_text(encoding="utf-8")
            entries = parse_ssh_config(config_text)
            
            result: Dict[str, SSHCredential] = {}
            for entry in entries:
                # Convert entry to credential dict
                cred_dict = entry.to_credential_dict()
                
                # Skip local context (it's always present)
                if cred_dict.get('id') == 'local':
                    continue
                
                # Generate ID if missing
                if not cred_dict.get('id'):
                    cred_dict['id'] = str(uuid.uuid4())
                
                # Create SSHCredential
                cred = SSHCredential(
                    id=cred_dict['id'],
                    name=cred_dict.get('name', ''),
                    host=cred_dict.get('host', ''),
                    port=int(cred_dict.get('port', 22)),
                    username=cred_dict.get('username', ''),
                    auth=cred_dict.get('auth', 'password'),
                    privateKeyId=cred_dict.get('privateKeyId'),
                    defaultPath=cred_dict.get('defaultPath'),
                    createdAt=cred_dict.get('createdAt', _now_iso()),
                    updatedAt=cred_dict.get('updatedAt', _now_iso()),
                )
                result[cred.id] = cred
            
            self._creds = result
            self._config_format = "config"
            logger.info(f"[HopService] Loaded {len(result)} credentials from config file")
            
        except Exception as e:
            logger.error(f"Failed to load credentials from config: {e}")
            self._creds = {}
            self._config_format = "config"
    
    def _load_from_json(self) -> None:
        """Load credentials from JSON file (legacy format - DEPRECATED)."""
        path = _creds_file()
        try:
            # Phase 5: JSON format is deprecated
            logger.warning(
                "[HopService] Loading from legacy JSON format. "
                "This format is deprecated. Config file will be generated automatically."
            )
            
            data = json.loads(path.read_text(encoding="utf-8"))
            result: Dict[str, SSHCredential] = {}
            for item in data:
                # Secrets are not persisted; construct without them
                cred = SSHCredential(
                    id=item["id"],
                    name=item.get("name", ""),
                    host=item.get("host", ""),
                    port=int(item.get("port", 22)),
                    username=item.get("username", ""),
                    auth=item.get("auth", "password"),
                    privateKeyId=item.get("privateKeyId"),
                    defaultPath=item.get("defaultPath"),
                    createdAt=item.get("createdAt", _now_iso()),
                    updatedAt=item.get("updatedAt", _now_iso()),
                )
                result[cred.id] = cred
            self._creds = result
            self._config_format = "json"
            logger.info(f"[HopService] Loaded {len(result)} credentials from legacy JSON file")
            
            # Phase 5: Always generate config file when loading from JSON
            if result:
                self._save_to_config()
                logger.info(
                    "[HopService] Generated config file at workspace/.icotes/hop/config. "
                    "Future saves will only update the config file."
                )
                
        except Exception as e:
            logger.error(f"Failed to load credentials from JSON: {e}")
            self._creds = {}
            self._config_format = "json"

    def _save_credentials(self) -> None:
        """Save credentials to config format only (Phase 5: JSON deprecated)."""
        # Phase 5: Only save to config format
        # JSON format is deprecated - kept as read-only fallback
        self._save_to_config()
    
    def _save_to_config(self) -> None:
        """Save credentials to SSH config file."""
        try:
            config_path = _config_file()
            
            # Convert credentials to config entries
            entries = []
            for cred in self._creds.values():
                entry = credential_to_config_entry(cred)
                entries.append(entry)
            
            # Generate config text
            config_text = generate_ssh_config(entries)
            
            # Atomic write (write to temp, then rename)
            temp_path = config_path.with_suffix('.tmp')
            temp_path.write_text(config_text, encoding="utf-8")
            temp_path.replace(config_path)
            
            # Set permissions (600)
            try:
                os.chmod(config_path, 0o600)
            except Exception:
                pass
                
            logger.debug(f"[HopService] Saved {len(self._creds)} credentials to config file")
            
        except Exception as e:
            logger.error(f"Failed to save credentials to config: {e}")
    
    def _save_to_json(self) -> None:
        """Save credentials to JSON file (backup)."""
        path = _creds_file()
        try:
            serializable = []
            for cred in self._creds.values():
                d = cred.to_public_dict()
                serializable.append(d)
            path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
            logger.debug(f"[HopService] Saved {len(self._creds)} credentials to JSON backup")
        except Exception as e:
            logger.error(f"Failed to save credentials to JSON: {e}")
    
    def get_config_format(self) -> str:
        """Return current config format: 'json' or 'config'."""
        return self._config_format

    # -------------------- Key management --------------------
    def store_private_key(self, key_bytes: bytes) -> str:
        """Store a private key and return its keyId. Sets 0600 perms."""
        key_id = str(uuid.uuid4())
        filename = _keys_dir() / key_id
        with open(filename, "wb") as f:
            f.write(key_bytes)
        # Set 0600 permissions
        try:
            os.chmod(filename, 0o600)
        except Exception:
            pass
        return key_id

    def get_key_path(self, key_id: str) -> Path:
        return _keys_dir() / key_id

    # -------------------- Credentials CRUD --------------------
    def list_credentials(self) -> List[Dict]:
        return [c.to_public_dict() for c in self._creds.values()]

    def get_credential(self, cred_id: str) -> Optional[Dict]:
        c = self._creds.get(cred_id)
        return c.to_public_dict() if c else None

    def create_credential(self, data: Dict) -> Dict:
        cred_id = data.get("id") or str(uuid.uuid4())
        cred = SSHCredential(
            id=cred_id,
            name=data.get("name", cred_id),
            host=data["host"],
            port=int(data.get("port", 22)),
            username=data.get("username", ""),
            auth=data.get("auth", "password"),
            privateKeyId=data.get("privateKeyId"),
            defaultPath=data.get("defaultPath"),
        )
        cred.updatedAt = _now_iso()
        self._creds[cred.id] = cred
        self._save_credentials()
        return cred.to_public_dict()

    def update_credential(self, cred_id: str, data: Dict) -> Optional[Dict]:
        cred = self._creds.get(cred_id)
        if not cred:
            return None
        # Update fields
        for field_name in ["name", "host", "username", "auth", "defaultPath"]:
            if field_name in data:
                setattr(cred, field_name, data[field_name])
        if "port" in data:
            port_val = data["port"]
            if port_val is not None:
                try:
                    cred.port = int(port_val) or 22
                except (TypeError, ValueError):
                    logger.debug(f"Invalid port value: {port_val}, keeping existing")
                    pass
        if "privateKeyId" in data:
            cred.privateKeyId = data["privateKeyId"]
        cred.updatedAt = _now_iso()
        self._save_credentials()
        return cred.to_public_dict()

    def delete_credential(self, cred_id: str) -> bool:
        removed = self._creds.pop(cred_id, None) is not None
        if removed:
            self._save_credentials()
        return removed

    # -------------------- Session / Connectivity --------------------
    async def connect(self, cred_id: str, *, password: Optional[str] = None, passphrase: Optional[str] = None) -> HopSession:
        """Connect to remote host using credential. Supports multiple simultaneous connections."""
        async with self._lock:
            cred = self._creds.get(cred_id)
            if not cred:
                raise ValueError("Credential not found")
            
            context_id = cred.id

            # Cancel any ongoing reconnection task for this context
            if context_id in self._reconnect_tasks and not self._reconnect_tasks[context_id].done():
                self._reconnect_tasks[context_id].cancel()
                self._reconnect_tasks.pop(context_id, None)

            # Create or update session for this context
            session = HopSession(
                contextId=context_id,
                credentialId=cred.id,
                credentialName=cred.name,  # Set the friendly name for UI display
                status="connecting",
                cwd=cred.defaultPath or "/",
                host=cred.host,
                port=cred.port,
                username=cred.username or None,
            )
            session.lastError = None
            self._sessions[context_id] = session

            # Store credentials for potential reconnection
            self._last_credentials[context_id] = {
                'cred_id': cred_id,
                'password': password,
                'passphrase': passphrase,
            }

            # Close any existing connection for this context
            await self._close_connection(context_id)

            if not ASYNCSSH_AVAILABLE:
                # Phase 1 fallback: stubbed connected state without real SSH
                session.status = "connected"
                self._sessions[context_id] = session
                self._active_context_id = context_id  # Switch to new connection
                return session

            try:
                # Phase 8: Sanitize logging of sensitive connection info
                safe_username = mask_credential_value(cred.username, show_prefix=2, show_suffix=2) if cred.username else '<auto>'
                log_msg = f"[HopService] Connecting to {cred.host}:{cred.port} as {safe_username} (auth={cred.auth})"
                logger.info(sanitize_log_message(log_msg))
                
                client_keys = None
                if cred.auth == "privateKey" and cred.privateKeyId:
                    key_path = str(self.get_key_path(cred.privateKeyId))
                    client_keys = [key_path]

                self._connection_start_times[context_id] = time.time()
                
                # Phase 8: Use configurable timeout
                # Record the event loop used to create the SSH/SFTP clients
                try:
                    self._loop = asyncio.get_running_loop()
                    logger.info("[HopService] connect loop id=%s", hex(id(self._loop)))
                except Exception:
                    self._loop = None
                conn = await asyncssh.connect(
                    host=cred.host,
                    port=cred.port or 22,
                    username=cred.username or None,
                    password=password if cred.auth == "password" else None,
                    client_keys=client_keys,
                    passphrase=passphrase if cred.auth == "privateKey" else None,
                    # Disable strict host key checking for development/trusted networks
                    # In production, you may want to manage known_hosts properly
                    known_hosts=None,
                    connect_timeout=CONNECTION_TIMEOUT,
                )
                self._connections[context_id] = conn
                
                try:
                    sftp = await asyncio.wait_for(
                        conn.start_sftp_client(),
                        timeout=OPERATION_TIMEOUT
                    )
                    self._sftp_clients[context_id] = sftp
                except asyncio.TimeoutError:
                    logger.warning(f"[HopService] SFTP client start timed out for {context_id}")
                    self._sftp_clients[context_id] = None
                except Exception as e:
                    logger.warning(f"[HopService] SFTP client start failed for {context_id}: {e}")
                    self._sftp_clients[context_id] = None

                session.status = "connected"
                session.lastConnectedAt = _now_iso()
                session.reconnectAttempt = 0
                session.connectionQuality = "good"
                self._sessions[context_id] = session
                
                # Determine remote home/cwd if not provided
                if not cred.defaultPath:
                    try:
                        # Prefer environment HOME
                        run_res = await asyncio.wait_for(
                            conn.run('printenv HOME', check=False),
                            timeout=5
                        )
                        home = (run_res.stdout or '').strip()
                        if not home:
                            # Fallback to pwd
                            run_res = await asyncio.wait_for(
                                conn.run('pwd', check=False),
                                timeout=5
                            )
                            home = (run_res.stdout or '').strip() or '/'
                        # Validate directory exists via SFTP if available
                        sftp = self._sftp_clients.get(context_id)
                        if sftp:
                            try:
                                await asyncio.wait_for(sftp.stat(home), timeout=5)
                                session.cwd = home
                            except Exception:
                                session.cwd = '/'
                        else:
                            session.cwd = home or '/'
                    except asyncio.TimeoutError:
                        logger.warning(f"[HopService] Home directory detection timed out for {context_id}")
                    except Exception as e:
                        logger.debug(f"[HopService] Home directory detection failed for {context_id}: {e}")
                        # Keep existing default
                        pass
                
                self._sessions[context_id] = session
                self._active_context_id = context_id  # Automatically switch to new connection
                        
                connection_time = time.time() - self._connection_start_times[context_id]
                logger.info(f"[HopService] Connected to {cred.host}:{cred.port} in {connection_time:.2f}s (context: {context_id})")
                return session
            except asyncio.TimeoutError:
                error_msg = f"Connection to {cred.host}:{cred.port} timed out after {CONNECTION_TIMEOUT}s"
                logger.error(f"[HopService] {error_msg}")
                session.status = "error"
                session.lastError = error_msg
                self._sessions[context_id] = session
                await self._close_connection(context_id)
                return session
            except Exception as e:
                # Phase 8: Sanitize error messages for sensitive info
                error_msg = sanitize_log_message(str(e))
                logger.error(f"[HopService] SSH connect error to {cred.host}:{cred.port} - {error_msg}")
                session.status = "error"
                session.lastError = self._format_user_friendly_error(e)
                self._sessions[context_id] = session
                await self._close_connection(context_id)
                return session
    def get_active_loop(self):
        return self._loop

    @asynccontextmanager
    async def ephemeral_sftp(self, context_id: Optional[str] = None):
        """Open a short-lived SFTP client in the CURRENT async loop.

        This avoids cross-loop issues by creating a fresh SSH/SFTP session
        bound to the caller's event loop. Closes both SFTP and SSH on exit.
        """
        if context_id is None:
            context_id = self._active_context_id

        if context_id == "local" or not ASYNCSSH_AVAILABLE:
            yield None
            return

        cred = self._creds.get(context_id)
        if not cred:
            yield None
            return

        # Retrieve last-used secret material (password/passphrase) if any
        last = self._last_credentials.get(context_id, {})
        password = last.get('password') if cred.auth == 'password' else None
        passphrase = last.get('passphrase') if cred.auth == 'privateKey' else None
        client_keys = None
        if cred.auth == 'privateKey' and cred.privateKeyId:
            key_path = str(self.get_key_path(cred.privateKeyId))
            client_keys = [key_path]

        conn = None
        sftp = None
        try:
            conn = await asyncssh.connect(
                host=cred.host,
                port=cred.port or 22,
                username=cred.username or None,
                password=password,
                client_keys=client_keys,
                passphrase=passphrase,
                known_hosts=None,
                connect_timeout=CONNECTION_TIMEOUT,
            )
            try:
                sftp = await asyncio.wait_for(conn.start_sftp_client(), timeout=OPERATION_TIMEOUT)
            except Exception as e:
                logger.error(f"[HopService] ephemeral SFTP start failed for {context_id}: {e}")
                try:
                    if conn:
                        conn.close()
                        await asyncio.wait_for(conn.wait_closed(), timeout=2.0)
                except Exception:
                    pass
                yield None
                return

            yield sftp
        finally:
            # Cleanup ephemeral resources
            try:
                if sftp:
                    res = sftp.exit()
                    if inspect.isawaitable(res):
                        try:
                            await asyncio.wait_for(res, timeout=1.0)
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
                    try:
                        await asyncio.wait_for(conn.wait_closed(), timeout=2.0)
                    except Exception:
                        pass
            except Exception:
                pass

    @asynccontextmanager
    async def ephemeral_ssh(self, context_id: Optional[str] = None):
        """Open a short-lived SSH connection in the CURRENT async loop.

        This is analogous to ephemeral_sftp but yields the SSH connection itself.
        It avoids cross-loop issues by creating a fresh connection bound to the caller's loop.
        """
        if context_id is None:
            context_id = self._active_context_id

        if context_id == "local" or not ASYNCSSH_AVAILABLE:
            yield None
            return

        cred = self._creds.get(context_id)
        if not cred:
            yield None
            return

        # Retrieve last-used secret material (password/passphrase) if any
        last = self._last_credentials.get(context_id, {})
        password = last.get('password') if cred.auth == 'password' else None
        passphrase = last.get('passphrase') if cred.auth == 'privateKey' else None
        client_keys = None
        if cred.auth == 'privateKey' and cred.privateKeyId:
            key_path = str(self.get_key_path(cred.privateKeyId))
            client_keys = [key_path]

        conn = None
        try:
            conn = await asyncssh.connect(
                host=cred.host,
                port=cred.port or 22,
                username=cred.username or None,
                password=password,
                client_keys=client_keys,
                passphrase=passphrase,
                known_hosts=None,
                connect_timeout=CONNECTION_TIMEOUT,
            )
            yield conn
        finally:
            try:
                if conn:
                    conn.close()
                    try:
                        await asyncio.wait_for(conn.wait_closed(), timeout=2.0)
                    except Exception:
                        pass
            except Exception:
                pass

    def _format_user_friendly_error(self, error: Exception) -> str:
        """Phase 8: Convert technical SSH errors to user-friendly messages."""
        error_str = str(error).lower()
        
        if 'permission denied' in error_str or 'authentication failed' in error_str:
            return "Authentication failed. Please check your username, password, or private key."
        elif 'connection refused' in error_str:
            return "Connection refused. The SSH server may not be running or the port is incorrect."
        elif 'no route to host' in error_str or 'network unreachable' in error_str:
            return "Network unreachable. Please check the hostname and your network connection."
        elif 'timeout' in error_str or 'timed out' in error_str:
            return "Connection timed out. The server may be down or unreachable."
        elif 'host key' in error_str:
            return "Host key verification failed. The server's identity has changed (possible security risk)."
        else:
            # Return sanitized original error for unknown cases
            return sanitize_log_message(str(error))

    async def _close_connection(self, context_id: str):
        """Gracefully close SFTP and SSH connection for a specific context with timeouts and abort fallback.

        Args:
            context_id: The context ID to close connection for
        
        Rationale: In some cases (e.g., active remote PTY channels), a graceful
        close can hang indefinitely. Use short timeouts and escalate to abort()
        to guarantee forward progress and avoid memory growth from stuck tasks.
        """
        start_ts = time.time()
        used_abort = False
        sftp_closed = False
        
        sftp = self._sftp_clients.get(context_id)
        conn = self._connections.get(context_id)
        
        try:
            # Close SFTP first
            if sftp:
                try:
                    res = sftp.exit()
                    if inspect.isawaitable(res):
                        await asyncio.wait_for(res, timeout=1.5)
                    sftp_closed = True
                except Exception:
                    # Ignore SFTP close errors/timeouts
                    pass

            # Then close SSH connection
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                # Wait briefly for clean shutdown; fall back to abort
                try:
                    await asyncio.wait_for(conn.wait_closed(), timeout=2.5)
                except (asyncio.TimeoutError, Exception):
                    # Force-close if graceful close hangs due to open channels
                    try:
                        if hasattr(conn, 'abort'):
                            conn.abort()
                            used_abort = True
                    except Exception:
                        pass
                    # Best effort wait after abort
                    try:
                        await asyncio.wait_for(conn.wait_closed(), timeout=1.0)
                    except Exception:
                        pass
        finally:
            logger.info(
                "[HopService] _close_connection complete for %s in %.3fs (sftp_closed=%s, used_abort=%s)",
                context_id,
                time.time() - start_ts,
                sftp_closed,
                used_abort,
            )
            self._connections.pop(context_id, None)
            self._sftp_clients.pop(context_id, None)

    async def _attempt_reconnect(self, context_id: str) -> bool:
        """Phase 8: Attempt automatic reconnection with exponential backoff for a specific context."""
        if context_id not in self._last_credentials:
            return False
        
        last_cred = self._last_credentials[context_id]
        session = self._sessions.get(context_id)
        if not session:
            return False
            
        max_attempts = RECONNECT_MAX_RETRIES
        attempt = session.reconnectAttempt
        
        while attempt < max_attempts:
            attempt += 1
            session.reconnectAttempt = attempt
            session.status = "reconnecting"
            self._sessions[context_id] = session
            
            # Exponential backoff
            wait_time = min(RECONNECT_BACKOFF_BASE ** attempt, 30)  # Cap at 30s
            logger.info(f"[HopService] Reconnection attempt {attempt}/{max_attempts} for {context_id} in {wait_time:.1f}s")
            
            await asyncio.sleep(wait_time)
            
            try:
                result = await self.connect(
                    last_cred['cred_id'],
                    password=last_cred.get('password'),
                    passphrase=last_cred.get('passphrase')
                )
                
                if result.status == "connected":
                    logger.info(f"[HopService] Reconnection successful for {context_id} after {attempt} attempts")
                    return True
            except Exception as e:
                logger.warning(f"[HopService] Reconnection attempt {attempt} for {context_id} failed: {e}")
                continue
        
        logger.error(f"[HopService] Reconnection failed for {context_id} after {max_attempts} attempts")
        session.lastError = f"Failed to reconnect after {max_attempts} attempts"
        self._sessions[context_id] = session
        return False

    async def disconnect(self, context_id: Optional[str] = None) -> HopSession:
        """Disconnect a specific context or the active context if none specified.
        
        Args:
            context_id: Context to disconnect. If None, disconnects the active context.
        
        Returns:
            The active session after disconnection
        """
        async with self._lock:
            # If no context specified, disconnect the active one
            if context_id is None:
                context_id = self._active_context_id
            
            # Can't disconnect local
            if context_id == "local":
                logger.warning("[HopService] Cannot disconnect local context")
                return self._sessions["local"]
            
            # Cancel any reconnection task for this context
            if context_id in self._reconnect_tasks and not self._reconnect_tasks[context_id].done():
                self._reconnect_tasks[context_id].cancel()
                self._reconnect_tasks.pop(context_id, None)
            
            await self._close_connection(context_id)
            
            # Remove session and credentials
            self._sessions.pop(context_id, None)
            self._last_credentials.pop(context_id, None)
            # NOTE: Do NOT clear _connection_start_times - we keep it to prove
            # that a connection was established in this runtime session
            # This prevents false-positive stale session detection
            
            # If we disconnected the active context, switch to local
            if self._active_context_id == context_id:
                self._active_context_id = "local"
                logger.info(f"[HopService] Disconnected {context_id}; context switched to local")
            else:
                logger.info(f"[HopService] Disconnected {context_id}; active context remains {self._active_context_id}")
            
            return self._sessions[self._active_context_id]

    async def check_connection_health(self, context_id: Optional[str] = None) -> str:
        """Phase 8: Check connection health and return quality indicator.
        
        Args:
            context_id: Context to check. If None, checks the active context.
        """
        if context_id is None:
            context_id = self._active_context_id
        
        conn = self._connections.get(context_id)
        session = self._sessions.get(context_id)
        
        if not conn or not session or session.status != "connected":
            return "unknown"
        
        try:
            # Quick health check - run a simple command
            start = time.time()
            result = await asyncio.wait_for(
                conn.run('echo ping', check=False),
                timeout=2
            )
            latency = time.time() - start
            
            if result.exit_status != 0:
                return "poor"
            elif latency > 1.0:
                return "degraded"
            else:
                return "good"
        except asyncio.TimeoutError:
            return "poor"
        except Exception:
            return "poor"

    def status(self) -> HopSession:
        """Get the status of the active context."""
        active_session = self._sessions.get(self._active_context_id)
        if not active_session:
            # Shouldn't happen, but fallback to local
            self._active_context_id = "local"
            active_session = self._sessions["local"]
        
        # Derive status from connection object if available
        if self._active_context_id != "local":
            conn = self._connections.get(self._active_context_id)
            if conn is not None and active_session.status == "connected":
                # Phase 8: Update connection quality periodically
                start_time = self._connection_start_times.get(self._active_context_id)
                if start_time:
                    uptime = time.time() - start_time
                    if uptime > 300:  # Every 5 minutes, update quality in background
                        # Don't block status() call, just note staleness
                        pass
            else:
                # Normalization: If session says connected but there's no live connection object
                # and we never started a connection in this runtime, treat as stale (e.g. container restart)
                if (
                    active_session.status == "connected"
                    and conn is None
                    and self._active_context_id not in self._connection_start_times
                ):
                    active_session.status = "disconnected"
                    # Fall back to local context to avoid misleading routing
                    self._active_context_id = "local"
                    active_session = self._sessions["local"]
        
        return active_session
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions (including local)."""
        result = []
        for context_id, session in self._sessions.items():
            if (
                context_id != "local"
                and session.status == "connected"
                and context_id not in self._connections
                and context_id not in self._connection_start_times
            ):
                session.status = "disconnected"
            session_dict = asdict(session)
            session_dict['active'] = (context_id == self._active_context_id)
            # Ensure credentialName is set (fallback for old sessions or if not set)
            if context_id != 'local' and not session_dict.get('credentialName'):
                if session.credentialId:
                    cred = self.get_credential(session.credentialId)
                    if cred:
                        session_dict['credentialName'] = cred.get('name', context_id)
            result.append(session_dict)
        return result
    
    async def hop_to(self, context_id: str) -> HopSession:
        """Switch the active context to a different session.
        
        Args:
            context_id: The context to switch to (must be an existing session)
        
        Returns:
            The newly active session
        
        Raises:
            ValueError: If the context doesn't exist
        """
        async with self._lock:
            if context_id not in self._sessions:
                raise ValueError(f"Context '{context_id}' does not exist")
            
            old_context = self._active_context_id
            self._active_context_id = context_id
            
            logger.info(f"[HopService] Hopped from '{old_context}' to '{context_id}'")
            return self._sessions[context_id]
    
    def get_active_connection(self):
        """Get the SSH connection object for the active context.
        
        Returns None if active context is local or not connected.
        """
        if self._active_context_id == "local":
            return None
        conn = self._connections.get(self._active_context_id)
        return conn

    
    
    def get_active_sftp(self):
        """Get the SFTP client for the active context.
        
        Returns None if active context is local or no SFTP client.
        """
        if self._active_context_id == "local":
            return None
        sftp = self._sftp_clients.get(self._active_context_id)
        return sftp

    # -------- New helpers for multi-context consumers --------
    def get_session(self, context_id: str) -> Optional[HopSession]:
        """Return session object for a specific context id, if present."""
        return self._sessions.get(context_id)

    def get_sftp_for_context(self, context_id: str):
        """Return SFTP client for the specified context id (None if unavailable)."""
        if context_id == 'local':
            return None
        return self._sftp_clients.get(context_id)
    
    # Legacy property accessors for backward compatibility
    @property
    def _conn(self):
        """Legacy accessor for backward compatibility."""
        return self.get_active_connection()
    
    @property
    def _sftp(self):
        """Legacy accessor for backward compatibility."""
        return self.get_active_sftp()


_hop_service_singleton: Optional[HopService] = None


async def get_hop_service() -> HopService:
    global _hop_service_singleton
    if _hop_service_singleton is None:
        _hop_service_singleton = HopService()
    return _hop_service_singleton
