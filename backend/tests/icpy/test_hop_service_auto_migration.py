"""
Tests for automatic migration in HopService.

Verifies that HopService runs migration automatically on startup when needed.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from icpy.services.hop_service import HopService
from icpy.scripts.migrate_hop_config import MigrationResult


class TestAutoMigration:
    """Test automatic migration on HopService startup."""
    
    @pytest.fixture
    def mock_workspace(self, tmp_path):
        """Set up a mock workspace directory."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # Create directory structure
        ssh_dir = workspace / ".icotes" / "ssh"
        ssh_dir.mkdir(parents=True)
        hop_dir = workspace / ".icotes" / "hop"
        hop_dir.mkdir(parents=True)
        
        # Patch the environment
        with patch.dict('os.environ', {'WORKSPACE_ROOT': str(workspace)}):
            yield {
                'workspace': workspace,
                'ssh_dir': ssh_dir,
                'hop_dir': hop_dir,
                'json_file': ssh_dir / "credentials.json",
                'config_file': hop_dir / "config"
            }
    
    def test_no_migration_when_config_exists(self, mock_workspace):
        """Should not migrate if config file already exists."""
        # Setup: Create config file
        config_file = mock_workspace['config_file']
        config_file.write_text("# SSH Config\n")
        
        # Mock should_migrate to return False
        with patch('icpy.services.hop_service.should_migrate', return_value=False):
            with patch('icpy.services.hop_service.migrate_credentials_to_config') as mock_migrate:
                service = HopService()
                
                # Should not call migration
                mock_migrate.assert_not_called()
    
    def test_no_migration_when_no_json(self, mock_workspace):
        """Should not migrate if no JSON file exists."""
        # No JSON file created
        
        with patch('icpy.services.hop_service.should_migrate', return_value=False):
            with patch('icpy.services.hop_service.migrate_credentials_to_config') as mock_migrate:
                service = HopService()
                
                mock_migrate.assert_not_called()
    
    def test_auto_migration_on_startup(self, mock_workspace):
        """Should automatically migrate JSON to config on startup."""
        # Setup: Create JSON file without config
        json_file = mock_workspace['json_file']
        json_data = {
            "hop1": {
                "id": "hop1",
                "name": "Test Hop",
                "host": "test.example.com",
                "port": 22,
                "username": "testuser",
                "auth": "password"
            }
        }
        json_file.write_text(json.dumps(json_data))
        
        # Mock migration
        mock_result = MigrationResult(
            success=True,
            credentials_migrated=1,
            keys_renamed=0,
            message="Migration successful",
            warnings=[]
        )
        
        with patch('icpy.services.hop_service.should_migrate', return_value=True):
            with patch('icpy.services.hop_service.migrate_credentials_to_config', return_value=mock_result) as mock_migrate:
                service = HopService()
                
                # Should call migration once
                mock_migrate.assert_called_once()
    
    def test_migration_with_warnings_logged(self, mock_workspace):
        """Should log warnings from migration."""
        json_file = mock_workspace['json_file']
        json_data = {
            "hop1": {
                "id": "hop1",
                "name": "Test Hop",
                "host": "test.example.com",
                "port": 22,
                "username": "testuser",
                "auth": "privateKey",
                "privateKeyId": "missing_key"
            }
        }
        json_file.write_text(json.dumps(json_data))
        
        # Mock migration with warnings
        mock_result = MigrationResult(
            success=True,
            credentials_migrated=1,
            keys_renamed=0,
            message="Migration successful with warnings",
            warnings=["Key file for hop 'hop1' not found"]
        )
        
        with patch('icpy.services.hop_service.should_migrate', return_value=True):
            with patch('icpy.services.hop_service.migrate_credentials_to_config', return_value=mock_result):
                with patch('icpy.services.hop_service.logger') as mock_logger:
                    service = HopService()
                    
                    # Should log warning
                    warning_calls = [call for call in mock_logger.warning.call_args_list]
                    assert any("Migration warning" in str(call) for call in warning_calls)
    
    def test_migration_failure_does_not_crash(self, mock_workspace):
        """Should handle migration failure gracefully and continue startup."""
        json_file = mock_workspace['json_file']
        json_data = {
            "hop1": {
                "id": "hop1",
                "name": "Test Hop",
                "host": "test.example.com",
                "port": 22,
                "username": "testuser",
                "auth": "password"
            }
        }
        json_file.write_text(json.dumps(json_data))
        
        # Mock migration to raise exception
        with patch('icpy.services.hop_service.should_migrate', return_value=True):
            with patch('icpy.services.hop_service.migrate_credentials_to_config', side_effect=Exception("Migration error")):
                with patch('icpy.services.hop_service.logger') as mock_logger:
                    # Should not crash
                    service = HopService()
                    
                    # Should log error
                    error_calls = [call for call in mock_logger.error.call_args_list]
                    assert any("Migration failed" in str(call) for call in error_calls)
                    
                    # Service should still be usable with JSON fallback
                    assert service is not None
    
    def test_migration_result_logged(self, mock_workspace):
        """Should log migration results with counts."""
        json_file = mock_workspace['json_file']
        json_data = {
            "hop1": {
                "id": "hop1",
                "name": "Test Hop 1",
                "host": "test1.example.com",
                "port": 22,
                "username": "user1",
                "auth": "privateKey",
                "privateKeyId": "key1"
            },
            "hop2": {
                "id": "hop2",
                "name": "Test Hop 2",
                "host": "test2.example.com",
                "port": 22,
                "username": "user2",
                "auth": "password"
            }
        }
        json_file.write_text(json.dumps(json_data))
        
        # Create key file
        keys_dir = mock_workspace['ssh_dir'] / "keys"
        keys_dir.mkdir(exist_ok=True)
        (keys_dir / "key1").write_text("fake-key-content")
        
        mock_result = MigrationResult(
            success=True,
            credentials_migrated=2,
            keys_renamed=1,
            message="Migration successful",
            warnings=[]
        )
        
        with patch('icpy.services.hop_service.should_migrate', return_value=True):
            with patch('icpy.services.hop_service.migrate_credentials_to_config', return_value=mock_result):
                with patch('icpy.services.hop_service.logger') as mock_logger:
                    service = HopService()
                    
                    # Should log migration info with counts
                    info_calls = [str(call) for call in mock_logger.info.call_args_list]
                    assert any("2 credentials" in call and "1 keys renamed" in call for call in info_calls)


