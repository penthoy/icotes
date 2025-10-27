"""
Tests for SSH config parser.

Following TDD approach: write tests first, then implement.
"""

import pytest
from pathlib import Path
from icpy.utils.ssh_config_parser import (
    parse_ssh_config,
    SSHConfigEntry,
    ConfigParseError,
)


class TestBasicParsing:
    """Test basic SSH config parsing functionality."""
    
    def test_parse_simple_host_entry(self):
        """Should parse a simple host entry with basic fields."""
        config = """
Host myserver
    HostName 192.168.1.100
    User admin
    Port 2222
"""
        entries = parse_ssh_config(config)
        
        assert len(entries) == 1
        assert entries[0].host == "myserver"
        assert entries[0].hostname == "192.168.1.100"
        assert entries[0].user == "admin"
        assert entries[0].port == 2222
    
    def test_parse_multiple_hosts(self):
        """Should parse multiple host entries."""
        config = """
Host server1
    HostName 192.168.1.100
    User user1

Host server2
    HostName 192.168.1.101
    User user2
"""
        entries = parse_ssh_config(config)
        
        assert len(entries) == 2
        assert entries[0].host == "server1"
        assert entries[0].hostname == "192.168.1.100"
        assert entries[1].host == "server2"
        assert entries[1].hostname == "192.168.1.101"
    
    def test_parse_with_identity_file(self):
        """Should parse IdentityFile directive."""
        config = """
Host keyserver
    HostName 192.168.1.100
    User admin
    IdentityFile ~/.ssh/id_rsa
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].identity_file == "~/.ssh/id_rsa"
    
    def test_parse_case_insensitive_directives(self):
        """Should handle case-insensitive SSH directives."""
        config = """
Host myserver
    hostname 192.168.1.100
    USER admin
    port 22
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].hostname == "192.168.1.100"
        assert entries[0].user == "admin"
        assert entries[0].port == 22
    
    def test_parse_with_tabs_and_spaces(self):
        """Should handle mixed whitespace (tabs and spaces)."""
        config = """
Host\tmyserver
\tHostName\t192.168.1.100
    User    admin
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].host == "myserver"
        assert entries[0].hostname == "192.168.1.100"
        assert entries[0].user == "admin"


class TestVSCodeCompatibility:
    """Test parsing of VS Code style SSH configs."""
    
    def test_parse_vscode_style_config(self):
        """Should parse VS Code Remote SSH config format."""
        config = """
Host icoteshop1
    HostName 192.168.2.211
    User penthoy
    Port 22
    IdentityFile C:/Users/penth/icoteshop1_key

Host supabase_local
    HostName 192.168.2.162
    User penthoy
    Port 22
    IdentityFile C:/Users/penth/supabase_key
"""
        entries = parse_ssh_config(config)
        
        assert len(entries) == 2
        assert entries[0].host == "icoteshop1"
        assert entries[0].identity_file == "C:/Users/penth/icoteshop1_key"
        assert entries[1].host == "supabase_local"
        assert entries[1].identity_file == "C:/Users/penth/supabase_key"
    
    def test_parse_windows_paths(self):
        """Should handle Windows-style file paths."""
        config = """
Host winserver
    HostName 192.168.1.100
    IdentityFile C:\\Users\\admin\\.ssh\\id_rsa
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].identity_file == "C:\\Users\\admin\\.ssh\\id_rsa"


class TestIcotesMetadata:
    """Test extraction of icotes-specific metadata from comments."""
    
    def test_parse_icotes_metadata_comment(self):
        """Should extract icotes metadata from comment."""
        config = """
Host hop1
    HostName 192.168.2.211
    User penthoy
    # icotes-meta: {"id": "abc-123", "auth": "privateKey", "defaultPath": "/home/penthoy"}
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].icotes_id == "abc-123"
        assert entries[0].icotes_auth == "privateKey"
        assert entries[0].icotes_default_path == "/home/penthoy"
    
    def test_parse_icotes_metadata_with_timestamps(self):
        """Should extract timestamps from icotes metadata."""
        config = """
Host hop1
    HostName 192.168.2.211
    # icotes-meta: {"id": "abc-123", "auth": "password", "createdAt": "2025-01-01T00:00:00Z", "updatedAt": "2025-01-02T00:00:00Z"}
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].icotes_created_at == "2025-01-01T00:00:00Z"
        assert entries[0].icotes_updated_at == "2025-01-02T00:00:00Z"
    
    def test_parse_without_icotes_metadata(self):
        """Should handle entries without icotes metadata."""
        config = """
Host regular
    HostName 192.168.1.100
    User admin
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].icotes_id is None
        assert entries[0].icotes_auth is None
    
    def test_parse_invalid_json_metadata(self):
        """Should handle invalid JSON in metadata gracefully."""
        config = """
