"""
Tests for HopService automatic migration integration.
"""

import json
from pathlib import Path
import pytest
from icpy.services.hop_service import HopService


@pytest.fixture
def clean_hop_dir(tmp_path, monkeypatch):
    """Create a clean hop directory for testing."""
    hop_dir = tmp_path / ".icotes" / "hop"
    hop_dir.mkdir(parents=True)
    ssh_dir = tmp_path / ".icotes" / "ssh"
    ssh_dir.mkdir(parents=True)
    
    # Mock workspace root using WORKSPACE_ROOT env var
    monkeypatch.setenv('WORKSPACE_ROOT', str(tmp_path))
    
    return tmp_path


class TestAutoMigration:
    """Test automatic migration on HopService initialization."""
    
    def test_no_migration_when_config_exists(self, clean_hop_dir):
        """Should not migrate if config file already exists."""
        hop_dir = clean_hop_dir / ".icotes" / "hop"
        config_path = hop_dir / "config"
        
        # Create existing config
        config_path.write_text("# Existing config\n")
        
        # Initialize service (should not migrate)
        service = HopService()
        
        # Config should still exist unchanged
        assert config_path.exists()
        assert config_path.read_text() == "# Existing config\n"
    
    def test_no_migration_when_no_json(self, clean_hop_dir):
        """Should not migrate if no JSON file exists."""
        # Initialize service (should not migrate)
        service = HopService()
        
        hop_dir = clean_hop_dir / ".icotes" / "hop"
        config_path = hop_dir / "config"
        
        # Config should not be created
        assert not config_path.exists()
    
    def test_auto_migration_on_startup(self, clean_hop_dir):
        """Should automatically migrate JSON to config on first startup."""
        ssh_dir = clean_hop_dir / ".icotes" / "ssh"
        hop_dir = clean_hop_dir / ".icotes" / "hop"
        
        # Create legacy JSON credentials (list format)
        creds_data = [
            {
                "id": "hop1",
                "name": "Production Server",
                "host": "prod.example.com",
                "port": 22,
                "username": "deploy",
                "auth": "privateKey",
                "privateKeyId": "prod-key-uuid"
            }
        ]
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text(json.dumps(creds_data, indent=2))
        
        # Create key file
        key_path = ssh_dir / "keys" / "prod-key-uuid"
        key_path.parent.mkdir(exist_ok=True)
        key_path.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nfake key\n-----END OPENSSH PRIVATE KEY-----")
        
        # Initialize service (should trigger migration)
        service = HopService()
        
        # Config should be created
        config_path = hop_dir / "config"
        assert config_path.exists()
        
        # Config should contain the credential
        config_content = config_path.read_text()
        assert "Host Production Server" in config_content
        assert "HostName prod.example.com" in config_content
        assert "User deploy" in config_content
        
        # Key file should be renamed to use the host name
        new_key_path = ssh_dir / "keys" / "Production Server_key"
        assert new_key_path.exists()
        assert not key_path.exists()
        
        # JSON backup should exist
        backup_path = ssh_dir / "credentials.json.bak"
        assert backup_path.exists()
    
    def test_auto_migration_loads_credentials(self, clean_hop_dir):
        """Should load credentials after auto-migration."""
        ssh_dir = clean_hop_dir / ".icotes" / "ssh"
        
        # Create legacy JSON credentials (list format)
        creds_data = [
            {
                "id": "hop1",
                "name": "Test Server",
                "host": "test.example.com",
                "port": 2222,
                "username": "testuser",
                "auth": "privateKey",
                "privateKeyId": "test-key"
            }
        ]
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text(json.dumps(creds_data, indent=2))
        
        # Create key file
        key_path = ssh_dir / "keys" / "test-key"
        key_path.parent.mkdir(exist_ok=True)
        key_path.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\ntest key\n-----END OPENSSH PRIVATE KEY-----")
        
        # Initialize service
        service = HopService()
        
        # Credential should be loaded
        creds = service.list_credentials()
        assert len(creds) == 1
        
        cred = creds[0]
        assert cred["id"] == "hop1"
        assert cred["name"] == "Test Server"
        assert cred["host"] == "test.example.com"
        assert cred["port"] == 2222
        assert cred["username"] == "testuser"
    
    def test_auto_migration_with_multiple_credentials(self, clean_hop_dir):
        """Should migrate multiple credentials correctly."""
        ssh_dir = clean_hop_dir / ".icotes" / "ssh"
        
        # Create multiple legacy credentials (list format)
        creds_data = [
            {
                "id": "hop1",
                "name": "Server One",
                "host": "one.example.com",
                "port": 22,
                "username": "user1",
                "auth": "privateKey",
                "privateKeyId": "key-1"
            },
            {
                "id": "hop2",
                "name": "Server Two",
                "host": "two.example.com",
                "port": 22,
                "username": "user2",
                "auth": "privateKey",
                "privateKeyId": "key-2"
            }
        ]
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text(json.dumps(creds_data, indent=2))
        
        # Create key files
        keys_dir = ssh_dir / "keys"
        keys_dir.mkdir(exist_ok=True)
        (keys_dir / "key-1").write_text("key 1")
        (keys_dir / "key-2").write_text("key 2")
        
        # Initialize service
        service = HopService()
        
        # Both credentials should be loaded
        creds = service.list_credentials()
        assert len(creds) == 2
        
        # Keys should be renamed to use host names
        assert (keys_dir / "Server One_key").exists()
        assert (keys_dir / "Server Two_key").exists()
        assert not (keys_dir / "key-1").exists()
        assert not (keys_dir / "key-2").exists()
    
    def test_auto_migration_handles_errors_gracefully(self, clean_hop_dir):
        """Should not crash if migration fails."""
        ssh_dir = clean_hop_dir / ".icotes" / "ssh"
        
        # Create invalid JSON
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text("{invalid json}")
        
        # Should not raise exception
        service = HopService()
        
        # Should still work with empty credentials
        creds = service.list_credentials()
        assert creds == []
    
    def test_migration_runs_once_only(self, clean_hop_dir):
        """Should only migrate once, not on every startup."""
        ssh_dir = clean_hop_dir / ".icotes" / "ssh"
        hop_dir = clean_hop_dir / ".icotes" / "hop"
        
        # Create legacy JSON (list format)
        creds_data = [{"id": "hop1", "name": "Test", "host": "test.com", "port": 22, "username": "user", "auth": "password"}]
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text(json.dumps(creds_data))
        
        # First startup - should migrate
        service1 = HopService()
        config_path = hop_dir / "config"
        assert config_path.exists()
        
        # Modify config
        original_content = config_path.read_text()
        config_path.write_text(original_content + "\n# Manual edit\n")
        
        # Second startup - should NOT re-migrate
        service2 = HopService()
        
        # Manual edit should still be there
        assert "# Manual edit" in config_path.read_text()
        
        # Backup should exist but JSON should still be present (from first migration)
        assert (ssh_dir / "credentials.json.bak").exists()


