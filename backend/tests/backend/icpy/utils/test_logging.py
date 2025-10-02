"""
Tests for secure logging utilities.
"""

import pytest
from icpy.utils.logging import (
    sanitize_string,
    sanitize_dict,
    sanitize_log_message,
    mask_credential_value,
    safe_repr,
)


def test_sanitize_string_password():
    """Test that passwords in strings are redacted."""
    text = '{"username": "user", "password": "secret123"}'
    result = sanitize_string(text)
    assert 'secret123' not in result
    assert '***REDACTED***' in result
    assert 'username' in result
    assert 'user' in result


def test_sanitize_string_passphrase():
    """Test that passphrases are redacted."""
    text = 'Connection with passphrase="my_secret_phrase" established'
    result = sanitize_string(text)
    assert 'my_secret_phrase' not in result
    assert '***REDACTED***' in result


def test_sanitize_string_ssh_key():
    """Test that SSH private keys are redacted."""
    text = '''-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA1234567890abcdef
-----END RSA PRIVATE KEY-----'''
    result = sanitize_string(text)
    assert '1234567890abcdef' not in result
    assert '***SSH_PRIVATE_KEY_REDACTED***' in result


def test_sanitize_dict_simple():
    """Test that password fields in dicts are redacted."""
    data = {
        'username': 'user123',
        'password': 'secret456',
        'email': 'user@example.com'
    }
    result = sanitize_dict(data)
    assert result['username'] == 'user123'
    assert result['password'] == '***REDACTED***'
    assert result['email'] == 'user@example.com'


def test_sanitize_dict_nested():
    """Test that nested secrets are redacted."""
    data = {
        'user': {
            'name': 'John',
            'credentials': {
                'password': 'secret',
                'api_key': 'key123'
            }
        },
        'public_data': 'visible'
    }
    result = sanitize_dict(data)
    assert result['user']['name'] == 'John'
    assert result['user']['credentials']['password'] == '***REDACTED***'
    assert result['user']['credentials']['api_key'] == '***REDACTED***'
    assert result['public_data'] == 'visible'


def test_sanitize_dict_with_lists():
    """Test that lists containing dicts are sanitized."""
    data = {
        'credentials': [
            {'name': 'cred1', 'password': 'pass1'},
            {'name': 'cred2', 'token': 'token123'}
        ]
    }
    result = sanitize_dict(data)
    assert result['credentials'][0]['name'] == 'cred1'
    assert result['credentials'][0]['password'] == '***REDACTED***'
    assert result['credentials'][1]['token'] == '***REDACTED***'


def test_sanitize_log_message_with_context():
    """Test log message sanitization with context."""
    message = "User login attempt"
    context = {
        'username': 'john',
        'password': 'secret123',
        'ip': '192.168.1.1'
    }
    result = sanitize_log_message(message, context)
    assert 'User login attempt' in result
    assert 'john' in result
    assert 'secret123' not in result
    assert '***REDACTED***' in result
    assert '192.168.1.1' in result


def test_mask_credential_value():
    """Test credential masking."""
    # Full mask
    assert mask_credential_value(None) == '***'
    assert mask_credential_value('') == '***'
    assert mask_credential_value('short') == '***'
    
    # With prefix and suffix
    long_value = 'abcdefghijklmnop'
    result = mask_credential_value(long_value, show_prefix=2, show_suffix=4)
    assert result == 'ab***mnop'
    assert 'cdefghijkl' not in result
    
    # Only prefix
    result = mask_credential_value(long_value, show_prefix=3, show_suffix=0)
    assert result == 'abc***'
    
    # Only suffix
    result = mask_credential_value(long_value, show_prefix=0, show_suffix=3)
    assert result == '***nop'


def test_safe_repr():
    """Test safe representation with length limiting."""
    data = {
        'password': 'secret',
        'data': 'value'
    }
    result = safe_repr(data, max_length=50)
    assert 'secret' not in result
    assert '***REDACTED***' in result
    assert len(result) <= 70  # 50 + some for truncation message


def test_case_insensitive_field_matching():
    """Test that field matching is case-insensitive."""
    data = {
        'Password': 'secret1',
        'PASSWORD': 'secret2',
        'PaSsWoRd': 'secret3',
        'apiKey': 'key1',
        'API_KEY': 'key2',
    }
    result = sanitize_dict(data)
    assert result['Password'] == '***REDACTED***'
    assert result['PASSWORD'] == '***REDACTED***'
    assert result['PaSsWoRd'] == '***REDACTED***'
    assert result['apiKey'] == '***REDACTED***'
    assert result['API_KEY'] == '***REDACTED***'


def test_multiple_secrets_in_string():
    """Test handling multiple secrets in one string."""
    text = 'Auth with password="pass1" and token="tok123" via api_key="key456"'
    result = sanitize_string(text)
    assert 'pass1' not in result
    assert 'tok123' not in result
    assert 'key456' not in result
    assert result.count('***REDACTED***') == 3
