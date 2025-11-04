"""
Tests for vendor_parts serialization and thought signature support.

Phase 6: Unit tests for Gemini thought signature integration.
"""

import json
import pytest
from datetime import datetime, timezone
from icpy.services.chat_service import ChatMessage, MessageSender, ChatMessageType


class TestVendorPartsSerialization:
    """Test vendor_parts field serialization and deserialization."""
    
    def test_message_without_vendor_parts(self):
        """Test backward compatibility - messages without vendor_parts."""
        msg = ChatMessage(
            id="msg_1",
            content="Hello",
            sender=MessageSender.USER,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        # Serialize
        msg_dict = msg.to_dict()
        assert 'vendor_parts' not in msg_dict
        assert 'vendor_model' not in msg_dict
        
        # Deserialize
        restored = ChatMessage.from_dict(msg_dict)
        assert restored.vendor_parts is None
        assert restored.vendor_model is None
    
    def test_message_with_vendor_parts(self):
        """Test messages with vendor_parts are preserved."""
        vendor_parts = [
            {'delta': {'content': 'Hello'}, 'index': 0, 'finish_reason': None},
            {'delta': {'thought_signature': 'abc123=='}, 'index': 1, 'finish_reason': None},
        ]
        
        msg = ChatMessage(
            id="msg_2",
            content="Hello from Gemini",
            sender=MessageSender.AI,
            timestamp=datetime.now(timezone.utc).isoformat(),
            vendor_parts=vendor_parts,
            vendor_model="gemini-2.5-pro"
        )
        
        # Serialize
        msg_dict = msg.to_dict()
        assert 'vendor_parts' in msg_dict
        assert 'vendor_model' in msg_dict
        assert msg_dict['vendor_parts'] == vendor_parts
        assert msg_dict['vendor_model'] == "gemini-2.5-pro"
        
        # Deserialize
        restored = ChatMessage.from_dict(msg_dict)
        assert restored.vendor_parts == vendor_parts
        assert restored.vendor_model == "gemini-2.5-pro"
        assert restored.content == "Hello from Gemini"
    
    def test_json_roundtrip(self):
        """Test JSON serialization roundtrip with vendor_parts."""
        vendor_parts = [
            {'delta': {'tool_calls': [{'id': 'call_1', 'function': {'name': 'test'}}]}, 'index': 0},
        ]
        
        msg = ChatMessage(
            id="msg_3",
            content="Tool call response",
            sender=MessageSender.AI,
            timestamp=datetime.now(timezone.utc).isoformat(),
            vendor_parts=vendor_parts,
            vendor_model="gemini-2.5-flash"
        )
        
        # Serialize to JSON string
        json_str = json.dumps(msg.to_dict())
        
        # Deserialize from JSON string
        msg_dict = json.loads(json_str)
        restored = ChatMessage.from_dict(msg_dict)
        
        assert restored.vendor_parts == vendor_parts
        assert restored.vendor_model == "gemini-2.5-flash"
        assert restored.content == "Tool call response"
    
    def test_loading_legacy_message_without_vendor_fields(self):
        """Test loading messages from old JSONL files without vendor fields."""
        # Simulate legacy message format
        legacy_dict = {
            'id': 'msg_old',
            'content': 'Legacy message',
            'sender': 'ai',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'message',
            'metadata': {},
            'agent_id': None,
            'session_id': 'session_1',
            'attachments': []
        }
        
        # Should load without error
        msg = ChatMessage.from_dict(legacy_dict)
        assert msg.vendor_parts is None
        assert msg.vendor_model is None
        assert msg.content == 'Legacy message'


class TestVendorMetadataContext:
    """Test vendor metadata context variable functionality."""
    
    def test_set_and_get_vendor_metadata(self):
        """Test setting and getting vendor metadata."""
        from icpy.agent.helpers import set_vendor_metadata, get_vendor_metadata, clear_vendor_metadata
        
        # Initially should be None
        clear_vendor_metadata()
        assert get_vendor_metadata() is None
        
        # Set metadata
        vendor_parts = [{'delta': {'content': 'test'}}]
        set_vendor_metadata(vendor_parts, "gemini-2.5-pro")
        
        # Get metadata
        metadata = get_vendor_metadata()
        assert metadata is not None
        assert metadata['vendor_parts'] == vendor_parts
        assert metadata['vendor_model'] == "gemini-2.5-pro"
        
        # Clear metadata
        clear_vendor_metadata()
        assert get_vendor_metadata() is None
    
    def test_set_empty_vendor_metadata(self):
        """Test setting empty vendor metadata clears it."""
        from icpy.agent.helpers import set_vendor_metadata, get_vendor_metadata
        
        # Set and then clear with empty
        set_vendor_metadata([{'test': 'data'}], "model")
        assert get_vendor_metadata() is not None
        
        set_vendor_metadata(None, None)
        assert get_vendor_metadata() is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