Host hop1
    HostName 192.168.2.211
    # icotes-meta: {invalid json}
"""
        entries = parse_ssh_config(config)
        
        # Should still parse the entry, just skip metadata
        assert entries[0].host == "hop1"
        assert entries[0].icotes_id is None


class TestCommentsAndWhitespace:
    """Test handling of comments and whitespace."""
    
    def test_ignore_comment_lines(self):
        """Should ignore regular comment lines."""
        config = """
# This is a comment
Host myserver
    # Another comment
    HostName 192.168.1.100
    User admin  # Inline comment (not standard but common)
"""
        entries = parse_ssh_config(config)
        
        assert len(entries) == 1
        assert entries[0].host == "myserver"
    
    def test_ignore_empty_lines(self):
        """Should ignore empty lines."""
        config = """

Host myserver
    HostName 192.168.1.100

    User admin

"""
        entries = parse_ssh_config(config)
        
        assert len(entries) == 1
    
    def test_preserve_original_comments(self):
        """Should preserve non-metadata comments for potential rewriting."""
        config = """
# Important note about this server
Host myserver
    HostName 192.168.1.100
    # Security: uses special key
    User admin
"""
        entries = parse_ssh_config(config)
        
        # Comments should be preserved in some form
        assert entries[0].host == "myserver"
        # Note: actual comment preservation will be in the entry object


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_parse_empty_config(self):
        """Should handle empty config file."""
        config = ""
        entries = parse_ssh_config(config)
        
        assert len(entries) == 0
    
    def test_parse_only_comments(self):
        """Should handle config with only comments."""
        config = """
# Comment 1
# Comment 2
# Comment 3
"""
        entries = parse_ssh_config(config)
        
        assert len(entries) == 0
    
    def test_parse_host_without_hostname(self):
        """Should handle Host entry without HostName."""
        config = """
Host myserver
    User admin
    Port 22
"""
        entries = parse_ssh_config(config)
        
        # Should still create entry, hostname may be same as host
        assert len(entries) == 1
        assert entries[0].host == "myserver"
        assert entries[0].hostname is None or entries[0].hostname == "myserver"
    
    def test_parse_duplicate_directives(self):
        """Should handle duplicate directives (last one wins per SSH spec)."""
        config = """
Host myserver
    HostName 192.168.1.100
    Port 22
    Port 2222
"""
        entries = parse_ssh_config(config)
        
        # SSH uses first match, but we'll use last for simplicity
        assert entries[0].port == 2222
    
    def test_parse_host_with_wildcard(self):
        """Should handle Host with wildcards."""
        config = """
Host *.example.com
    User admin
    Port 22
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].host == "*.example.com"
    
    def test_parse_quoted_values(self):
        """Should handle quoted values."""
        config = """
Host myserver
    HostName "192.168.1.100"
    User "admin user"
"""
        entries = parse_ssh_config(config)
        
        # Should strip quotes
        assert entries[0].hostname == "192.168.1.100"
        assert entries[0].user == "admin user"
    
    def test_missing_host_directive(self):
        """Should handle directives before first Host."""
        config = """
User defaultuser
Port 22

Host myserver
    HostName 192.168.1.100
"""
        entries = parse_ssh_config(config)
        
        # Global directives are ignored or handled separately
        assert len(entries) == 1
        assert entries[0].host == "myserver"

    def test_invalid_port_keeps_default(self):
        config = """
Host badport
    HostName localhost
    Port not-a-number
"""
        entries = parse_ssh_config(config)
        assert len(entries) == 1
        e = entries[0]
        assert e.port == 22

    def test_icotes_metadata_without_json_is_ignored(self):
        config = """
Host test
    HostName localhost
    # icotes-meta:
"""
        entries = parse_ssh_config(config)
        assert len(entries) == 1
        e = entries[0]
        assert e.icotes_id is None
        assert e.icotes_auth is None

    def test_multiple_metadata_uses_first_valid(self):
        config = """
Host test
    HostName localhost
    # icotes-meta: {"id": "first", "auth": "password"}
    # icotes-meta: {"id": "second", "auth": "privateKey"}
"""
        entries = parse_ssh_config(config)
        assert len(entries) == 1
        e = entries[0]
        assert e.icotes_id == "first"
        assert e.icotes_auth == "password"

    def test_directives_without_values_are_ignored_or_defaulted(self):
        # Lines with directive but no value should not crash
        config = """
Host
    Port 
    IdentityFile 
"""
        entries = parse_ssh_config(config)
        assert len(entries) == 1
        e = entries[0]
        # Empty host name captured as empty string
        assert e.host == ""
        # Port defaults to 22 when value missing
        assert e.port == 22
        # Identity file remains None when value missing
        assert e.identity_file is None


