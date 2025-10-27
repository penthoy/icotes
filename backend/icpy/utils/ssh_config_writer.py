"""
SSH Config Writer for icotes hop configuration.

Generates OpenSSH config format with icotes-specific metadata embedded in comments.
"""

import json
from pathlib import Path
from typing import List, Any, Dict
from icpy.utils.ssh_config_parser import SSHConfigEntry


def generate_ssh_config(entries: List[SSHConfigEntry]) -> str:
    """
    Generate SSH config text from list of SSHConfigEntry objects.
    
    Args:
        entries: List of SSHConfigEntry objects
        
    Returns:
        SSH config file content as string
    """
    lines = []
    
    # Add header
    lines.append("# icotes hop configuration")
    lines.append("# This file is compatible with VS Code Remote SSH config")
    lines.append("")
    
    # Generate each entry
    for i, entry in enumerate(entries):
        if i > 0:
            # Blank line between entries
            lines.append("")
        
        lines.extend(_generate_entry_lines(entry))
    
    return '\n'.join(lines)


def _generate_entry_lines(entry: SSHConfigEntry) -> List[str]:
    """Generate lines for a single SSH config entry."""
    lines = []
    
    # Host directive
    lines.append(f"Host {entry.host}")
    
    # Standard directives in order
    if entry.hostname:
        lines.append(f"    HostName {entry.hostname}")
    
    if entry.user:
        lines.append(f"    User {entry.user}")
    
    if entry.port and entry.port != 22:
        lines.append(f"    Port {entry.port}")
    elif entry.port == 22:
        # Include default port for clarity
        lines.append(f"    Port {entry.port}")
    
    if entry.identity_file:
        lines.append(f"    IdentityFile {entry.identity_file}")
    
    # Add icotes metadata if present
    metadata = _build_metadata_dict(entry)
    if metadata:
        metadata_json = json.dumps(metadata, separators=(', ', ': '))
        lines.append(f"    # icotes-meta: {metadata_json}")
    
    return lines


def _build_metadata_dict(entry: SSHConfigEntry) -> dict:
    """Build icotes metadata dictionary from entry."""
    metadata = {}
    
    if entry.icotes_id:
        metadata['id'] = entry.icotes_id
    if entry.icotes_auth:
        metadata['auth'] = entry.icotes_auth
    if entry.icotes_default_path:
        metadata['defaultPath'] = entry.icotes_default_path
    if entry.icotes_created_at:
        metadata['createdAt'] = entry.icotes_created_at
    if entry.icotes_updated_at:
        metadata['updatedAt'] = entry.icotes_updated_at
    
    return metadata


def credential_to_config_entry(cred: Any) -> SSHConfigEntry:
    """
    Convert SSHCredential-like object to SSHConfigEntry for writing to config.
    
    Args:
        cred: Object with credential attributes (name, host, username, port, etc.)
        
    Returns:
        SSHConfigEntry object
    """
    # Determine identity file path if privateKey auth
    identity_file = None
    auth = getattr(cred, 'auth', 'password')
    private_key_id = getattr(cred, 'privateKeyId', None)
    
    if auth == "privateKey" and private_key_id:
        # Build path to key file
        # For now, use relative path from workspace root
        identity_file = f"~/.icotes/ssh/keys/{private_key_id}"
    
    return SSHConfigEntry(
        host=getattr(cred, 'name', ''),
        hostname=getattr(cred, 'host', ''),
        user=getattr(cred, 'username', None) or None,
        port=getattr(cred, 'port', 22),
        identity_file=identity_file,
        icotes_id=getattr(cred, 'id', None),
        icotes_auth=auth,
        icotes_default_path=getattr(cred, 'defaultPath', None),
        icotes_created_at=getattr(cred, 'createdAt', None),
        icotes_updated_at=getattr(cred, 'updatedAt', None),
    )
