"""
Tests for WhatsApp Access Control module.

Tests the pairing code generation, approval workflow, allowlist management,
and access mode behaviors.
"""

import asyncio
import json
import os
import tempfile
import time

import pytest

from icpy.services.whatsapp.access_control import (
    WhatsAppAccessControl,
    PairingRequest,
    CODE_LENGTH,
    CODE_TTL_SECONDS,
    MAX_PENDING,
    PAIRING_CHARSET,
)


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    return str(tmp_path / "wa_data")


@pytest.fixture
def access_open(tmp_data_dir):
    """Access control in 'open' mode."""
    return WhatsAppAccessControl(tmp_data_dir, mode="open")


@pytest.fixture
def access_pairing(tmp_data_dir):
    """Access control in 'pairing' mode."""
    return WhatsAppAccessControl(tmp_data_dir, mode="pairing")


@pytest.fixture
def access_allowlist(tmp_data_dir):
    """Access control in 'allowlist' mode."""
    return WhatsAppAccessControl(tmp_data_dir, mode="allowlist")


@pytest.fixture
def access_disabled(tmp_data_dir):
    """Access control in 'disabled' mode."""
    return WhatsAppAccessControl(tmp_data_dir, mode="disabled")


# ─── PairingRequest tests ────────────────────────────────────


class TestPairingRequest:
    """Tests for the PairingRequest data class."""

    def test_create(self):
        req = PairingRequest("+16047193142", "ABCD1234")
        assert req.phone_e164 == "+16047193142"
        assert req.code == "ABCD1234"
        assert not req.is_expired()

    def test_expired(self):
        req = PairingRequest("+16047193142", "ABCD1234")
        req.created_at = time.time() - CODE_TTL_SECONDS - 1
        assert req.is_expired()

    def test_not_expired(self):
        req = PairingRequest("+16047193142", "ABCD1234")
        assert not req.is_expired()

    def test_to_dict_roundtrip(self):
        req = PairingRequest("+16047193142", "ABCD1234")
        d = req.to_dict()
        req2 = PairingRequest.from_dict(d)
        assert req2.phone_e164 == req.phone_e164
        assert req2.code == req.code
        assert req2.created_at == req.created_at


# ─── Access mode tests ───────────────────────────────────────


class TestAccessModes:
    """Tests for the different access control modes."""

    def test_open_allows_everyone(self, access_open):
        assert access_open.is_allowed("+16047193142")
        assert access_open.is_allowed("+447898114104")
        assert access_open.is_allowed("+0000000000")

    def test_disabled_blocks_everyone(self, access_disabled):
        assert not access_disabled.is_allowed("+16047193142")
        assert not access_disabled.is_allowed("+447898114104")

    @pytest.mark.asyncio
    async def test_allowlist_only_allows_listed(self, access_allowlist):
        assert not access_allowlist.is_allowed("+16047193142")
        await access_allowlist.add_allowed("+16047193142")
        assert access_allowlist.is_allowed("+16047193142")
        assert not access_allowlist.is_allowed("+447898114104")

    @pytest.mark.asyncio
    async def test_wildcard_allows_all(self, access_allowlist):
        assert not access_allowlist.is_allowed("+16047193142")
        await access_allowlist.add_allowed("*")
        assert access_allowlist.is_allowed("+16047193142")
        assert access_allowlist.is_allowed("+447898114104")


# ─── Pairing code tests ─────────────────────────────────────


