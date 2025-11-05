"""
Hop Config Validation Tool

Validates the SSH config file at workspace/.icotes/hop/config for:
- Syntax correctness
- Required fields
- VS Code compatibility
- Common errors

Usage:
    python -m icpy.scripts.validate_hop_config
    
    Or from icotes backend directory:
    uv run python -m icpy.scripts.validate_hop_config
"""

import sys
from pathlib import Path
from typing import List, Tuple
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from icpy.utils.ssh_config_parser import parse_ssh_config, ConfigParseError


def get_config_path() -> Path:
    """Get the hop config file path."""
    workspace_root = os.environ.get('WORKSPACE_ROOT')
    if not workspace_root:
        # Try to find workspace directory
        current = Path.cwd()
        for parent in [current, *current.parents]:
            candidate = parent / 'workspace'
            if candidate.is_dir():
                workspace_root = str(candidate)
                break
    
    if not workspace_root:
        workspace_root = str(Path.cwd() / 'workspace')
    
    return Path(workspace_root) / '.icotes' / 'hop' / 'config'


def validate_config() -> Tuple[bool, List[str], List[str]]:
    """
    Validate hop config file.
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    config_path = get_config_path()
    errors: List[str] = []
    warnings: List[str] = []
    
    # Check if file exists
    if not config_path.exists():
        errors.append(f"Config file not found at {config_path}")
        return False, errors, warnings
    
    # Check file permissions
    try:
        stat_info = config_path.stat()
        mode = stat_info.st_mode & 0o777
        if mode != 0o600:
            warnings.append(
                f"Config file has permissions {oct(mode)}, should be 0600 (read/write owner only). "
                f"Run: chmod 600 {config_path}"
            )
    except Exception as e:
        warnings.append(f"Could not check file permissions: {e}")
    
    # Parse config file
    try:
        config_text = config_path.read_text(encoding='utf-8')
        
        if not config_text.strip():
            errors.append("Config file is empty")
            return False, errors, warnings
        
        entries = parse_ssh_config(config_text)
        
        if not entries:
            warnings.append("No host entries found in config")
        
        # Validate each entry
        for i, entry in enumerate(entries, 1):
            entry_id = f"Entry #{i} (Host {entry.host})"
            
            # Required fields
            if not entry.host:
                errors.append(f"{entry_id}: Missing Host directive")
            
            if not entry.hostname:
                warnings.append(f"{entry_id}: Missing HostName directive (will use Host as HostName)")
            
            if not entry.user:
                warnings.append(f"{entry_id}: Missing User directive (SSH will use current user)")
            
            # Check auth configuration
            if entry.icotes_auth:
                if entry.icotes_auth not in ['password', 'privateKey', 'agent']:
                    errors.append(
                        f"{entry_id}: Invalid auth type '{entry.icotes_auth}'. "
                        f"Must be: password, privateKey, or agent"
                    )
                
                # If privateKey auth, should have IdentityFile
                if entry.icotes_auth == 'privateKey' and not entry.identity_file:
                    errors.append(
                        f"{entry_id}: Auth type is 'privateKey' but no IdentityFile directive found"
                    )
            else:
                if entry.host != 'local':  # local doesn't need auth
                    warnings.append(
                        f"{entry_id}: No icotes-meta auth field found, will default to password"
                    )
            
            # Check if identity file exists
            if entry.identity_file:
                # Expand ~ and environment variables
                identity_path_str = entry.identity_file
                
                # Special handling for workspace-relative paths
                workspace = config_path.parent.parent.parent
                keys_dir = workspace / '.icotes' / 'ssh' / 'keys'
                
                # Check if it's a workspace-relative path like ~/.icotes/ssh/keys/...
                if identity_path_str.startswith('~/.icotes/'):
                    # This is workspace-relative, not home-relative
                    # Extract the key filename
                    key_name = Path(identity_path_str).name
                    full_path = keys_dir / key_name
                    if not full_path.exists():
                        errors.append(f"{entry_id}: Identity file not found: {full_path}")
                else:
                    # Try as absolute or home-relative path
                    identity_path = Path(identity_path_str).expanduser()
                    if identity_path.is_absolute():
                        if not identity_path.exists():
                            errors.append(f"{entry_id}: Identity file not found: {identity_path}")
                    else:
                        # Relative path - check in .icotes/ssh/keys
                        full_path = keys_dir / identity_path
                        if not full_path.exists():
                            errors.append(f"{entry_id}: Identity file not found: {full_path}")
            
            # Check port
            if entry.port and (entry.port < 1 or entry.port > 65535):
                errors.append(f"{entry_id}: Invalid port {entry.port} (must be 1-65535)")
            
            # Check for duplicate hosts
            for j, other in enumerate(entries[:i-1], 1):
                if other.host == entry.host:
                    warnings.append(
                        f"{entry_id}: Duplicate host name (first defined at entry #{j}). "
                        f"Last definition will be used."
                    )
        
        # VS Code compatibility checks
        for entry in entries:
            if entry.identity_file:
                # VS Code prefers absolute paths or ~ paths
                if not entry.identity_file.startswith('~') and not Path(entry.identity_file).is_absolute():
                    warnings.append(
                        f"Host {entry.host}: Identity file uses relative path '{entry.identity_file}'. "
                        f"Consider using absolute path or ~ for better VS Code compatibility."
                    )
        
        print(f"\n✓ Successfully parsed {len(entries)} host entries")
        
    except ConfigParseError as e:
        errors.append(f"Config parsing error: {e}")
        return False, errors, warnings
    
    except Exception as e:
        errors.append(f"Unexpected error reading config: {e}")
        return False, errors, warnings
    
    # Determine if valid
    is_valid = len(errors) == 0
    
    return is_valid, errors, warnings


def main():
    """Run validation and print results."""
    print("=" * 70)
    print("Hop Config Validation Tool")
    print("=" * 70)
    
    config_path = get_config_path()
    print(f"\nValidating: {config_path}")
    print("-" * 70)
    
    is_valid, errors, warnings = validate_config()
    
    # Print errors
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"  • {error}")
    
    # Print warnings
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  • {warning}")
    
    # Print summary
    print("\n" + "=" * 70)
    if is_valid:
        if warnings:
            print("✓ Config is VALID (with warnings)")
            print("\nYour hop config is syntactically correct and will work,")
            print("but you may want to address the warnings above.")
        else:
            print("✓ Config is VALID")
            print("\nYour hop config looks great! No issues found.")
    else:
        print("❌ Config is INVALID")
        print("\nPlease fix the errors above before using hop connections.")
        print(f"\nEdit config: code {config_path}")
    print("=" * 70)
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