class TestMigrationEdgeCases:
    """Test edge cases in migration integration."""
    
    def test_migration_with_missing_key_file(self, clean_hop_dir):
        """Should handle missing key files gracefully."""
        ssh_dir = clean_hop_dir / ".icotes" / "ssh"
        
        # Create credential with missing key (list format)
        creds_data = [
            {
                "id": "hop1",
                "name": "Test",
                "host": "test.com",
                "port": 22,
                "username": "user",
                "auth": "privateKey",
                "privateKeyId": "missing-key"
            }
        ]
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text(json.dumps(creds_data))
        
        # Should not crash
        service = HopService()
        
        # Config should still be created
        config_path = clean_hop_dir / ".icotes" / "hop" / "config"
        assert config_path.exists()
        
        # Credential should be in config but without key rename (uses name as Host)
        config_content = config_path.read_text()
        assert "Host Test" in config_content
        assert "IdentityFile" in config_content
    
    def test_migration_preserves_all_fields(self, clean_hop_dir):
        """Should preserve all credential fields during migration."""
        ssh_dir = clean_hop_dir / ".icotes" / "ssh"
        
        # Create credential with all fields (list format)
        creds_data = [
            {
                "id": "hop1",
                "name": "Full Featured Server",
                "host": "server.example.com",
                "port": 2222,
                "username": "admin",
                "auth": "privateKey",
                "privateKeyId": "server-key"
            }
        ]
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text(json.dumps(creds_data))
        
        # Create key
        key_path = ssh_dir / "keys" / "server-key"
        key_path.parent.mkdir(exist_ok=True)
        key_path.write_text("key content")
        
        # Migrate
        service = HopService()
        
        # Load and verify all fields
        creds = service.list_credentials()
        assert len(creds) == 1
        
        cred = creds[0]
        assert cred["name"] == "Full Featured Server"
        assert cred["host"] == "server.example.com"
        assert cred["port"] == 2222
        assert cred["username"] == "admin"

