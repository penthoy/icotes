"""
Logging utilities for secure logging with secret sanitization.

This module provides utilities to ensure sensitive data (passwords, private keys,
passphrases, tokens, etc.) never appear in logs.
"""

import re
from typing import Any, Dict, Optional


# Patterns to detect potential secrets
SECRET_PATTERNS = [
    # Double-quoted JSON style
    (re.compile(r'("password"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    (re.compile(r'("passphrase"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    (re.compile(r'("token"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    (re.compile(r'("api_key"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    (re.compile(r'("apiKey"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    (re.compile(r'("private_key"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    (re.compile(r'("privateKey"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    (re.compile(r'("secret"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    # Single-quoted repr() style (for safe_repr)
    (re.compile(r"('password'\s*:\s*')[^']*(')", re.IGNORECASE), r"\1***REDACTED***\2"),
    (re.compile(r"('passphrase'\s*:\s*')[^']*(')", re.IGNORECASE), r"\1***REDACTED***\2"),
    (re.compile(r"('token'\s*:\s*')[^']*(')", re.IGNORECASE), r"\1***REDACTED***\2"),
    (re.compile(r"('api_?key'\s*:\s*')[^']*(')", re.IGNORECASE), r"\1***REDACTED***\2"),
    (re.compile(r"('apiKey'\s*:\s*')[^']*(')", re.IGNORECASE), r"\1***REDACTED***\2"),
    (re.compile(r"('private_?key'\s*:\s*')[^']*(')", re.IGNORECASE), r"\1***REDACTED***\2"),
    (re.compile(r"('privateKey'\s*:\s*')[^']*(')", re.IGNORECASE), r"\1***REDACTED***\2"),
    (re.compile(r"('secret'\s*:\s*')[^']*(')", re.IGNORECASE), r"\1***REDACTED***\2"),
    # Query string style
    (re.compile(r'(password=)[^\s&]+', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(passphrase=)[^\s&]+', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(token=)[^\s&]+', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(api_key=)[^\s&]+', re.IGNORECASE), r'\1***REDACTED***'),
    # SSH key patterns
    (re.compile(r'-----BEGIN [A-Z ]+PRIVATE KEY-----[^-]*-----END [A-Z ]+PRIVATE KEY-----'), '***SSH_PRIVATE_KEY_REDACTED***'),
]

# Fields that should always be redacted in structured data
SECRET_FIELDS = {
    'password', 'passphrase', 'token', 'api_key', 'apikey', 'apiKey',
    'private_key', 'privatekey', 'privateKey', 'secret', 'auth_token', 'authtoken', 'authToken',
    'access_token', 'accesstoken', 'accessToken', 'refresh_token', 'refreshtoken', 'refreshToken',
}


def sanitize_string(text: str) -> str:
    """
    Sanitize a string by replacing potential secrets with placeholders.
    
    Args:
        text: String that may contain secrets
        
    Returns:
        Sanitized string with secrets replaced by placeholders
    """
    if not text:
        return text
    
    result = text
    for pattern, replacement in SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    
    return result


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize a dictionary by replacing secret values.
    
    Args:
        data: Dictionary that may contain secrets
        
    Returns:
        New dictionary with secrets replaced by placeholders
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if this field should be redacted
        if any(secret_field in key_lower for secret_field in SECRET_FIELDS):
            result[key] = '***REDACTED***'
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [sanitize_dict(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, str):
            result[key] = sanitize_string(value)
        else:
            result[key] = value
    
    return result


def sanitize_log_message(message: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Sanitize a log message and optional context dict.
    
    Args:
        message: Log message that may contain secrets
        context: Optional context dict that may contain secrets
        
    Returns:
        Sanitized log message
    """
    sanitized_msg = sanitize_string(message)
    
    if context:
        sanitized_context = sanitize_dict(context)
        sanitized_msg = f"{sanitized_msg} | Context: {sanitized_context}"
    
    return sanitized_msg


def mask_credential_value(value: Optional[str], show_prefix: int = 0, show_suffix: int = 4) -> str:
    """
    Mask a credential value, optionally showing a prefix and suffix for identification.
    
    Args:
        value: The value to mask
        show_prefix: Number of characters to show at the start
        show_suffix: Number of characters to show at the end
        
    Returns:
        Masked value like "ab***xyz" or "***" if value is None/empty
    """
    if not value:
        return '***'
    
    # If value is too short to show prefix+suffix meaningfully, just mask completely
    if len(value) <= (show_prefix + show_suffix) or len(value) < 6:
        return '***'
    
    if show_prefix > 0 and show_suffix > 0:
        return f"{value[:show_prefix]}***{value[-show_suffix:]}"
    elif show_prefix > 0:
        return f"{value[:show_prefix]}***"
    elif show_suffix > 0:
        return f"***{value[-show_suffix:]}"
    else:
        return '***'


def safe_repr(obj: Any, max_length: int = 200) -> str:
    """
    Create a safe repr of an object with secrets sanitized and length limited.
    
    Args:
        obj: Object to represent
        max_length: Maximum length of the repr string
        
    Returns:
        Safe, sanitized repr string
    """
    if isinstance(obj, dict):
        obj = sanitize_dict(obj)
    
    repr_str = repr(obj)
    sanitized = sanitize_string(repr_str)
    
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + '...(truncated)'
    
    return sanitized