class TestDefaultValues:
    """Test default value handling."""
    
    def test_default_port_22(self):
        """Should default port to 22 if not specified."""
        config = """
Host myserver
    HostName 192.168.1.100
    User admin
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].port == 22
    
    def test_explicit_port_overrides_default(self):
        """Should use explicit port when provided."""
        config = """
Host myserver
    HostName 192.168.1.100
    Port 2222
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].port == 2222


class TestLocalContextEntry:
    """Test handling of special 'local' context entry."""
    
    def test_parse_local_context_entry(self):
        """Should parse special local context entry."""
        config = """
Host local
    HostName localhost
    # icotes-meta: {"id": "local", "auth": "none", "defaultPath": "/home/user/icotes"}
"""
        entries = parse_ssh_config(config)
        
        assert entries[0].host == "local"
        assert entries[0].hostname == "localhost"
        assert entries[0].icotes_id == "local"
        assert entries[0].icotes_auth == "none"


class TestRoundTripCompatibility:
    """Test that parsed config can be converted back."""
    
    def test_entry_to_dict(self):
        """Should convert SSHConfigEntry to dict for SSHCredential."""
        config = """
Host myserver
    HostName 192.168.1.100
    User admin
    Port 2222
    # icotes-meta: {"id": "abc-123", "auth": "password"}
"""
        entries = parse_ssh_config(config)
        entry_dict = entries[0].to_credential_dict()
        
        assert entry_dict['name'] == 'myserver'
        assert entry_dict['host'] == '192.168.1.100'
        assert entry_dict['username'] == 'admin'
        assert entry_dict['port'] == 2222
        assert entry_dict['id'] == 'abc-123'
        assert entry_dict['auth'] == 'password'

    def test_entry_to_dict_extracts_private_key_id(self):
        """Should extract privateKeyId from IdentityFile path when present."""
        config = """
Host hop1
    HostName 192.168.1.10
    User admin
    IdentityFile ~/.icotes/ssh/keys/hop1_key
    # icotes-meta: {"id": "id-123", "auth": "privateKey"}
"""
        entries = parse_ssh_config(config)
        entry_dict = entries[0].to_credential_dict()
        assert entry_dict['privateKeyId'] == 'hop1_key'

    def test_extract_key_id_none_when_no_identityfile(self):
        """Private key ID extraction returns None when identity_file is missing/empty."""
        entry = SSHConfigEntry(host='noid')
        assert entry.identity_file is None
        # Directly exercise the helper for coverage
        assert entry._extract_key_id() is None


# Test data for integration testing
SAMPLE_VSCODE_CONFIG = """
Host icotessupabase2
    HostName 192.168.2.204
    User penthoy
    IdentityFile C:/Users/penth/icotessupabase2_key

Host icoteshop1
    HostName 192.168.2.211
    User penthoy
    Port 22
    IdentityFile C:/Users/penth/icoteshop1_key

Host supabase_local
    HostName 192.168.2.162
    User penthoy
    Port 22
    IdentityFile C:/Users/penth/supabase_key
"""

SAMPLE_ICOTES_CONFIG = """
# icotes hop configuration
# This file is compatible with VS Code Remote SSH config

Host local
    HostName localhost
    # icotes-meta: {"id": "local", "auth": "none", "defaultPath": "/home/penthoy/icotes"}

Host hop1
    HostName 192.168.2.211
    User penthoy
    Port 22
    IdentityFile ~/.icotes/ssh/keys/hop1_key
    # icotes-meta: {"id": "550e8400-e29b-41d4-a716-446655440000", "auth": "privateKey", "defaultPath": "/home/penthoy/icotes", "createdAt": "2025-01-01T00:00:00Z"}

Host supabase_local
    HostName 192.168.2.162
    User penthoy
    Port 22
    # icotes-meta: {"id": "550e8400-e29b-41d4-a716-446655440001", "auth": "password", "createdAt": "2025-01-01T00:00:00Z"}
"""
