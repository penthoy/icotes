"""
Message Broker Implementation for icpy Backend
Provides in-memory event bus using asyncio.Queue and asyncio.Event
Supports topic-based subscription system with wildcard patterns
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import fnmatch
import weakref
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for the message broker"""
    NOTIFICATION = "notification"
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"


@dataclass
class Message:
    """Message structure for the message broker"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.NOTIFICATION
    topic: str = ""
    payload: Any = None
    timestamp: float = field(default_factory=time.time)
    sender: Optional[str] = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[float] = None  # Time to live in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            'id': self.id,
            'type': self.type.value,
            'topic': self.topic,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'sender': self.sender,
            'correlation_id': self.correlation_id,
            'reply_to': self.reply_to,
            'ttl': self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=MessageType(data.get('type', MessageType.NOTIFICATION.value)),
            topic=data.get('topic', ''),
            payload=data.get('payload'),
            timestamp=data.get('timestamp', time.time()),
            sender=data.get('sender'),
            correlation_id=data.get('correlation_id'),
            reply_to=data.get('reply_to'),
            ttl=data.get('ttl')
        )
    
    def is_expired(self) -> bool:
        """Check if message has expired based on TTL"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl


@dataclass
class Subscription:
    """Subscription information for message broker"""
    subscriber_id: str
    topic_pattern: str
    callback: Callable[[Message], None]
    handler_task: Optional[asyncio.Task] = None
    filter_func: Optional[Callable[[Message], bool]] = None
    created_at: float = field(default_factory=time.time)
    
    def matches_topic(self, topic: str) -> bool:
        """Check if topic matches subscription pattern using glob-style wildcards"""
        return fnmatch.fnmatch(topic, self.topic_pattern)


