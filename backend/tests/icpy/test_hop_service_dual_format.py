"""
Integration tests for HopService with dual-format support (JSON + SSH config).

Tests Phase 2: HopService should support both formats simultaneously.
"""

import json
import pytest
from pathlib import Path
from icpy.services.hop_service import HopService, SSHCredential


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    icotes_dir = workspace / ".icotes" / "ssh"
    icotes_dir.mkdir(parents=True)
    return workspace


@pytest.fixture
def hop_dir(temp_workspace):
    """Create hop directory."""
    hop = temp_workspace / ".icotes" / "hop"
    hop.mkdir(parents=True)
    return hop


class TestDualFormatLoading:
    """Test loading credentials from both JSON and config formats."""
    
    def test_load_from_json_only(self, temp_workspace, monkeypatch):
        """Should load credentials from JSON when config doesn't exist (legacy behavior before migration)."""
        from unittest.mock import patch
        
        # Create JSON credentials file
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        creds_file = ssh_dir / "credentials.json"
        
        creds_data = [
            {
                "id": "test-1",
                "name": "server1",
                "host": "192.168.1.100",
                "port": 22,
                "username": "admin",
                "auth": "password",
            }
        ]
        creds_file.write_text(json.dumps(creds_data))
        
        # Mock workspace root
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        # Mock migration to not run (simulate legacy behavior)
        with patch('icpy.services.hop_service.should_migrate', return_value=False):
            # Create service
            service = HopService()
            
            # Should load from JSON
            creds = service.list_credentials()
            assert len(creds) == 1
            assert creds[0]['name'] == 'server1'
            assert service.get_config_format() == 'json'
    
    def test_load_from_config_only(self, temp_workspace, hop_dir, monkeypatch):
        """Should load credentials from config when JSON doesn't exist."""
        # Create SSH config file
        config_file = hop_dir / "config"
        config_text = """
# icotes hop configuration

Host server1
    HostName 192.168.1.100
    User admin
    Port 22
    # icotes-meta: {"id": "test-1", "auth": "password"}
"""
        config_file.write_text(config_text)
        
        # Mock workspace root
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        # Create service
        service = HopService()
        
        # Should load from config
        creds = service.list_credentials()
        assert len(creds) == 1
        assert creds[0]['name'] == 'server1'
        assert service.get_config_format() == 'config'
    
    def test_prefer_config_when_both_exist(self, temp_workspace, hop_dir, monkeypatch):
        """Should prefer config format when both JSON and config exist."""
        # Create JSON credentials
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        creds_file = ssh_dir / "credentials.json"
        creds_data = [{"id": "json-1", "name": "json_server", "host": "192.168.1.1", "port": 22}]
        creds_file.write_text(json.dumps(creds_data))
        
        # Create config file
        config_file = hop_dir / "config"
        config_text = """
Host config_server
    HostName 192.168.1.2
    # icotes-meta: {"id": "config-1", "auth": "password"}
"""
        config_file.write_text(config_text)
        
        # Mock workspace root
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        # Create service
        service = HopService()
        
        # Should load from config (preferred)
        creds = service.list_credentials()
        assert len(creds) == 1
        assert creds[0]['name'] == 'config_server'
        assert service.get_config_format() == 'config'


class TestDualFormatSaving:
    """Test saving credentials to both formats during transition."""
    
    @pytest.mark.asyncio
    async def test_save_updates_both_formats(self, temp_workspace, hop_dir, monkeypatch):
        """Phase 5: Should update config only (JSON is deprecated)."""
        # Start with JSON credentials
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        creds_file = ssh_dir / "credentials.json"
        creds_data = [{"id": "test-1", "name": "server1", "host": "192.168.1.100", "port": 22, "username": "admin", "auth": "password"}]
        creds_file.write_text(json.dumps(creds_data))
        
        # Mock workspace root
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        # Create service (will auto-migrate)
        service = HopService()
        
        # Create new credential
        new_cred = service.create_credential({
            "name": "server2",
            "host": "192.168.1.101",
            "port": 22,
            "username": "admin2",
            "auth": "password",
        })
        
        # Config file should exist and be updated
        assert (hop_dir / "config").exists()
        
        # JSON should still exist (from migration) but NOT be updated
        assert creds_file.exists()
        json_data = json.loads(creds_file.read_text())
        assert len(json_data) == 1  # Phase 5: JSON is not updated anymore
        
        # Config should have both credentials (original + new)
        config_text = (hop_dir / "config").read_text()
        assert "Host server1" in config_text
        assert "Host server2" in config_text
    
    @pytest.mark.asyncio
    async def test_update_credential_updates_both_formats(self, temp_workspace, hop_dir, monkeypatch):
        """Phase 5: Should update config only (JSON is deprecated)."""
        # Start with config file
        config_file = hop_dir / "config"
        config_text = """
Host server1
    HostName 192.168.1.100
    User admin
    Port 22
    # icotes-meta: {"id": "test-1", "auth": "password"}
"""
        config_file.write_text(config_text)
        
        # Mock workspace root
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        # Create service
        service = HopService()
        
        # Update credential
        updated = service.update_credential("test-1", {
            "name": "server1_updated",
            "host": "192.168.1.200"
        })
        
        # Config should be updated with new values
        updated_config = config_file.read_text()
        assert "Host server1_updated" in updated_config
        assert "HostName 192.168.1.200" in updated_config
        assert updated is not None
        assert updated['name'] == "server1_updated"
        assert updated['host'] == "192.168.1.200"
        
        # Config should be updated with new values
        config_text = config_file.read_text()
        assert "192.168.1.200" in config_text
        
        # Phase 5: JSON should not be created or updated
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        # JSON file should not exist since we only write to config
        assert not json_file.exists()


