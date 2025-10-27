"""
Hop Config Migration Script

Migrates credentials from JSON format to SSH config format.
"""

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of migration operation."""
    success: bool
    credentials_migrated: int = 0
    keys_renamed: int = 0
    message: str = ""
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    skipped: bool = False


def should_migrate(workspace_root: Path) -> bool:
    """
    Check if migration is needed.
    
    Returns True if JSON exists and config doesn't.
    """
    workspace_root = Path(workspace_root)
    json_file = workspace_root / ".icotes" / "ssh" / "credentials.json"
    config_file = workspace_root / ".icotes" / "hop" / "config"
    
    # Migrate if JSON exists and config doesn't
    return json_file.exists() and not config_file.exists()


def migrate_credentials_to_config(workspace_root: Path) -> MigrationResult:
    """
    Migrate credentials from JSON to SSH config format.
    
    Steps:
    1. Check if migration is needed
    2. Backup original JSON
    3. Load credentials from JSON
    4. Rename key files (UUID → descriptive names)
    5. Generate config file
    6. Return result
    """
    workspace_root = Path(workspace_root)
    
    # Check if migration needed
    if not should_migrate(workspace_root):
        config_file = workspace_root / ".icotes" / "hop" / "config"
        if config_file.exists():
            return MigrationResult(
                success=True,
                skipped=True,
                message="Config file already exists, skipping migration"
            )
        else:
            return MigrationResult(
                success=True,
                skipped=True,
                message="No JSON credentials file found, nothing to migrate"
            )
    
    ssh_dir = workspace_root / ".icotes" / "ssh"
    keys_dir = ssh_dir / "keys"
    json_file = ssh_dir / "credentials.json"
    backup_file = ssh_dir / "credentials.json.bak"
    
    hop_dir = workspace_root / ".icotes" / "hop"
    hop_dir.mkdir(parents=True, exist_ok=True)
    config_file = hop_dir / "config"
    
    result = MigrationResult(success=False)
    
    try:
        # Step 1: Backup JSON file
        logger.info(f"[Migration] Creating backup: {backup_file}")
        shutil.copy(json_file, backup_file)
        
        # Step 2: Load credentials
        logger.info(f"[Migration] Loading credentials from {json_file}")
        credentials_data = json.loads(json_file.read_text(encoding="utf-8"))
        
        if not isinstance(credentials_data, list):
            raise ValueError("Credentials must be a list")
        
        result.credentials_migrated = len(credentials_data)
        
        # Step 3: Rename key files and update privateKeyId
        for cred in credentials_data:
            if cred.get("auth") == "privateKey" and cred.get("privateKeyId"):
                old_key_id = cred["privateKeyId"]
                old_key_path = keys_dir / old_key_id
                
                # Generate new key name
                cred_name = cred.get("name", cred.get("id", "unnamed"))
                new_key_name = f"{cred_name}_key"
                new_key_path = keys_dir / new_key_name
                
                # Rename key file if it exists
                if old_key_path.exists():
                    logger.info(f"[Migration] Renaming key: {old_key_id} → {new_key_name}")
                    shutil.move(str(old_key_path), str(new_key_path))
                    result.keys_renamed += 1
                    
                    # Update privateKeyId in credential
                    cred["privateKeyId"] = new_key_name
                else:
                    warning = f"Key file not found for credential '{cred_name}': {old_key_id}"
                    logger.warning(f"[Migration] {warning}")
                    result.warnings.append(warning)
                    # Keep the old key ID even though file is missing
        
        # Step 4: Generate config file
        logger.info(f"[Migration] Generating config file: {config_file}")
        config_text = _generate_config_from_credentials(credentials_data)
        
        # Write config file
        config_file.write_text(config_text, encoding="utf-8")
        
        # Set permissions (600)
        try:
            import os
            os.chmod(config_file, 0o600)
        except Exception:
            pass
        
        # Success!
        result.success = True
        result.message = f"Successfully migrated {result.credentials_migrated} credentials, renamed {result.keys_renamed} key files"
        logger.info(f"[Migration] {result.message}")
        
        return result
        
    except json.JSONDecodeError as e:
        error = f"Failed to parse JSON credentials file: {e}"
        logger.error(f"[Migration] {error}")
        result.error = error
        return result
        
    except Exception as e:
        error = f"Migration failed: {e}"
        logger.error(f"[Migration] {error}")
        result.error = error
        return result


def _generate_config_from_credentials(credentials_data: List[dict]) -> str:
    """Generate SSH config text from credentials data."""
    from icpy.utils.ssh_config_parser import SSHConfigEntry
    from icpy.utils.ssh_config_writer import generate_ssh_config
    
    entries = []
    
    for cred in credentials_data:
        # Build identity file path if privateKey auth
        identity_file = None
        if cred.get("auth") == "privateKey" and cred.get("privateKeyId"):
            identity_file = f"~/.icotes/ssh/keys/{cred['privateKeyId']}"
        
        # Create config entry
        entry = SSHConfigEntry(
            host=cred.get("name", cred.get("id", "unnamed")),
            hostname=cred.get("host", ""),
            user=cred.get("username") or None,
            port=int(cred.get("port", 22)),
            identity_file=identity_file,
            icotes_id=cred.get("id"),
            icotes_auth=cred.get("auth", "password"),
            icotes_default_path=cred.get("defaultPath"),
            icotes_created_at=cred.get("createdAt"),
            icotes_updated_at=cred.get("updatedAt"),
        )
        
        entries.append(entry)
    
    return generate_ssh_config(entries)