class MessageBroker:
    """
    In-memory message broker with topic-based subscription system
    Supports request/response patterns and reactive programming patterns
    """
    
    def __init__(self, max_history: int = 1000):
        self.subscribers: Dict[str, List[Subscription]] = defaultdict(list)
        self.message_history: List[Message] = []
        self.max_history = max_history
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Performance metrics
        self.stats = {
            'messages_published': 0,
            'messages_delivered': 0,
            'active_subscriptions': 0,
            'request_response_pairs': 0
        }
    
    async def start(self):
        """Start the message broker"""
        if self.running:
            return
            
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        logger.info("Message broker started")
    
    async def stop(self):
        """Stop the message broker"""
        if not self.running:
            return
            
        self.running = False
        
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all pending requests
        for future in self.pending_requests.values():
            if not future.done():
                future.cancel()
        
        self.pending_requests.clear()
        logger.info("Message broker stopped")
    
    async def publish(self, topic: str, payload: Any, message_type: MessageType = MessageType.NOTIFICATION,
                     sender: Optional[str] = None, ttl: Optional[float] = None,
                     correlation_id: Optional[str] = None, reply_to: Optional[str] = None) -> str:
        """
        Publish a message to a topic
        Returns the message ID
        """
        if not self.running:
            raise RuntimeError("Message broker is not running")
        
        message = Message(
            type=message_type,
            topic=topic,
            payload=payload,
            sender=sender,
            ttl=ttl,
            correlation_id=correlation_id,
            reply_to=reply_to
        )
        
        # Store in history
        async with self._lock:
            self.message_history.append(message)
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)
        
        # Deliver to subscribers
        delivered_count = await self._deliver_message(message)
        
        # Update stats
        self.stats['messages_published'] += 1
        self.stats['messages_delivered'] += delivered_count
        
        logger.debug(f"Published message {message.id} to topic '{topic}' - delivered to {delivered_count} subscribers")
        return message.id
    
    async def subscribe(self, topic_pattern: str, callback: Callable[[Message], None],
                       subscriber_id: Optional[str] = None, filter_func: Optional[Callable[[Message], bool]] = None) -> str:
        """
        Subscribe to messages matching a topic pattern
        Returns subscription ID
        """
        if not self.running:
            raise RuntimeError("Message broker is not running")
        
        if subscriber_id is None:
            subscriber_id = str(uuid.uuid4())
        
        subscription = Subscription(
            subscriber_id=subscriber_id,
            topic_pattern=topic_pattern,
            callback=callback,
            filter_func=filter_func
        )
        
        async with self._lock:
            self.subscribers[topic_pattern].append(subscription)
            self.stats['active_subscriptions'] += 1
        
        logger.debug(f"Subscriber {subscriber_id} subscribed to pattern '{topic_pattern}'")
        return subscriber_id
    
    async def unsubscribe(self, subscriber_id: str, topic_pattern: Optional[str] = None):
        """
        Unsubscribe from messages
        If topic_pattern is None, unsubscribe from all patterns
        """
        async with self._lock:
            if topic_pattern:
                # Unsubscribe from specific pattern
                if topic_pattern in self.subscribers:
                    self.subscribers[topic_pattern] = [
                        sub for sub in self.subscribers[topic_pattern]
                        if sub.subscriber_id != subscriber_id
                    ]
                    if not self.subscribers[topic_pattern]:
                        del self.subscribers[topic_pattern]
                    self.stats['active_subscriptions'] -= 1
            else:
                # Unsubscribe from all patterns
                removed_count = 0
                for pattern in list(self.subscribers.keys()):
                    original_count = len(self.subscribers[pattern])
                    self.subscribers[pattern] = [
                        sub for sub in self.subscribers[pattern]
                        if sub.subscriber_id != subscriber_id
                    ]
                    removed_count += original_count - len(self.subscribers[pattern])
                    if not self.subscribers[pattern]:
                        del self.subscribers[pattern]
                self.stats['active_subscriptions'] -= removed_count
        
        logger.debug(f"Unsubscribed {subscriber_id} from {topic_pattern or 'all patterns'}")
    
    async def request(self, topic: str, payload: Any, timeout: float = 30.0,
                     sender: Optional[str] = None) -> Any:
        """
        Send a request message and wait for response
        Returns the response payload
        """
        if not self.running:
            raise RuntimeError("Message broker is not running")
        
        correlation_id = str(uuid.uuid4())
        reply_to = f"_reply.{correlation_id}"
        
        # Create future for response
        response_future = asyncio.Future()
        self.pending_requests[correlation_id] = response_future
        
        # Subscribe to reply topic
        async def response_handler(message: Message):
            if message.correlation_id == correlation_id:
                if not response_future.done():
                    if message.type == MessageType.ERROR:
                        response_future.set_exception(Exception(message.payload))
                    else:
                        response_future.set_result(message.payload)
        
        reply_subscription_id = await self.subscribe(reply_to, response_handler)
        
        try:
            # Send request
            message_id = await self.publish(
                topic=topic,
                payload=payload,
                message_type=MessageType.REQUEST,
                sender=sender,
                correlation_id=correlation_id,
                reply_to=reply_to
            )
            
            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)
            self.stats['request_response_pairs'] += 1
            return response
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request to '{topic}' timed out after {timeout} seconds")
        finally:
            # Cleanup
            await self.unsubscribe(reply_subscription_id, reply_to)
            self.pending_requests.pop(correlation_id, None)
    
    async def respond(self, request_message: Message, response_payload: Any,
                     is_error: bool = False, sender: Optional[str] = None):
        """
        Send a response to a request message
        """
        if not request_message.reply_to or not request_message.correlation_id:
            raise ValueError("Cannot respond to message without reply_to or correlation_id")
        
        message_type = MessageType.ERROR if is_error else MessageType.RESPONSE
        
        await self.publish(
            topic=request_message.reply_to,
            payload=response_payload,
            message_type=message_type,
            sender=sender,
            correlation_id=request_message.correlation_id
        )
    
    async def replay_messages(self, subscriber_id: str, topic_pattern: str,
                            since_timestamp: Optional[float] = None,
                            limit: Optional[int] = None) -> List[Message]:
        """
        Replay historical messages to a subscriber
        """
        async with self._lock:
            filtered_messages = []
            
            for message in self.message_history:
                # Check timestamp filter
                if since_timestamp and message.timestamp < since_timestamp:
                    continue
                
                # Check topic pattern
                if fnmatch.fnmatch(message.topic, topic_pattern):
                    filtered_messages.append(message)
                
                # Check limit
                if limit and len(filtered_messages) >= limit:
                    break
            
            return filtered_messages
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics"""
        async with self._lock:
            return {
                **self.stats,
                'active_subscriptions': sum(len(subs) for subs in self.subscribers.values()),
                'pending_requests': len(self.pending_requests),
                'message_history_size': len(self.message_history),
                'topic_patterns': list(self.subscribers.keys())
            }
    
    async def _deliver_message(self, message: Message) -> int:
        """Deliver message to all matching subscribers"""
        if message.is_expired():
            return 0
        
        delivered_count = 0
        tasks = []
        
        async with self._lock:
            for pattern, subscriptions in self.subscribers.items():
                for subscription in subscriptions:
                    if subscription.matches_topic(message.topic):
                        # Apply filter if provided
                        if subscription.filter_func and not subscription.filter_func(message):
                            continue
                        
                        # Create task for async delivery
                        task = asyncio.create_task(self._safe_callback(subscription.callback, message))
                        tasks.append(task)
                        delivered_count += 1
        
        # Wait for all deliveries to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return delivered_count
    
    async def _safe_callback(self, callback: Callable[[Message], None], message: Message):
        """Safely execute callback with error handling"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)
        except Exception as e:
            logger.error(f"Error in message callback: {e}")
    
    async def _cleanup_expired_messages(self):
        """Periodically clean up expired messages"""
        while self.running:
            try:
                async with self._lock:
                    original_count = len(self.message_history)
                    self.message_history = [
                        msg for msg in self.message_history if not msg.is_expired()
                    ]
                    removed_count = original_count - len(self.message_history)
                    
                    if removed_count > 0:
                        logger.debug(f"Cleaned up {removed_count} expired messages")
                
                await asyncio.sleep(60)  # Cleanup every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message cleanup: {e}")
                await asyncio.sleep(10)  # Retry after 10 seconds


# Global message broker instance
_message_broker: Optional[MessageBroker] = None


async def get_message_broker() -> MessageBroker:
    """Get the global message broker instance"""
    global _message_broker
    if _message_broker is None:
        _message_broker = MessageBroker()
        await _message_broker.start()
    return _message_broker


async def shutdown_message_broker():
    """Shutdown the global message broker"""
    global _message_broker
    if _message_broker:
        await _message_broker.stop()
        _message_broker = None