class TestConfigFormatMethod:
    """Test get_config_format() method."""
    
    def test_reports_json_format(self, temp_workspace, monkeypatch):
        """Should report 'json' when using JSON format (with migration disabled)."""
        from unittest.mock import patch
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text("[]")
        
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        # Mock migration to not run
        with patch('icpy.services.hop_service.should_migrate', return_value=False):
            service = HopService()
            assert service.get_config_format() == 'json'
    
    def test_reports_config_format(self, temp_workspace, hop_dir, monkeypatch):
        """Should report 'config' when using config format."""
        config_file = hop_dir / "config"
        config_file.write_text("# icotes hop configuration\n")
        
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        service = HopService()
        assert service.get_config_format() == 'config'


class TestBackwardCompatibility:
    """Test backward compatibility with existing JSON credentials."""
    
    @pytest.mark.asyncio
    async def test_existing_json_continues_to_work(self, temp_workspace, monkeypatch):
        """Should continue to work with existing JSON credentials."""
        # Create realistic JSON credentials file
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        keys_dir = ssh_dir / "keys"
        keys_dir.mkdir(parents=True)
        
        creds_file = ssh_dir / "credentials.json"
        creds_data = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "hop1",
                "host": "192.168.2.211",
                "port": 22,
                "username": "penthoy",
                "auth": "privateKey",
                "privateKeyId": "hop1_key",
                "defaultPath": "/home/penthoy/icotes",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z",
            }
        ]
        creds_file.write_text(json.dumps(creds_data))
        
        # Create dummy key file
        (keys_dir / "hop1_key").write_text("dummy key content")
        
        # Mock workspace root
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        # Create service
        service = HopService()
        
        # Should load existing credentials
        creds = service.list_credentials()
        assert len(creds) == 1
        assert creds[0]['name'] == 'hop1'
        assert creds[0]['auth'] == 'privateKey'
        assert creds[0]['defaultPath'] == '/home/penthoy/icotes'
        
        # Should be able to add new credentials
        new_cred = service.create_credential({
            "name": "hop2",
            "host": "192.168.2.212",
            "port": 22,
            "username": "penthoy",
            "auth": "password",
        })
        
        assert new_cred is not None
        assert service.get_credential(new_cred['id']) is not None


class TestConfigFileGeneration:
    """Test that config files are generated correctly."""
    
    @pytest.mark.asyncio
    async def test_generated_config_is_valid(self, temp_workspace, hop_dir, monkeypatch):
        """Should generate valid SSH config file."""
        # Start with JSON
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        creds_file = ssh_dir / "credentials.json"
        creds_data = [
            {
                "id": "test-1",
                "name": "myserver",
                "host": "192.168.1.100",
                "port": 2222,
                "username": "admin",
                "auth": "password",
                "defaultPath": "/home/admin/workspace",
            }
        ]
        creds_file.write_text(json.dumps(creds_data))
        
        # Mock workspace root
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        # Create service (should generate config)
        service = HopService()
        
        # Verify config file was created
        config_file = hop_dir / "config"
        assert config_file.exists()
        
        # Verify config content
        config_text = config_file.read_text()
        assert "Host myserver" in config_text
        assert "HostName 192.168.1.100" in config_text
        assert "Port 2222" in config_text
        assert "User admin" in config_text
        assert '"defaultPath": "/home/admin/workspace"' in config_text
