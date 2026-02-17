"""
WhatsApp Access Control

Manages phone number allowlists and pairing code approval for the WhatsApp bot.
Follows the pairing approval pattern from the WhatsApp guide — unknown numbers
must provide a pairing code that the bot owner approves.

Modes:
  - "open"      : Accept messages from anyone
  - "pairing"   : Unknown numbers must be approved via pairing code
  - "allowlist"  : Only pre-approved numbers can interact
  - "disabled"  : WhatsApp channel is off
"""

import asyncio
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)

# Charset without ambiguous chars (0/O, 1/I/L)
PAIRING_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
MAX_PENDING = 5
CODE_TTL_SECONDS = 3600  # 1 hour


class PairingRequest:
    """A pending pairing request from an unknown phone number."""

    def __init__(self, phone_e164: str, code: str):
        self.phone_e164 = phone_e164
        self.code = code
        self.created_at = time.time()

    def is_expired(self) -> bool:
        return time.time() - self.created_at > CODE_TTL_SECONDS

    def to_dict(self) -> dict:
        return {
            "phone": self.phone_e164,
            "code": self.code,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PairingRequest":
        req = cls(d["phone"], d["code"])
        req.created_at = d.get("created_at", time.time())
        return req


class WhatsAppAccessControl:
    """
    Access control for the WhatsApp bot.

    Supports three modes:
      - open:      anyone can message the bot
      - pairing:   unknown numbers get a pairing code to give the owner
      - allowlist: only pre-approved numbers work
    """

    def __init__(self, data_dir: str, mode: str = "pairing"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.mode = mode
        self.allowlist: Set[str] = set()
        self.pending: Dict[str, PairingRequest] = {}  # code → request
        self._lock = asyncio.Lock()

    # ─── Persistence ─────────────────────────────────────────

    async def load(self):
        """Load allowlist and pending pairings from disk."""
        async with self._lock:
            allow_path = self.data_dir / "allowlist.json"
            pending_path = self.data_dir / "pending_pairings.json"

            if allow_path.exists():
                try:
                    data = json.loads(allow_path.read_text())
                    self.allowlist = set(data if isinstance(data, list) else [])
                    logger.info(f"Loaded {len(self.allowlist)} allowed numbers")
                except Exception as e:
                    logger.warning(f"Failed to load allowlist: {e}")

            if pending_path.exists():
                try:
                    data = json.loads(pending_path.read_text())
                    for item in data:
                        req = PairingRequest.from_dict(item)
                        if not req.is_expired():
                            self.pending[req.code] = req
                    logger.info(f"Loaded {len(self.pending)} pending pairings")
                except Exception as e:
                    logger.warning(f"Failed to load pending pairings: {e}")

    async def _save_allowlist(self):
        """Save allowlist to disk with atomic write."""
        path = self.data_dir / "allowlist.json"
        tmp = path.with_suffix(".tmp")
        try:
            # Filter out None values and sort
            clean = sorted(x for x in self.allowlist if x is not None)
            tmp.write_text(json.dumps(clean, indent=2))
            tmp.rename(path)
        except Exception as e:
            logger.error(f"Failed to save allowlist: {e}")

    async def _save_pending(self):
        """Save pending pairings to disk."""
        path = self.data_dir / "pending_pairings.json"
        tmp = path.with_suffix(".tmp")
        try:
            data = [r.to_dict() for r in self.pending.values()]
            tmp.write_text(json.dumps(data, indent=2))
            tmp.rename(path)
        except Exception as e:
            logger.error(f"Failed to save pending pairings: {e}")

    # ─── Access checks ───────────────────────────────────────

    def is_allowed(self, phone_e164: str) -> bool:
        """Check if a phone number is allowed to interact with the bot."""
        if self.mode == "open":
            return True
        if self.mode == "disabled":
            return False
        # Wildcard allows all
        if "*" in self.allowlist:
            return True
        return phone_e164 in self.allowlist

    # ─── Pairing ─────────────────────────────────────────────

    async def generate_pairing_code(self, phone_e164: str) -> Optional[str]:
        """
        Generate a pairing code for an unknown phone number.

        Returns the code string, or None if max pending requests reached.
        """
        if not phone_e164:
            logger.warning("Cannot generate pairing code: no phone number provided")
            return None

        async with self._lock:
            # Clean expired entries first
            self._clean_expired()

            # Check if this phone already has a pending request
            for code, req in self.pending.items():
                if req.phone_e164 == phone_e164:
                    return code  # Return existing code

            # Check limits
            if len(self.pending) >= MAX_PENDING:
                logger.warning("Max pending pairing requests reached")
                return None

            # Generate unique code
            code = self._make_code()
            while code in self.pending:
                code = self._make_code()

            self.pending[code] = PairingRequest(phone_e164, code)
            await self._save_pending()
            logger.info(f"Generated pairing code {code} for {phone_e164}")
            return code

    async def approve(self, code: str) -> Optional[str]:
        """
        Approve a pairing code, adding the phone to the allowlist.

        Returns the phone number if approved, None if code not found.
        """
        async with self._lock:
            self._clean_expired()
            normalized = code.upper().replace("-", "").replace(" ", "")

            req = self.pending.pop(normalized, None)
            if not req:
                return None

            self.allowlist.add(req.phone_e164)
            await self._save_allowlist()
            await self._save_pending()
            logger.info(f"Approved pairing for {req.phone_e164}")
            return req.phone_e164

    async def revoke(self, phone_e164: str) -> bool:
        """Remove a phone number from the allowlist."""
        async with self._lock:
            if phone_e164 in self.allowlist:
                self.allowlist.discard(phone_e164)
                await self._save_allowlist()
                logger.info(f"Revoked access for {phone_e164}")
                return True
            return False

    async def add_allowed(self, phone_e164: str):
        """Directly add a phone number to the allowlist."""
        async with self._lock:
            self.allowlist.add(phone_e164)
            await self._save_allowlist()

    def list_pending(self) -> list:
        """List all pending pairing requests."""
        self._clean_expired()
        return [
            {"phone": r.phone_e164, "code": r.code, "created_at": r.created_at}
            for r in self.pending.values()
        ]

    # ─── Internal ─────────────────────────────────────────────

    def _make_code(self) -> str:
        """Generate a random pairing code."""
        return "".join(secrets.choice(PAIRING_CHARSET) for _ in range(CODE_LENGTH))

    def _clean_expired(self):
        """Remove expired pairing requests."""
        expired = [code for code, req in self.pending.items() if req.is_expired()]
        for code in expired:
            del self.pending[code]
        if expired:
            logger.debug(f"Cleaned {len(expired)} expired pairing requests")
