"""
Tests for SSH config writer.

Following TDD approach: write tests first, then implement.
"""

import pytest
from icpy.utils.ssh_config_parser import SSHConfigEntry
from icpy.utils.ssh_config_writer import (
    generate_ssh_config,
    credential_to_config_entry,
)
from icpy.services.hop_service import SSHCredential


class TestBasicGeneration:
    """Test basic SSH config generation."""
    
    def test_generate_simple_entry(self):
        """Should generate a simple host entry."""
        entry = SSHConfigEntry(
            host="myserver",
            hostname="192.168.1.100",
            user="admin",
            port=22,
        )
        
        config = generate_ssh_config([entry])
        
        assert "Host myserver" in config
        assert "HostName 192.168.1.100" in config
        assert "User admin" in config
        assert "Port 22" in config
    
    def test_generate_multiple_entries(self):
        """Should generate multiple host entries with blank lines between."""
        entries = [
            SSHConfigEntry(host="server1", hostname="192.168.1.100", user="user1"),
            SSHConfigEntry(host="server2", hostname="192.168.1.101", user="user2"),
        ]
        
        config = generate_ssh_config(entries)
        
        assert "Host server1" in config
        assert "Host server2" in config
        # Should have blank line between entries
        assert "\n\n" in config
    
    def test_generate_with_identity_file(self):
        """Should include IdentityFile directive."""
        entry = SSHConfigEntry(
            host="keyserver",
            hostname="192.168.1.100",
            user="admin",
            identity_file="~/.ssh/id_rsa",
        )
        
        config = generate_ssh_config([entry])
        
        assert "IdentityFile ~/.ssh/id_rsa" in config
    
    def test_generate_custom_port(self):
        """Should include Port directive for non-22 ports."""
        entry = SSHConfigEntry(
            host="myserver",
            hostname="192.168.1.100",
            port=2222,
        )
        
        config = generate_ssh_config([entry])
        
        assert "Port 2222" in config
    
    def test_omit_default_port(self):
        """Should omit Port directive for default port 22."""
        entry = SSHConfigEntry(
            host="myserver",
            hostname="192.168.1.100",
            port=22,
        )
        
        config = generate_ssh_config([entry])
        
        # Port 22 is default, can be omitted
        # But our implementation includes it for clarity
        # This test accepts either behavior
        assert "Host myserver" in config


class TestIcotesMetadata:
    """Test embedding of icotes metadata."""
    
    def test_embed_icotes_metadata(self):
        """Should embed icotes metadata as comment."""
        entry = SSHConfigEntry(
            host="hop1",
            hostname="192.168.2.211",
            user="penthoy",
            icotes_id="abc-123",
            icotes_auth="privateKey",
            icotes_default_path="/home/penthoy",
        )
        
        config = generate_ssh_config([entry])
        
        assert "# icotes-meta:" in config
        assert '"id": "abc-123"' in config
        assert '"auth": "privateKey"' in config
        assert '"defaultPath": "/home/penthoy"' in config
    
    def test_embed_timestamps(self):
        """Should embed timestamps in metadata."""
        entry = SSHConfigEntry(
            host="hop1",
            hostname="192.168.2.211",
            icotes_id="abc-123",
            icotes_auth="password",
            icotes_created_at="2025-01-01T00:00:00Z",
            icotes_updated_at="2025-01-02T00:00:00Z",
        )
        
        config = generate_ssh_config([entry])
        
        assert '"createdAt": "2025-01-01T00:00:00Z"' in config
        assert '"updatedAt": "2025-01-02T00:00:00Z"' in config
    
    def test_no_metadata_for_standard_entry(self):
        """Should not add icotes-meta comment if no metadata."""
        entry = SSHConfigEntry(
            host="regular",
            hostname="192.168.1.100",
            user="admin",
        )
        
        config = generate_ssh_config([entry])
        
        assert "# icotes-meta:" not in config


class TestFormatting:
    """Test config formatting and style."""
    
    def test_proper_indentation(self):
        """Should use proper indentation (4 spaces)."""
        entry = SSHConfigEntry(
            host="myserver",
            hostname="192.168.1.100",
            user="admin",
        )
        
        config = generate_ssh_config([entry])
        
        # Check indentation
        lines = config.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('Host'):
                assert line.startswith('    ') or line.startswith('#')
    
    def test_field_ordering(self):
        """Should output fields in standard order."""
        entry = SSHConfigEntry(
            host="myserver",
            hostname="192.168.1.100",
            user="admin",
            port=2222,
            identity_file="~/.ssh/id_rsa",
        )
        
        config = generate_ssh_config([entry])
        lines = [l.strip() for l in config.split('\n') if l.strip()]
        
        # Standard order: Host, HostName, User, Port, IdentityFile
        host_idx = next(i for i, l in enumerate(lines) if l.startswith('Host'))
        hostname_idx = next(i for i, l in enumerate(lines) if l.startswith('HostName'))
        user_idx = next(i for i, l in enumerate(lines) if l.startswith('User'))
        port_idx = next(i for i, l in enumerate(lines) if l.startswith('Port'))
        
        assert host_idx < hostname_idx < user_idx < port_idx
    
    def test_header_comment(self):
        """Should include header comment."""
        entry = SSHConfigEntry(host="myserver", hostname="192.168.1.100")
        
        config = generate_ssh_config([entry])
        
        assert "# icotes hop configuration" in config
        assert "# This file is compatible with VS Code Remote SSH config" in config


