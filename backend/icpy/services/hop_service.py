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

from ..utils.logging import sanitize_log_message, mask_credential_value

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


def _app_data_dir() -> Path:
    """Return the base directory for icotes SSH data in the workspace.

    We keep hop-related files under workspace/.icotes/ssh for Docker persistence.
    This ensures credentials survive container restarts when workspace is mounted as a volume.
    """
    # Get workspace root from environment or fallback
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
    
    base = Path(workspace_root) / '.icotes' / 'ssh'
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
    """Manage credentials & a single active hop session."""

    def __init__(self) -> None:
        self._creds: Dict[str, SSHCredential] = {}
        self._session: HopSession = HopSession()
        # runtime connection objects (not serialized)
        self._conn = None
        self._sftp = None
        self._lock = asyncio.Lock()
        # Phase 8: Reconnection state
        self._reconnect_task: Optional[asyncio.Task] = None
        self._last_credential: Optional[Dict] = None  # For reconnection
        self._connection_start_time: Optional[float] = None
        self._load_credentials()

    # -------------------- Persistence --------------------
    def _load_credentials(self) -> None:
        path = _creds_file()
        if not path.exists():
            self._creds = {}
            return
        try:
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
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            self._creds = {}

    def _save_credentials(self) -> None:
        path = _creds_file()
        try:
            serializable = []
            for cred in self._creds.values():
                d = cred.to_public_dict()
                serializable.append(d)
            path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

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
        """Connect to remote host using credential. Phase 2+8: real connectivity with enhanced error handling."""
        async with self._lock:
            cred = self._creds.get(cred_id)
            if not cred:
                raise ValueError("Credential not found")

            # Cancel any ongoing reconnection task
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
                self._reconnect_task = None

            # Seed session with useful metadata for UI
            self._session = HopSession(
                contextId=cred.id,
                credentialId=cred.id,
                status="connecting",
                cwd=cred.defaultPath or "/",
                host=cred.host,
                port=cred.port,
                username=cred.username or None,
            )
            self._session.lastError = None

            # Store credentials for potential reconnection (sanitized)
            self._last_credential = {
                'cred_id': cred_id,
                'password': password,
                'passphrase': passphrase,
            }

            # Close any existing connection first
            await self._close_connection()

            if not ASYNCSSH_AVAILABLE:
                # Phase 1 fallback: stubbed connected state without real SSH
                self._session.status = "connected"
                return self._session

            try:
                # Phase 8: Sanitize logging of sensitive connection info
                safe_username = mask_credential_value(cred.username, show_prefix=2, show_suffix=2) if cred.username else '<auto>'
                log_msg = f"[HopService] Connecting to {cred.host}:{cred.port} as {safe_username} (auth={cred.auth})"
                logger.info(sanitize_log_message(log_msg))
                
                client_keys = None
                if cred.auth == "privateKey" and cred.privateKeyId:
                    key_path = str(self.get_key_path(cred.privateKeyId))
                    client_keys = [key_path]

                self._connection_start_time = time.time()
                
                # Phase 8: Use configurable timeout
                self._conn = await asyncssh.connect(
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
                try:
                    self._sftp = await asyncio.wait_for(
                        self._conn.start_sftp_client(),
                        timeout=OPERATION_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    logger.warning("[HopService] SFTP client start timed out")
                    self._sftp = None
                except Exception as e:
                    logger.warning(f"[HopService] SFTP client start failed: {e}")
                    self._sftp = None

                self._session.status = "connected"
                self._session.lastConnectedAt = _now_iso()
                self._session.reconnectAttempt = 0
                self._session.connectionQuality = "good"
                
                # Determine remote home/cwd if not provided
                if not cred.defaultPath:
                    try:
                        # Prefer environment HOME
                        run_res = await asyncio.wait_for(
                            self._conn.run('printenv HOME', check=False),
                            timeout=5
                        )
                        home = (run_res.stdout or '').strip()
                        if not home:
                            # Fallback to pwd
                            run_res = await asyncio.wait_for(
                                self._conn.run('pwd', check=False),
                                timeout=5
                            )
                            home = (run_res.stdout or '').strip() or '/'
                        # Validate directory exists via SFTP if available
                        if self._sftp:
                            try:
                                await asyncio.wait_for(self._sftp.stat(home), timeout=5)
                                self._session.cwd = home
                            except Exception:
                                self._session.cwd = '/'
                        else:
                            self._session.cwd = home or '/'
                    except asyncio.TimeoutError:
                        logger.warning("[HopService] Home directory detection timed out")
                    except Exception as e:
                        logger.debug(f"[HopService] Home directory detection failed: {e}")
                        # Keep existing default
                        pass
                        
                connection_time = time.time() - self._connection_start_time
                logger.info(f"[HopService] Connected to {cred.host}:{cred.port} in {connection_time:.2f}s")
                return self._session
            except asyncio.TimeoutError:
                error_msg = f"Connection to {cred.host}:{cred.port} timed out after {CONNECTION_TIMEOUT}s"
                logger.error(f"[HopService] {error_msg}")
                self._session.status = "error"
                self._session.lastError = error_msg
                await self._close_connection()
                return self._session
            except Exception as e:
                # Phase 8: Sanitize error messages for sensitive info
                error_msg = sanitize_log_message(str(e))
                logger.error(f"[HopService] SSH connect error to {cred.host}:{cred.port} - {error_msg}")
                self._session.status = "error"
                self._session.lastError = self._format_user_friendly_error(e)
                await self._close_connection()
                return self._session

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

    async def _close_connection(self):
        """Gracefully close SFTP and SSH connection with timeouts and abort fallback.

        Rationale: In some cases (e.g., active remote PTY channels), a graceful
        close can hang indefinitely. Use short timeouts and escalate to abort()
        to guarantee forward progress and avoid memory growth from stuck tasks.
        """
        start_ts = time.time()
        used_abort = False
        sftp_closed = False
        try:
            # Close SFTP first
            if self._sftp:
                try:
                    res = self._sftp.exit()
                    if inspect.isawaitable(res):
                        await asyncio.wait_for(res, timeout=1.5)
                    sftp_closed = True
                except Exception:
                    # Ignore SFTP close errors/timeouts
                    pass

            # Then close SSH connection
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                # Wait briefly for clean shutdown; fall back to abort
                try:
                    await asyncio.wait_for(self._conn.wait_closed(), timeout=2.5)
                except (asyncio.TimeoutError, Exception):
                    # Force-close if graceful close hangs due to open channels
                    try:
                        if hasattr(self._conn, 'abort'):
                            self._conn.abort()
                            used_abort = True
                    except Exception:
                        pass
                    # Best effort wait after abort
                    try:
                        await asyncio.wait_for(self._conn.wait_closed(), timeout=1.0)
                    except Exception:
                        pass
        finally:
            logger.info(
                "[HopService] _close_connection complete in %.3fs (sftp_closed=%s, used_abort=%s)",
                time.time() - start_ts,
                sftp_closed,
                used_abort,
            )
            self._conn = None
            self._sftp = None

    async def _attempt_reconnect(self) -> bool:
        """Phase 8: Attempt automatic reconnection with exponential backoff."""
        if not self._last_credential:
            return False
            
        max_attempts = RECONNECT_MAX_RETRIES
        attempt = self._session.reconnectAttempt
        
        while attempt < max_attempts:
            attempt += 1
            self._session.reconnectAttempt = attempt
            self._session.status = "reconnecting"
            
            # Exponential backoff
            wait_time = min(RECONNECT_BACKOFF_BASE ** attempt, 30)  # Cap at 30s
            logger.info(f"[HopService] Reconnection attempt {attempt}/{max_attempts} in {wait_time:.1f}s")
            
            await asyncio.sleep(wait_time)
            
            try:
                result = await self.connect(
                    self._last_credential['cred_id'],
                    password=self._last_credential.get('password'),
                    passphrase=self._last_credential.get('passphrase')
                )
                
                if result.status == "connected":
                    logger.info(f"[HopService] Reconnection successful after {attempt} attempts")
                    return True
            except Exception as e:
                logger.warning(f"[HopService] Reconnection attempt {attempt} failed: {e}")
                continue
        
        logger.error(f"[HopService] Reconnection failed after {max_attempts} attempts")
        self._session.lastError = f"Failed to reconnect after {max_attempts} attempts"
        return False

    async def disconnect(self) -> HopSession:
        async with self._lock:
            # Cancel any reconnection task
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
                self._reconnect_task = None
            
            await self._close_connection()
            self._session = HopSession()  # back to local
            self._last_credential = None
            self._connection_start_time = None
            logger.info("[HopService] Disconnected; context returned to local")
            return self._session

    async def check_connection_health(self) -> str:
        """Phase 8: Check connection health and return quality indicator."""
        if not self._conn or self._session.status != "connected":
            return "unknown"
        
        try:
            # Quick health check - run a simple command
            start = time.time()
            result = await asyncio.wait_for(
                self._conn.run('echo ping', check=False),
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
        # Derive status from connection object if available
        if self._conn is not None and self._session.status == "connected":
            # Phase 8: Update connection quality periodically
            if self._connection_start_time:
                uptime = time.time() - self._connection_start_time
                if uptime > 300:  # Every 5 minutes, update quality in background
                    # Don't block status() call, just note staleness
                    pass
            return self._session
        # If not connected, normalize session
        if self._session.contextId != "local" and self._conn is None:
            self._session.status = "disconnected"
        return self._session


_hop_service_singleton: Optional[HopService] = None


async def get_hop_service() -> HopService:
    global _hop_service_singleton
    if _hop_service_singleton is None:
        _hop_service_singleton = HopService()
    return _hop_service_singleton