class TestPairingCodes:
    """Tests for the pairing code generation and approval workflow."""

    @pytest.mark.asyncio
    async def test_generate_code(self, access_pairing):
        code = await access_pairing.generate_pairing_code("+16047193142")
        assert code is not None
        assert len(code) == CODE_LENGTH
        # All chars should be from the allowed charset
        for c in code:
            assert c in PAIRING_CHARSET

    @pytest.mark.asyncio
    async def test_same_phone_returns_same_code(self, access_pairing):
        code1 = await access_pairing.generate_pairing_code("+16047193142")
        code2 = await access_pairing.generate_pairing_code("+16047193142")
        assert code1 == code2

    @pytest.mark.asyncio
    async def test_different_phones_get_different_codes(self, access_pairing):
        code1 = await access_pairing.generate_pairing_code("+16047193142")
        code2 = await access_pairing.generate_pairing_code("+447898114104")
        assert code1 != code2

    @pytest.mark.asyncio
    async def test_approve_adds_to_allowlist(self, access_pairing):
        code = await access_pairing.generate_pairing_code("+16047193142")
        assert not access_pairing.is_allowed("+16047193142")

        phone = await access_pairing.approve(code)
        assert phone == "+16047193142"
        assert access_pairing.is_allowed("+16047193142")

    @pytest.mark.asyncio
    async def test_approve_unknown_code_returns_none(self, access_pairing):
        result = await access_pairing.approve("XXXXXXXX")
        assert result is None

    @pytest.mark.asyncio
    async def test_approve_case_insensitive(self, access_pairing):
        code = await access_pairing.generate_pairing_code("+16047193142")
        phone = await access_pairing.approve(code.lower())
        assert phone == "+16047193142"

    @pytest.mark.asyncio
    async def test_max_pending_limit(self, access_pairing):
        # Generate MAX_PENDING codes
        for i in range(MAX_PENDING):
            code = await access_pairing.generate_pairing_code(f"+1000000000{i}")
            assert code is not None

        # The next one should return None
        code = await access_pairing.generate_pairing_code("+19999999999")
        assert code is None

    @pytest.mark.asyncio
    async def test_expired_codes_cleaned(self, access_pairing):
        code = await access_pairing.generate_pairing_code("+16047193142")
        # Manually expire it
        access_pairing.pending[code].created_at = time.time() - CODE_TTL_SECONDS - 1

        # Should generate a new code (old one expired)
        code2 = await access_pairing.generate_pairing_code("+16047193142")
        assert code2 is not None
        assert code2 != code

    @pytest.mark.asyncio
    async def test_list_pending(self, access_pairing):
        await access_pairing.generate_pairing_code("+16047193142")
        await access_pairing.generate_pairing_code("+447898114104")
        pending = access_pairing.list_pending()
        assert len(pending) == 2
        phones = {p["phone"] for p in pending}
        assert "+16047193142" in phones
        assert "+447898114104" in phones


# ─── Revoke tests ────────────────────────────────────────────


class TestRevoke:
    """Tests for revoking access."""

    @pytest.mark.asyncio
    async def test_revoke_allowed_number(self, access_pairing):
        await access_pairing.add_allowed("+16047193142")
        assert access_pairing.is_allowed("+16047193142")
        revoked = await access_pairing.revoke("+16047193142")
        assert revoked
        assert not access_pairing.is_allowed("+16047193142")

    @pytest.mark.asyncio
    async def test_revoke_unlisted_number(self, access_pairing):
        revoked = await access_pairing.revoke("+16047193142")
        assert not revoked


# ─── Persistence tests ──────────────────────────────────────


class TestPersistence:
    """Tests for saving and loading state from disk."""

    @pytest.mark.asyncio
    async def test_save_and_load_allowlist(self, tmp_data_dir):
        # Create and save
        ac1 = WhatsAppAccessControl(tmp_data_dir, mode="pairing")
        await ac1.add_allowed("+16047193142")
        await ac1.add_allowed("+447898114104")

        # Load from same directory
        ac2 = WhatsAppAccessControl(tmp_data_dir, mode="pairing")
        await ac2.load()
        assert ac2.is_allowed("+16047193142")
        assert ac2.is_allowed("+447898114104")
        assert not ac2.is_allowed("+11111111111")

    @pytest.mark.asyncio
    async def test_save_and_load_pending(self, tmp_data_dir):
        ac1 = WhatsAppAccessControl(tmp_data_dir, mode="pairing")
        code = await ac1.generate_pairing_code("+16047193142")

        # Load from same directory
        ac2 = WhatsAppAccessControl(tmp_data_dir, mode="pairing")
        await ac2.load()
        assert len(ac2.pending) == 1
        assert code in ac2.pending

    @pytest.mark.asyncio
    async def test_expired_pending_not_loaded(self, tmp_data_dir):
        ac1 = WhatsAppAccessControl(tmp_data_dir, mode="pairing")
        code = await ac1.generate_pairing_code("+16047193142")
        # Expire it
        ac1.pending[code].created_at = time.time() - CODE_TTL_SECONDS - 1
        # Re-save (simulate)
        await ac1._save_pending()

        # Load — expired should be filtered
        ac2 = WhatsAppAccessControl(tmp_data_dir, mode="pairing")
        await ac2.load()
        assert len(ac2.pending) == 0
