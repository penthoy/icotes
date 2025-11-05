"""
Tests for hop config migration script.

Following TDD approach: write tests first, then implement.
"""

import json
import shutil
import pytest
from pathlib import Path
from icpy.scripts.migrate_hop_config import (
    migrate_credentials_to_config,
    should_migrate,
    MigrationResult,
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    ssh_dir = workspace / ".icotes" / "ssh"
    ssh_dir.mkdir(parents=True)
    keys_dir = ssh_dir / "keys"
    keys_dir.mkdir()
    return workspace


@pytest.fixture
def hop_dir(temp_workspace):
    """Create hop directory."""
    hop = temp_workspace / ".icotes" / "hop"
    hop.mkdir(parents=True)
    return hop


class TestShouldMigrate:
    """Test migration detection logic."""
    
    def test_should_migrate_when_json_exists_and_config_missing(self, temp_workspace, hop_dir):
        """Should return True when JSON exists but config doesn't."""
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        json_file.write_text("[]")
        
        assert should_migrate(temp_workspace) is True
    
    def test_should_not_migrate_when_config_exists(self, temp_workspace, hop_dir):
        """Should return False when config already exists."""
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        json_file.write_text("[]")
        
        config_file = hop_dir / "config"
        config_file.write_text("# icotes hop configuration\n")
        
        assert should_migrate(temp_workspace) is False
    
    def test_should_not_migrate_when_json_missing(self, temp_workspace):
        """Should return False when JSON file doesn't exist."""
        assert should_migrate(temp_workspace) is False
    
    def test_should_not_migrate_when_both_missing(self, temp_workspace):
        """Should return False when neither file exists."""
        assert should_migrate(temp_workspace) is False

    def test_migrate_returns_skipped_when_no_json(self, temp_workspace):
        """migrate_credentials_to_config should skip clean workspaces with no JSON present."""
        result = migrate_credentials_to_config(temp_workspace)
        assert result.success is True
        assert result.skipped is True
        assert "No JSON credentials file found" in result.message


class TestBasicMigration:
    """Test basic migration functionality."""
    
    def test_migrate_empty_credentials(self, temp_workspace, hop_dir, monkeypatch):
        """Should handle empty credentials list."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        json_file.write_text("[]")
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert result.success is True
        assert result.credentials_migrated == 0
        assert result.keys_renamed == 0
        assert (hop_dir / "config").exists()
    
    def test_migrate_single_password_credential(self, temp_workspace, hop_dir, monkeypatch):
        """Should migrate a single password-based credential."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        
        creds_data = [{
            "id": "test-1",
            "name": "myserver",
            "host": "192.168.1.100",
            "port": 22,
            "username": "admin",
            "auth": "password",
            "createdAt": "2025-01-01T00:00:00Z",
        }]
        json_file.write_text(json.dumps(creds_data))
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert result.success is True
        assert result.credentials_migrated == 1
        assert (hop_dir / "config").exists()
        
        # Verify config content
        config_text = (hop_dir / "config").read_text()
        assert "Host myserver" in config_text
        assert "HostName 192.168.1.100" in config_text
        assert "User admin" in config_text
    
    def test_migrate_multiple_credentials(self, temp_workspace, hop_dir, monkeypatch):
        """Should migrate multiple credentials."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        
        creds_data = [
            {"id": "test-1", "name": "server1", "host": "192.168.1.100", "port": 22, "username": "user1", "auth": "password"},
            {"id": "test-2", "name": "server2", "host": "192.168.1.101", "port": 22, "username": "user2", "auth": "password"},
            {"id": "test-3", "name": "server3", "host": "192.168.1.102", "port": 2222, "username": "user3", "auth": "password"},
        ]
        json_file.write_text(json.dumps(creds_data))
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert result.success is True
        assert result.credentials_migrated == 3
        
        config_text = (hop_dir / "config").read_text()
        assert "Host server1" in config_text
        assert "Host server2" in config_text
        assert "Host server3" in config_text


class TestKeyFileRenaming:
    """Test private key file renaming."""
    
    def test_rename_key_file_from_uuid_to_name(self, temp_workspace, hop_dir, monkeypatch):
        """Should rename key file from UUID to credential name."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        keys_dir = ssh_dir / "keys"
        json_file = ssh_dir / "credentials.json"
        
        # Create key file with UUID name
        old_key_id = "550e8400-e29b-41d4-a716-446655440000"
        old_key_file = keys_dir / old_key_id
        old_key_file.write_text("dummy private key content")
        
        creds_data = [{
            "id": "test-1",
            "name": "hop1",
            "host": "192.168.2.211",
            "port": 22,
            "username": "penthoy",
            "auth": "privateKey",
            "privateKeyId": old_key_id,
        }]
        json_file.write_text(json.dumps(creds_data))
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert result.success is True
        assert result.keys_renamed == 1
        
        # Old key file should be renamed
        new_key_file = keys_dir / "hop1_key"
        assert new_key_file.exists()
        assert new_key_file.read_text() == "dummy private key content"
        assert not old_key_file.exists()
        
        # Config should reference new key name
        config_text = (hop_dir / "config").read_text()
        assert "hop1_key" in config_text
    
    def test_rename_multiple_key_files(self, temp_workspace, hop_dir, monkeypatch):
        """Should rename multiple key files."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        keys_dir = ssh_dir / "keys"
        json_file = ssh_dir / "credentials.json"
        
        # Create multiple key files
        key1_id = "550e8400-e29b-41d4-a716-446655440000"
        key2_id = "550e8400-e29b-41d4-a716-446655440001"
        (keys_dir / key1_id).write_text("key1 content")
        (keys_dir / key2_id).write_text("key2 content")
        
        creds_data = [
            {"id": "test-1", "name": "server1", "host": "192.168.1.100", "port": 22, "auth": "privateKey", "privateKeyId": key1_id},
            {"id": "test-2", "name": "server2", "host": "192.168.1.101", "port": 22, "auth": "privateKey", "privateKeyId": key2_id},
        ]
        json_file.write_text(json.dumps(creds_data))
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert result.success is True
        assert result.keys_renamed == 2
        
        assert (keys_dir / "server1_key").exists()
        assert (keys_dir / "server2_key").exists()
    
    def test_skip_key_rename_if_file_missing(self, temp_workspace, hop_dir, monkeypatch):
        """Should skip key rename if file doesn't exist."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        
        creds_data = [{
            "id": "test-1",
            "name": "server1",
            "host": "192.168.1.100",
            "port": 22,
            "auth": "privateKey",
            "privateKeyId": "nonexistent-key-id",
        }]
        json_file.write_text(json.dumps(creds_data))
        
        result = migrate_credentials_to_config(temp_workspace)
        
        # Should succeed but warn about missing key
        assert result.success is True
        assert result.keys_renamed == 0
        assert len(result.warnings) > 0
        assert any("nonexistent-key-id" in w for w in result.warnings)


class TestBackupCreation:
    """Test backup creation during migration."""
    
    def test_creates_json_backup(self, temp_workspace, hop_dir, monkeypatch):
        """Should create backup of JSON file."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        
        creds_data = [{"id": "test-1", "name": "server1", "host": "192.168.1.100", "port": 22, "auth": "password"}]
        json_file.write_text(json.dumps(creds_data))
        
        migrate_credentials_to_config(temp_workspace)
        
        # Backup should exist
        backup_file = ssh_dir / "credentials.json.bak"
        assert backup_file.exists()
        
        # Backup should have same content as original
        assert backup_file.read_text() == json_file.read_text()
    
    def test_overwrites_existing_backup(self, temp_workspace, hop_dir, monkeypatch):
        """Should overwrite existing backup file."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        backup_file = ssh_dir / "credentials.json.bak"
        
        # Create old backup
        backup_file.write_text("old backup content")
        
        creds_data = [{"id": "test-1", "name": "server1", "host": "192.168.1.100", "port": 22, "auth": "password"}]
        json_file.write_text(json.dumps(creds_data))
        
        migrate_credentials_to_config(temp_workspace)
        
        # Backup should be updated
        assert backup_file.read_text() != "old backup content"
        assert "server1" in backup_file.read_text()


class TestIdempotency:
    """Test that migration is idempotent (safe to run multiple times)."""
    
    def test_second_migration_does_nothing(self, temp_workspace, hop_dir, monkeypatch):
        """Should not migrate if config already exists."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        
        creds_data = [{"id": "test-1", "name": "server1", "host": "192.168.1.100", "port": 22, "auth": "password"}]
        json_file.write_text(json.dumps(creds_data))
        
        # First migration
        result1 = migrate_credentials_to_config(temp_workspace)
        assert result1.success is True
        assert result1.credentials_migrated == 1
        
        # Second migration should skip
        result2 = migrate_credentials_to_config(temp_workspace)
        assert result2.success is True
        assert result2.credentials_migrated == 0
        assert result2.skipped is True
        assert "already exists" in result2.message
    
    def test_safe_to_run_multiple_times(self, temp_workspace, hop_dir, monkeypatch):
        """Should be safe to run multiple times."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        
        creds_data = [{"id": "test-1", "name": "server1", "host": "192.168.1.100", "port": 22, "auth": "password"}]
        json_file.write_text(json.dumps(creds_data))
        
        # Run migration 3 times
        for i in range(3):
            result = migrate_credentials_to_config(temp_workspace)
            assert result.success is True


class TestErrorHandling:
    """Test error handling and rollback."""
    
    def test_handles_malformed_json(self, temp_workspace, hop_dir, monkeypatch):
        """Should handle malformed JSON gracefully."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        json_file.write_text("{invalid json")
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert result.success is False
        assert "JSON" in result.error or "parse" in result.error.lower()

    def test_handles_non_list_credentials(self, tmp_path, monkeypatch):
        workspace = tmp_path
        ssh_dir = workspace / ".icotes" / "ssh"
        ssh_dir.mkdir(parents=True)
        creds_file = ssh_dir / "credentials.json"
        # Write a dict instead of a list
        creds_file.write_text("{}", encoding="utf-8")
        # Ensure no existing config so migration attempts to run
        hop_dir = workspace / ".icotes" / "hop"
        if hop_dir.exists():
            shutil.rmtree(hop_dir)
        
        from icpy.scripts.migrate_hop_config import migrate_credentials_to_config
        result = migrate_credentials_to_config(workspace)
        assert not result.success
        assert result.error and "Credentials must be a list" in result.error

    def test_handles_config_write_error_gracefully(self, tmp_path, monkeypatch):
        # Simulate write failure when writing config file
        workspace = tmp_path
        ssh_dir = workspace / ".icotes" / "ssh"
        ssh_dir.mkdir(parents=True)
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text("[]", encoding="utf-8")
        
        # Monkeypatch Path.write_text to raise an error only for the config path
        from pathlib import Path as _Path
        real_write_text = _Path.write_text
        def flaky_write(self, *args, **kwargs):
            if str(self).endswith("/.icotes/hop/config"):
                raise OSError("disk full")
            return real_write_text(self, *args, **kwargs)
        monkeypatch.setattr(_Path, "write_text", flaky_write)
        
        from icpy.scripts.migrate_hop_config import migrate_credentials_to_config
        result = migrate_credentials_to_config(workspace)
        assert not result.success
        assert result.error and "Migration failed" in result.error

    def test_chmod_exception_is_ignored(self, tmp_path, monkeypatch):
        # Verify chmod failure does not abort migration
        workspace = tmp_path
        ssh_dir = workspace / ".icotes" / "ssh"
        ssh_dir.mkdir(parents=True)
        creds_file = ssh_dir / "credentials.json"
        creds_file.write_text("[]", encoding="utf-8")
        
        import os as _os
        real_chmod = _os.chmod
        def selective_chmod(path, mode, *args, **kwargs):
            # Only raise for the final config file, not for the backup copy
            p = str(path)
            if p.endswith("/.icotes/hop/config"):
                raise PermissionError("nope")
            return real_chmod(path, mode)
        monkeypatch.setattr(_os, "chmod", selective_chmod)
        
        from icpy.scripts.migrate_hop_config import migrate_credentials_to_config
        result = migrate_credentials_to_config(workspace)
        # Migration should still succeed even if chmod fails
        assert result.success
    
    def test_preserves_original_on_error(self, temp_workspace, hop_dir, monkeypatch):
        """Should preserve original JSON if migration fails."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        
        original_content = json.dumps([{"id": "test-1", "name": "server1", "host": "192.168.1.100"}])
        json_file.write_text(original_content)
        
        # Even if migration has issues, original should be intact
        migrate_credentials_to_config(temp_workspace)
        
        # Original file should still exist and be valid
        assert json_file.exists()
        assert json.loads(json_file.read_text())


class TestMigrationResult:
    """Test MigrationResult data structure."""
    
    def test_result_contains_all_fields(self, temp_workspace, hop_dir, monkeypatch):
        """Should return result with all required fields."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        json_file.write_text("[]")
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert hasattr(result, 'success')
        assert hasattr(result, 'credentials_migrated')
        assert hasattr(result, 'keys_renamed')
        assert hasattr(result, 'message')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'error')
        assert hasattr(result, 'skipped')
    
    def test_result_includes_warnings(self, temp_workspace, hop_dir, monkeypatch):
        """Should include warnings in result."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        json_file = ssh_dir / "credentials.json"
        
        # Credential with missing key file
        creds_data = [{
            "id": "test-1",
            "name": "server1",
            "host": "192.168.1.100",
            "port": 22,
            "auth": "privateKey",
            "privateKeyId": "missing-key",
        }]
        json_file.write_text(json.dumps(creds_data))
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert len(result.warnings) > 0
        assert any("missing" in w.lower() for w in result.warnings)


class TestRealWorldScenarios:
    """Test real-world migration scenarios."""
    
    def test_migrate_realistic_credentials(self, temp_workspace, hop_dir, monkeypatch):
        """Should migrate realistic credential set."""
        monkeypatch.setenv('WORKSPACE_ROOT', str(temp_workspace))
        
        ssh_dir = temp_workspace / ".icotes" / "ssh"
        keys_dir = ssh_dir / "keys"
        json_file = ssh_dir / "credentials.json"
        
        # Create realistic key file
        key_id = "550e8400-e29b-41d4-a716-446655440000"
        (keys_dir / key_id).write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIE...")
        
        creds_data = [
            {
                "id": "cred-1",
                "name": "hop1",
                "host": "192.168.2.211",
                "port": 22,
                "username": "penthoy",
                "auth": "privateKey",
                "privateKeyId": key_id,
                "defaultPath": "/home/penthoy/icotes",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z",
            },
            {
                "id": "cred-2",
                "name": "supabase_local",
                "host": "192.168.2.162",
                "port": 22,
                "username": "penthoy",
                "auth": "password",
                "defaultPath": "/home/penthoy/supabase",
                "createdAt": "2025-01-01T00:00:00Z",
            },
        ]
        json_file.write_text(json.dumps(creds_data, indent=2))
        
        result = migrate_credentials_to_config(temp_workspace)
        
        assert result.success is True
        assert result.credentials_migrated == 2
        assert result.keys_renamed == 1
        
        # Verify config content
        config_text = (hop_dir / "config").read_text()
        assert "Host hop1" in config_text
        assert "Host supabase_local" in config_text
        assert "hop1_key" in config_text
        assert "defaultPath" in config_text