class TestMigrationIntegration:
    """Integration tests for migration with real HopService."""
    
    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace for integration tests."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        ssh_dir = workspace / ".icotes" / "ssh"
        ssh_dir.mkdir(parents=True)
        keys_dir = ssh_dir / "keys"
        keys_dir.mkdir(exist_ok=True)
        hop_dir = workspace / ".icotes" / "hop"
        hop_dir.mkdir(parents=True)
        
        with patch.dict('os.environ', {'WORKSPACE_ROOT': str(workspace)}):
            yield {
                'workspace': workspace,
                'ssh_dir': ssh_dir,
                'keys_dir': keys_dir,
                'hop_dir': hop_dir,
                'json_file': ssh_dir / "credentials.json",
                'config_file': hop_dir / "config"
            }
    
    def test_end_to_end_migration(self, temp_workspace):
        """Test complete migration flow from JSON to config."""
        # Create JSON credentials (list format, not dict!)
        json_file = temp_workspace['json_file']
        json_data = [
            {
                "id": "hop1",
                "name": "Production Server",
                "host": "prod.example.com",
                "port": 22,
                "username": "deploy",
                "auth": "password",
                "defaultPath": "/var/www"
            }
        ]
        json_file.write_text(json.dumps(json_data))
        
        # Initialize service (should trigger migration)
        service = HopService()
        
        # Verify config file was created
        config_file = temp_workspace['config_file']
        assert config_file.exists()
        
        # Verify backup was created
        backup_file = json_file.with_suffix('.json.bak')
        assert backup_file.exists()
        
        # Verify config content
        config_content = config_file.read_text()
        assert "Host Production Server" in config_content
        assert "HostName prod.example.com" in config_content
        assert "User deploy" in config_content
        
        # Verify credentials loaded correctly
        creds = service.list_credentials()
        assert len(creds) == 1
        assert creds[0]['name'] == "Production Server"
        assert creds[0]['host'] == "prod.example.com"
    
    def test_idempotent_migration(self, temp_workspace):
        """Test that multiple service initializations don't re-migrate."""
        # Create JSON credentials (list format, not dict!)
        json_file = temp_workspace['json_file']
        json_data = [
            {
                "id": "hop1",
                "name": "Test Server",
                "host": "test.example.com",
                "port": 22,
                "username": "testuser",
                "auth": "password"
            }
        ]
        json_file.write_text(json.dumps(json_data))
        
        # First initialization (migrates)
        service1 = HopService()
        config_file = temp_workspace['config_file']
        first_content = config_file.read_text()
        first_mtime = config_file.stat().st_mtime
        
        # Second initialization (should not re-migrate)
        import time
        time.sleep(0.01)  # Ensure different mtime if file changes
        service2 = HopService()
        second_content = config_file.read_text()
        second_mtime = config_file.stat().st_mtime
        
        # Config should not have changed
        assert first_content == second_content
        assert first_mtime == second_mtime
        
        # Both services should have same credentials
        creds1 = service1.list_credentials()
        creds2 = service2.list_credentials()
        assert len(creds1) == len(creds2) == 1
        assert creds1[0]['name'] == creds2[0]['name']
