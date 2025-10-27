"""
SSH Config Parser for icotes hop configuration.

Parses OpenSSH config format with icotes-specific metadata stored in comments.
Compatible with VS Code Remote SSH configuration.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ConfigParseError(Exception):
    """Raised when SSH config parsing fails."""
    pass


@dataclass
class SSHConfigEntry:
    """Represents a single Host entry in SSH config."""
    
    # Standard SSH config fields
    host: str
    hostname: Optional[str] = None
    user: Optional[str] = None
    port: int = 22
    identity_file: Optional[str] = None
    
    # icotes-specific metadata (from comments)
    icotes_id: Optional[str] = None
    icotes_auth: Optional[str] = None
    icotes_default_path: Optional[str] = None
    icotes_created_at: Optional[str] = None
    icotes_updated_at: Optional[str] = None
    
    # Preserve comments for potential rewriting
    comments: List[str] = field(default_factory=list)
    
    def to_credential_dict(self) -> Dict:
        """Convert to dict format compatible with SSHCredential."""
        return {
            'id': self.icotes_id,
            'name': self.host,
            'host': self.hostname or self.host,
            'username': self.user or '',
            'port': self.port,
            'auth': self.icotes_auth or 'password',
            'privateKeyId': self._extract_key_id() if self.identity_file else None,
            'defaultPath': self.icotes_default_path,
            'createdAt': self.icotes_created_at,
            'updatedAt': self.icotes_updated_at,
        }
    
    def _extract_key_id(self) -> Optional[str]:
        """Extract key ID from identity file path."""
        if not self.identity_file:
            return None
        
        # Extract just the filename from the path
        # e.g., ~/.icotes/ssh/keys/hop1_key -> hop1_key
        # e.g., C:/Users/penth/icoteshop1_key -> icoteshop1_key
        import os
        return os.path.basename(self.identity_file)


def parse_ssh_config(config_text: str) -> List[SSHConfigEntry]:
    """
    Parse SSH config text into list of SSHConfigEntry objects.
    
    Args:
        config_text: SSH config file content
        
    Returns:
        List of SSHConfigEntry objects
        
    Raises:
        ConfigParseError: If config is malformed
    """
    entries: List[SSHConfigEntry] = []
    current_entry: Optional[SSHConfigEntry] = None
    pending_comments: List[str] = []
    
    lines = config_text.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        # Strip leading/trailing whitespace
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            continue
        
        # Handle comments
        if stripped.startswith('#'):
            # Check if it's icotes metadata
            if 'icotes-meta:' in stripped:
                # Store for current entry
                pending_comments.append(stripped)
            else:
                # Regular comment - preserve it
                pending_comments.append(stripped)
            continue
        
        # Split line into directive and value
        # Handle both spaces and tabs
        parts = re.split(r'\s+', stripped, 1)
        
        directive = parts[0].lower()
        value = parts[1].strip() if len(parts) > 1 else ''
        
        # Strip quotes from value
        value = value.strip('"').strip("'")
        
        # Handle Host directive
        if directive == 'host':
            # Save previous entry if exists, including any pending comments
            if current_entry:
                # Add any pending comments to the current entry before saving
                if pending_comments:
                    current_entry.comments.extend(pending_comments)
                    pending_comments.clear()
                    # Re-parse metadata in case it was added after directives
                    _parse_icotes_metadata(current_entry)
                entries.append(current_entry)
            
            # Create new entry
            current_entry = SSHConfigEntry(
                host=value,
                comments=[]  # Start with empty comments for new entry
            )
            
            # Don't parse metadata yet - wait for all comments/directives
            
        elif current_entry:
            # Parse directives within a Host block
            if directive == 'hostname':
                # Treat missing/empty values as None
                current_entry.hostname = value or None
            elif directive == 'user':
                # Treat missing/empty values as None
                current_entry.user = value or None
            elif directive == 'port':
                try:
                    current_entry.port = int(value)
                except ValueError:
                    # Keep default port if invalid
                    pass
            elif directive == 'identityfile':
                # Treat missing/empty values as None
                current_entry.identity_file = value or None
    
    # Process any remaining pending comments for the last entry
    if current_entry and pending_comments:
        current_entry.comments.extend(pending_comments)
        pending_comments.clear()
        # Re-parse metadata in case it was added after directives
        _parse_icotes_metadata(current_entry)
    
    # Don't forget the last entry
    if current_entry:
        entries.append(current_entry)
    
    return entries


def _parse_icotes_metadata(entry: SSHConfigEntry) -> None:
    """
    Extract icotes metadata from comments in an entry.
    
    Modifies entry in-place to set icotes_* fields.
    """
    for comment in entry.comments:
        if 'icotes-meta:' not in comment:
            continue
        
        # Extract JSON from comment
        # Format: # icotes-meta: {"key": "value", ...}
        match = re.search(r'icotes-meta:\s*(\{.*\})', comment)
        if not match:
            continue
        
        json_str = match.group(1)
        try:
            metadata = json.loads(json_str)
            
            # Extract fields
            entry.icotes_id = metadata.get('id')
            entry.icotes_auth = metadata.get('auth')
            entry.icotes_default_path = metadata.get('defaultPath')
            entry.icotes_created_at = metadata.get('createdAt')
            entry.icotes_updated_at = metadata.get('updatedAt')
            
            # Stop after first valid metadata
            break
            
        except json.JSONDecodeError:
            # Invalid JSON, skip this metadata
            continue
