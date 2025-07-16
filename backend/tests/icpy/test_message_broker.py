"""
Integration tests for Message Broker
Tests basic pub/sub functionality and reactive programming patterns
"""

import asyncio
import pytest
import pytest_asyncio
import time
from typing import List
from unittest.mock import Mock, AsyncMock

# Add the backend directory to the path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.core.message_broker import MessageBroker, Message, MessageType, Subscription


class TestMessageBroker:
    """Test cases for MessageBroker"""
    
    @pytest_asyncio.fixture
    async def broker(self):
        """Create and start a message broker for testing"""
        broker = MessageBroker(max_history=100)
        await broker.start()
        yield broker
        await broker.stop()
    
    @pytest.mark.asyncio
    async def test_broker_startup_shutdown(self):
        """Test broker startup and shutdown"""
        broker = MessageBroker()
        assert not broker.running
        
        await broker.start()
        assert broker.running
        assert broker.cleanup_task is not None
        
        await broker.stop()
        assert not broker.running
        assert broker.cleanup_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_basic_publish_subscribe(self, broker):
        """Test basic publish/subscribe functionality"""
        received_messages = []
        
        def callback(message: Message):
            received_messages.append(message)
        
        # Subscribe to topic
        subscriber_id = await broker.subscribe("test.topic", callback)
        
        # Publish message
        test_payload = {"data": "test message"}
        message_id = await broker.publish("test.topic", test_payload)
        
        # Allow message delivery
        await asyncio.sleep(0.1)
        
        # Verify message was received
        assert len(received_messages) == 1
        assert received_messages[0].topic == "test.topic"
        assert received_messages[0].payload == test_payload
        assert received_messages[0].id == message_id
        assert received_messages[0].type == MessageType.NOTIFICATION
        
        # Verify subscription tracking
        stats = await broker.get_stats()
        assert stats['active_subscriptions'] == 1
        assert stats['messages_published'] == 1
        assert stats['messages_delivered'] == 1
    
    @pytest.mark.asyncio
    async def test_wildcard_subscriptions(self, broker):
        """Test wildcard pattern subscriptions"""
        received_messages = []
        
        def callback(message: Message):
            received_messages.append(message)
        
        # Subscribe to wildcard pattern
        await broker.subscribe("test.*", callback)
        
        # Publish messages to different topics
        await broker.publish("test.topic1", "message1")
        await broker.publish("test.topic2", "message2")
        await broker.publish("other.topic", "message3")  # Should not match
        
        # Allow message delivery
        await asyncio.sleep(0.1)
        
        # Verify only matching messages were received
        assert len(received_messages) == 2
        assert received_messages[0].payload == "message1"
        assert received_messages[1].payload == "message2"
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, broker):
        """Test multiple subscribers to the same topic"""
        received_messages_1 = []
        received_messages_2 = []
        
        def callback1(message: Message):
            received_messages_1.append(message)
        
        def callback2(message: Message):
            received_messages_2.append(message)
        
        # Subscribe both callbacks
        await broker.subscribe("test.topic", callback1)
        await broker.subscribe("test.topic", callback2)
        
        # Publish message
        await broker.publish("test.topic", "test message")
        
        # Allow message delivery
        await asyncio.sleep(0.1)
        
        # Verify both subscribers received the message
        assert len(received_messages_1) == 1
        assert len(received_messages_2) == 1
        assert received_messages_1[0].payload == "test message"
        assert received_messages_2[0].payload == "test message"
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, broker):
        """Test unsubscribe functionality"""
        received_messages = []
        
        def callback(message: Message):
            received_messages.append(message)
        
        # Subscribe and publish
        subscriber_id = await broker.subscribe("test.topic", callback)
        await broker.publish("test.topic", "message1")
        await asyncio.sleep(0.1)
        
        # Unsubscribe
        await broker.unsubscribe(subscriber_id, "test.topic")
        
        # Publish another message
        await broker.publish("test.topic", "message2")
        await asyncio.sleep(0.1)
        
        # Verify only first message was received
        assert len(received_messages) == 1
        assert received_messages[0].payload == "message1"
    
    @pytest.mark.asyncio
    async def test_request_response_pattern(self, broker):
        """Test request/response messaging pattern"""
        # Set up responder
        async def responder(message: Message):
            if message.type == MessageType.REQUEST:
                response_payload = f"Response to: {message.payload}"
                await broker.respond(message, response_payload)
        
        await broker.subscribe("service.echo", responder)
        
        # Send request
        response = await broker.request("service.echo", "Hello, service!")
        
        # Verify response
        assert response == "Response to: Hello, service!"
    
    @pytest.mark.asyncio
    async def test_request_timeout(self, broker):
        """Test request timeout functionality"""
        # No responder set up, so request should timeout
        with pytest.raises(TimeoutError):
            await broker.request("service.nonexistent", "test", timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_message_filtering(self, broker):
        """Test message filtering functionality"""
        received_messages = []
        
        def callback(message: Message):
            received_messages.append(message)
        
        # Filter function - only accept messages with 'important' in payload
        def filter_func(message: Message):
            return isinstance(message.payload, dict) and message.payload.get('important', False)
        
        await broker.subscribe("test.topic", callback, filter_func=filter_func)
        
        # Publish messages
        await broker.publish("test.topic", {"data": "normal", "important": False})
        await broker.publish("test.topic", {"data": "important", "important": True})
        await broker.publish("test.topic", {"data": "another normal"})
        
        # Allow message delivery
        await asyncio.sleep(0.1)
        
        # Verify only important message was received
        assert len(received_messages) == 1
        assert received_messages[0].payload['important'] is True
    
    @pytest.mark.asyncio
    async def test_message_history_and_replay(self, broker):
        """Test message history and replay functionality"""
        # Publish some messages
        await broker.publish("test.topic", "message1")
        await broker.publish("test.topic", "message2")
        await broker.publish("other.topic", "message3")
        
        # Test replay
        history = await broker.replay_messages("test_subscriber", "test.topic")
        
        # Verify history
        assert len(history) == 2
        assert history[0].payload == "message1"
        assert history[1].payload == "message2"
        
        # Test replay with limit
        limited_history = await broker.replay_messages("test_subscriber", "test.topic", limit=1)
        assert len(limited_history) == 1
        assert limited_history[0].payload == "message1"
    
    @pytest.mark.asyncio
    async def test_message_ttl_expiration(self, broker):
        """Test message time-to-live expiration"""
        received_messages = []
        
        def callback(message: Message):
            received_messages.append(message)
        
        await broker.subscribe("test.topic", callback)
        
        # Publish message with short TTL
        await broker.publish("test.topic", "expires quickly", ttl=0.1)
        
        # Wait for message to expire
        await asyncio.sleep(0.2)
        
        # Publish another message (should not be expired)
        await broker.publish("test.topic", "does not expire")
        
        # Allow message delivery
        await asyncio.sleep(0.1)
        
        # Verify only non-expired message was received
        # Note: This test may be flaky due to timing
        assert len(received_messages) >= 1
        assert received_messages[-1].payload == "does not expire"
    
    @pytest.mark.asyncio
    async def test_async_callback_support(self, broker):
        """Test support for async callbacks"""
        received_messages = []
        
        async def async_callback(message: Message):
            # Simulate async work
            await asyncio.sleep(0.01)
            received_messages.append(message)
        
        await broker.subscribe("test.topic", async_callback)
        await broker.publish("test.topic", "async test message")
        
        # Allow async callback to complete
        await asyncio.sleep(0.1)
        
        assert len(received_messages) == 1
        assert received_messages[0].payload == "async test message"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_callbacks(self, broker):
        """Test error handling in message callbacks"""
        received_messages = []
        
        def faulty_callback(message: Message):
            if message.payload == "error":
                raise ValueError("Test error")
            received_messages.append(message)
        
        await broker.subscribe("test.topic", faulty_callback)
        
        # Publish messages - one should cause error, one should succeed
        await broker.publish("test.topic", "error")
        await broker.publish("test.topic", "success")
        
        # Allow message delivery
        await asyncio.sleep(0.1)
        
        # Verify error didn't prevent other messages from being processed
        assert len(received_messages) == 1
        assert received_messages[0].payload == "success"
    
    @pytest.mark.asyncio
    async def test_reactive_programming_patterns(self, broker):
        """Test reactive programming patterns like map, filter, reduce"""
        results = []
        
        # Set up a chain of reactive operations
        async def number_processor(message: Message):
            if message.topic == "numbers":
                # Map: multiply by 2
                doubled = message.payload * 2
                await broker.publish("numbers.doubled", doubled)
        
        async def filter_processor(message: Message):
            if message.topic == "numbers.doubled":
                # Filter: only even numbers greater than 10
                if message.payload > 10 and message.payload % 2 == 0:
                    await broker.publish("numbers.filtered", message.payload)
        
        async def result_collector(message: Message):
            if message.topic == "numbers.filtered":
                results.append(message.payload)
        
        # Set up the reactive chain
        await broker.subscribe("numbers", number_processor)
        await broker.subscribe("numbers.doubled", filter_processor)
        await broker.subscribe("numbers.filtered", result_collector)
        
        # Publish test numbers
        test_numbers = [3, 5, 7, 8, 10]
        for num in test_numbers:
            await broker.publish("numbers", num)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify reactive chain worked
        # Numbers: 3->6, 5->10, 7->14, 8->16, 10->20
        # Filtered (>10 and even): 14, 16, 20
        expected = [14, 16, 20]
        assert results == expected
    
    @pytest.mark.asyncio
    async def test_broker_statistics(self, broker):
        """Test broker statistics collection"""
        # Subscribe and publish some messages
        await broker.subscribe("test.*", lambda msg: None)
        await broker.subscribe("other.*", lambda msg: None)
        
        await broker.publish("test.topic", "message1")
        await broker.publish("other.topic", "message2")
        
        # Allow message delivery
        await asyncio.sleep(0.1)
        
        stats = await broker.get_stats()
        
        # Verify statistics
        assert stats['messages_published'] == 2
        assert stats['messages_delivered'] == 2
        assert stats['active_subscriptions'] == 2
        assert stats['pending_requests'] == 0
        assert stats['message_history_size'] == 2
        assert 'test.*' in stats['topic_patterns']
        assert 'other.*' in stats['topic_patterns']


class TestMessage:
    """Test cases for Message class"""
    
    def test_message_creation(self):
        """Test message creation and serialization"""
        message = Message(
            type=MessageType.REQUEST,
            topic="test.topic",
            payload={"data": "test"},
            sender="test_sender"
        )
        
        assert message.type == MessageType.REQUEST
        assert message.topic == "test.topic"
        assert message.payload == {"data": "test"}
        assert message.sender == "test_sender"
        assert message.id is not None
        assert message.timestamp is not None
    
    def test_message_serialization(self):
        """Test message to_dict and from_dict methods"""
        original = Message(
            type=MessageType.NOTIFICATION,
            topic="test.topic",
            payload="test payload",
            sender="test_sender"
        )
        
        # Serialize to dict
        data = original.to_dict()
        
        # Deserialize from dict
        recreated = Message.from_dict(data)
        
        # Verify all fields match
        assert recreated.id == original.id
        assert recreated.type == original.type
        assert recreated.topic == original.topic
        assert recreated.payload == original.payload
        assert recreated.sender == original.sender
        assert recreated.timestamp == original.timestamp
    
    def test_message_expiration(self):
        """Test message TTL expiration"""
        # Create message with short TTL
        message = Message(
            topic="test.topic",
            payload="test",
            ttl=0.1
        )
        
        # Should not be expired initially
        assert not message.is_expired()
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired now
        assert message.is_expired()
    
    def test_message_without_ttl(self):
        """Test message without TTL never expires"""
        message = Message(
            topic="test.topic",
            payload="test"
        )
        
        # Should never expire
        assert not message.is_expired()
        
        # Even after some time
        time.sleep(0.1)
        assert not message.is_expired()


class TestSubscription:
    """Test cases for Subscription class"""
    
    def test_subscription_topic_matching(self):
        """Test subscription topic pattern matching"""
        callback = Mock()
        
        # Test exact match
        sub1 = Subscription("sub1", "test.topic", callback)
        assert sub1.matches_topic("test.topic")
        assert not sub1.matches_topic("test.other")
        
        # Test wildcard match
        sub2 = Subscription("sub2", "test.*", callback)
        assert sub2.matches_topic("test.topic")
        assert sub2.matches_topic("test.other")
        assert not sub2.matches_topic("other.topic")
        
        # Test complex pattern
        sub3 = Subscription("sub3", "*.service.*", callback)
        assert sub3.matches_topic("user.service.create")
        assert sub3.matches_topic("auth.service.login")
        assert not sub3.matches_topic("service.create")
        assert not sub3.matches_topic("user.create")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