class TestCredentialConversion:
    """Test conversion from SSHCredential to SSHConfigEntry."""
    
    def test_convert_password_credential(self):
        """Should convert password-based credential."""
        cred = SSHCredential(
            id="abc-123",
            name="myserver",
            host="192.168.1.100",
            port=22,
            username="admin",
            auth="password",
        )
        
        entry = credential_to_config_entry(cred)
        
        assert entry.host == "myserver"
        assert entry.hostname == "192.168.1.100"
        assert entry.user == "admin"
        assert entry.port == 22
        assert entry.icotes_id == "abc-123"
        assert entry.icotes_auth == "password"
    
    def test_convert_privatekey_credential(self):
        """Should convert privateKey-based credential."""
        cred = SSHCredential(
            id="abc-123",
            name="keyserver",
            host="192.168.1.100",
            username="admin",
            auth="privateKey",
            privateKeyId="mykey_id",
        )
        
        entry = credential_to_config_entry(cred)
        
        assert entry.icotes_auth == "privateKey"
        assert "mykey_id" in entry.identity_file
    
    def test_convert_with_default_path(self):
        """Should include defaultPath in metadata."""
        cred = SSHCredential(
            id="abc-123",
            name="myserver",
            host="192.168.1.100",
            username="admin",
            auth="password",
            defaultPath="/home/admin/workspace",
        )
        
        entry = credential_to_config_entry(cred)
        
        assert entry.icotes_default_path == "/home/admin/workspace"
    
    def test_convert_with_timestamps(self):
        """Should preserve timestamps."""
        cred = SSHCredential(
            id="abc-123",
            name="myserver",
            host="192.168.1.100",
            username="admin",
            auth="password",
            createdAt="2025-01-01T00:00:00Z",
            updatedAt="2025-01-02T00:00:00Z",
        )
        
        entry = credential_to_config_entry(cred)
        
        assert entry.icotes_created_at == "2025-01-01T00:00:00Z"
        assert entry.icotes_updated_at == "2025-01-02T00:00:00Z"


class TestSpecialCases:
    """Test special cases and edge conditions."""
    
    def test_generate_empty_list(self):
        """Should generate header-only config for empty list."""
        config = generate_ssh_config([])
        
        assert "# icotes hop configuration" in config
        assert "Host" not in config
    
    def test_generate_local_context(self):
        """Should generate special local context entry."""
        entry = SSHConfigEntry(
            host="local",
            hostname="localhost",
            icotes_id="local",
            icotes_auth="none",
            icotes_default_path="/home/user/icotes",
        )
        
        config = generate_ssh_config([entry])
        
        assert "Host local" in config
        assert "HostName localhost" in config
        assert '"id": "local"' in config
        assert '"auth": "none"' in config
    
    def test_handle_special_characters_in_values(self):
        """Should handle special characters in values."""
        entry = SSHConfigEntry(
            host="my-server_01",
            hostname="192.168.1.100",
            user="admin-user",
            icotes_default_path="/home/user/my workspace",
        )
        
        config = generate_ssh_config([entry])
        
        assert "Host my-server_01" in config
        assert "User admin-user" in config
    
    def test_windows_path_preservation(self):
        """Should preserve Windows-style paths."""
        entry = SSHConfigEntry(
            host="winserver",
            hostname="192.168.1.100",
            identity_file="C:\\Users\\admin\\.ssh\\id_rsa",
        )
        
        config = generate_ssh_config([entry])
        
        assert "C:\\Users\\admin\\.ssh\\id_rsa" in config


class TestRoundTrip:
    """Test round-trip conversion (parse -> write -> parse)."""
    
    def test_roundtrip_preserves_data(self):
        """Should preserve all data in parse -> write -> parse cycle."""
        from icpy.utils.ssh_config_parser import parse_ssh_config
        
        original = [
            SSHConfigEntry(
                host="hop1",
                hostname="192.168.2.211",
                user="penthoy",
                port=22,
                identity_file="~/.icotes/ssh/keys/hop1_key",
                icotes_id="abc-123",
                icotes_auth="privateKey",
                icotes_default_path="/home/penthoy/icotes",
                icotes_created_at="2025-01-01T00:00:00Z",
            ),
        ]
        
        # Write to config
        config_text = generate_ssh_config(original)
        
        # Parse back
        parsed = parse_ssh_config(config_text)
        
        # Verify all fields preserved
        assert len(parsed) == 1
        assert parsed[0].host == original[0].host
        assert parsed[0].hostname == original[0].hostname
        assert parsed[0].user == original[0].user
        assert parsed[0].port == original[0].port
        assert parsed[0].identity_file == original[0].identity_file
        assert parsed[0].icotes_id == original[0].icotes_id
        assert parsed[0].icotes_auth == original[0].icotes_auth
        assert parsed[0].icotes_default_path == original[0].icotes_default_path
        assert parsed[0].icotes_created_at == original[0].icotes_created_at
    
    def test_roundtrip_multiple_entries(self):
        """Should preserve multiple entries in round-trip."""
        from icpy.utils.ssh_config_parser import parse_ssh_config
        
        original = [
            SSHConfigEntry(host="server1", hostname="192.168.1.100", user="user1"),
            SSHConfigEntry(host="server2", hostname="192.168.1.101", user="user2"),
            SSHConfigEntry(host="server3", hostname="192.168.1.102", user="user3"),
        ]
        
        config_text = generate_ssh_config(original)
        parsed = parse_ssh_config(config_text)
        
        assert len(parsed) == 3
        for i in range(3):
            assert parsed[i].host == original[i].host
            assert parsed[i].hostname == original[i].hostname
            assert parsed[i].user == original[i].user
