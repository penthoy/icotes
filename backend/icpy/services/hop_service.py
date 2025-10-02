"""
Hop Service: Manage SSH credentials, keys, and active hop session.

Phases implemented:
- Phase 1: Credentials CRUD, key upload (store-only), status stub
- Phase 2: Real SSH connectivity with asyncssh, connect/disconnect/status

Security:
- Passwords and passphrases are treated as write-only and never persisted or returned
- Private keys are stored under ~/.icotes/ssh/keys with 0600 permissions
- No secrets are logged
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

try:
    import asyncssh  # Phase 2: real connectivity
    ASYNCSSH_AVAILABLE = True
except Exception:  # pragma: no cover - dependency issues handled by tests
    asyncssh = None
    ASYNCSSH_AVAILABLE = False


logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _app_data_dir() -> Path:
    """Return the base directory for icotes data in the user's home.

    We keep hop-related files under ~/.icotes/ssh
    """
    base = Path(os.path.expanduser("~/.icotes/ssh"))
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
    status: str = "disconnected"  # disconnected|connecting|connected|error
    cwd: str = "/"
    lastError: Optional[str] = None
    # Helpful fields for UI/telemetry (non-secret)
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None


class HopService:
    """Manage credentials & a single active hop session."""

    def __init__(self) -> None:
        # Capture the home directory at instantiation time to detect env changes in tests
        self._home_dir: str = os.path.expanduser("~")
        self._creds: Dict[str, SSHCredential] = {}
        self._session: HopSession = HopSession()
        # runtime connection objects (not serialized)
        self._conn = None
        self._sftp = None
        self._lock = asyncio.Lock()
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
            cred.port = int(data["port"]) or 22
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
        """Connect to remote host using credential. Phase 2: real connectivity."""
        async with self._lock:
            cred = self._creds.get(cred_id)
            if not cred:
                raise ValueError("Credential not found")

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

            # Close any existing connection first
            await self._close_connection()

            if not ASYNCSSH_AVAILABLE:
                # Phase 1 fallback: stubbed connected state without real SSH
                self._session.status = "connected"
                return self._session

            try:
                logger.info(f"[HopService] Connecting to {cred.host}:{cred.port} as {cred.username or '<auto>'} (auth={cred.auth})")
                client_keys = None
                if cred.auth == "privateKey" and cred.privateKeyId:
                    key_path = str(self.get_key_path(cred.privateKeyId))
                    client_keys = [key_path]

                # known_hosts=None -> permissive in dev (configurable later)
                self._conn = await asyncssh.connect(
                    host=cred.host,
                    port=cred.port or 22,
                    username=cred.username or None,
                    password=password if cred.auth == "password" else None,
                    client_keys=client_keys,
                    passphrase=passphrase if cred.auth == "privateKey" else None,
                    known_hosts=None,
                    connect_timeout=10,
                )
                try:
                    self._sftp = await self._conn.start_sftp_client()
                except Exception:
                    self._sftp = None

                self._session.status = "connected"
                # Determine remote home/cwd if not provided
                if not cred.defaultPath:
                    try:
                        # Prefer environment HOME
                        run_res = await self._conn.run('printenv HOME', check=False)
                        home = (run_res.stdout or '').strip()
                        if not home:
                            # Fallback to pwd
                            run_res = await self._conn.run('pwd', check=False)
                            home = (run_res.stdout or '').strip() or '/'
                        # Validate directory exists via SFTP if available
                        if self._sftp:
                            try:
                                await self._sftp.stat(home)
                                self._session.cwd = home
                            except Exception:
                                self._session.cwd = '/'
                        else:
                            self._session.cwd = home or '/'
                    except Exception:
                        # Keep existing default
                        pass
                logger.info(f"[HopService] Connected: {cred.host}:{cred.port}")
                return self._session
            except Exception as e:
                logger.error(f"SSH connect error to {cred.host}:{cred.port} - {e}")
                self._session.status = "error"
                self._session.lastError = str(e)
                # ensure cleanup
                await self._close_connection()
                return self._session

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

    async def disconnect(self) -> HopSession:
        async with self._lock:
            await self._close_connection()
            self._session = HopSession()  # back to local
            logger.info("[HopService] Disconnected; context returned to local")
            return self._session

    def status(self) -> HopSession:
        # Derive status from connection object if available
        if self._conn is not None and self._session.status == "connected":
            return self._session
        # If not connected, normalize session
        if self._session.contextId != "local" and self._conn is None:
            self._session.status = "disconnected"
        return self._session


_hop_service_singleton: Optional[HopService] = None


async def get_hop_service() -> HopService:
    global _hop_service_singleton
    current_home = os.path.expanduser("~")
    if (
        _hop_service_singleton is None
        or getattr(_hop_service_singleton, "_home_dir", None) != current_home
    ):
        # Recreate singleton if HOME changed (common in tests)
        _hop_service_singleton = HopService()
    return _hop_service_singleton
