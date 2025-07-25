"""
Context Manager for ICPY Agentic Workflows

This module provides memory and context management infrastructure for agents,
including session-based memory, context sharing, and vector store integration.
"""

import json
import pickle
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Set
import asyncio


@dataclass
class MemoryEntry:
    """Individual memory entry"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    memory_type: str = "episodic"  # episodic, semantic, procedural
    agent_id: str = ""
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    importance: float = 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class ContextSession:
    """Context session for agent interactions"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    session_type: str = "conversation"  # conversation, workflow, task
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    max_context_length: int = 4000
    retention_policy: str = "fifo"  # fifo, importance, recency
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SharedContext:
    """Shared context between multiple agents"""
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    participant_agents: Set[str] = field(default_factory=set)
    shared_memories: List[str] = field(default_factory=list)  # memory entry IDs
    access_rules: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class MemoryStore(ABC):
    """Abstract base class for memory storage backends"""
    
    @abstractmethod
    async def store_memory(self, memory: MemoryEntry) -> bool:
        """Store a memory entry"""
        pass
    
    @abstractmethod
    async def retrieve_memories(self, agent_id: str, session_id: Optional[str] = None,
                              memory_type: Optional[str] = None, limit: int = 100) -> List[MemoryEntry]:
        """Retrieve memories by criteria"""
        pass
    
    @abstractmethod
    async def search_memories(self, query: str, agent_id: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memories by content similarity"""
        pass
    
    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory"""
        pass
    
    @abstractmethod
    async def cleanup_expired_memories(self, cutoff_date: datetime) -> int:
        """Clean up expired memories"""
        pass


class InMemoryStore(MemoryStore):
    """In-memory implementation of memory store"""
    
    def __init__(self):
        self.memories: Dict[str, MemoryEntry] = {}
        self.agent_memories: Dict[str, List[str]] = {}  # agent_id -> memory_ids
        self.session_memories: Dict[str, List[str]] = {}  # session_id -> memory_ids
    
    async def store_memory(self, memory: MemoryEntry) -> bool:
        """Store a memory entry"""
        self.memories[memory.id] = memory
        
        # Index by agent
        if memory.agent_id not in self.agent_memories:
            self.agent_memories[memory.agent_id] = []
        self.agent_memories[memory.agent_id].append(memory.id)
        
        # Index by session
        if memory.session_id:
            if memory.session_id not in self.session_memories:
                self.session_memories[memory.session_id] = []
            self.session_memories[memory.session_id].append(memory.id)
        
        return True
    
    async def retrieve_memories(self, agent_id: str, session_id: Optional[str] = None,
                              memory_type: Optional[str] = None, limit: int = 100) -> List[MemoryEntry]:
        """Retrieve memories by criteria"""
        memory_ids = []
        
        if session_id:
            memory_ids = self.session_memories.get(session_id, [])
        else:
            memory_ids = self.agent_memories.get(agent_id, [])
        
        memories = []
        for memory_id in memory_ids:
            if memory_id in self.memories:
                memory = self.memories[memory_id]
                
                # Filter by type if specified
                if memory_type and memory.memory_type != memory_type:
                    continue
                
                memories.append(memory)
        
        # Sort by timestamp (most recent first) and limit
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        return memories[:limit]
    
    async def search_memories(self, query: str, agent_id: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memories by content similarity (simple text search)"""
        query_lower = query.lower()
        matching_memories = []
        
        memory_ids = self.agent_memories.get(agent_id, [])
        for memory_id in memory_ids:
            if memory_id in self.memories:
                memory = self.memories[memory_id]
                if query_lower in memory.content.lower():
                    matching_memories.append(memory)
        
        # Sort by importance and recency
        matching_memories.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
        return matching_memories[:limit]
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory"""
        if memory_id not in self.memories:
            return False
        
        memory = self.memories[memory_id]
        
        # Remove from indexes
        if memory.agent_id in self.agent_memories:
            self.agent_memories[memory.agent_id] = [
                mid for mid in self.agent_memories[memory.agent_id] if mid != memory_id
            ]
        
        if memory.session_id and memory.session_id in self.session_memories:
            self.session_memories[memory.session_id] = [
                mid for mid in self.session_memories[memory.session_id] if mid != memory_id
            ]
        
        del self.memories[memory_id]
        return True
    
    async def cleanup_expired_memories(self, cutoff_date: datetime) -> int:
        """Clean up expired memories"""
        expired_ids = []
        for memory_id, memory in self.memories.items():
            if memory.timestamp < cutoff_date:
                expired_ids.append(memory_id)
        
        for memory_id in expired_ids:
            await self.delete_memory(memory_id)
        
        return len(expired_ids)


class FileBasedStore(MemoryStore):
    """File-based implementation of memory store"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.memory_index: Dict[str, str] = {}  # memory_id -> file_path
        self.agent_index: Dict[str, List[str]] = {}  # agent_id -> memory_ids
        self.session_index: Dict[str, List[str]] = {}  # session_id -> memory_ids
        self._load_indexes()
    
    async def store_memory(self, memory: MemoryEntry) -> bool:
        """Store a memory entry to file"""
        try:
            # Create agent directory
            agent_dir = self.storage_path / memory.agent_id
            agent_dir.mkdir(exist_ok=True)
            
            # Save memory to file
            memory_file = agent_dir / f"{memory.id}.json"
            with open(memory_file, 'w') as f:
                json.dump({
                    'id': memory.id,
                    'content': memory.content,
                    'memory_type': memory.memory_type,
                    'agent_id': memory.agent_id,
                    'session_id': memory.session_id,
                    'timestamp': memory.timestamp.isoformat(),
                    'importance': memory.importance,
                    'access_count': memory.access_count,
                    'last_accessed': memory.last_accessed.isoformat() if memory.last_accessed else None,
                    'metadata': memory.metadata,
                    'embedding': memory.embedding
                }, f, indent=2)
            
            # Update indexes
            self.memory_index[memory.id] = str(memory_file)
            
            if memory.agent_id not in self.agent_index:
                self.agent_index[memory.agent_id] = []
            self.agent_index[memory.agent_id].append(memory.id)
            
            if memory.session_id:
                if memory.session_id not in self.session_index:
                    self.session_index[memory.session_id] = []
                self.session_index[memory.session_id].append(memory.id)
            
            self._save_indexes()
            return True
            
        except Exception as e:
            print(f"Failed to store memory {memory.id}: {e}")
            return False
    
    async def retrieve_memories(self, agent_id: str, session_id: Optional[str] = None,
                              memory_type: Optional[str] = None, limit: int = 100) -> List[MemoryEntry]:
        """Retrieve memories from files"""
        memory_ids = []
        
        if session_id:
            memory_ids = self.session_index.get(session_id, [])
        else:
            memory_ids = self.agent_index.get(agent_id, [])
        
        memories = []
        for memory_id in memory_ids:
            try:
                memory = await self._load_memory(memory_id)
                if memory and (not memory_type or memory.memory_type == memory_type):
                    memories.append(memory)
            except Exception as e:
                print(f"Failed to load memory {memory_id}: {e}")
        
        # Sort by timestamp and limit
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        return memories[:limit]
    
    async def search_memories(self, query: str, agent_id: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memories in files"""
        query_lower = query.lower()
        matching_memories = []
        
        memory_ids = self.agent_index.get(agent_id, [])
        for memory_id in memory_ids:
            try:
                memory = await self._load_memory(memory_id)
                if memory and query_lower in memory.content.lower():
                    matching_memories.append(memory)
            except Exception as e:
                print(f"Failed to search memory {memory_id}: {e}")
        
        matching_memories.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
        return matching_memories[:limit]
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory file"""
        if memory_id not in self.memory_index:
            return False
        
        try:
            # Delete file
            file_path = Path(self.memory_index[memory_id])
            file_path.unlink(missing_ok=True)
            
            # Update indexes
            del self.memory_index[memory_id]
            
            for agent_id in self.agent_index:
                self.agent_index[agent_id] = [
                    mid for mid in self.agent_index[agent_id] if mid != memory_id
                ]
            
            for session_id in self.session_index:
                self.session_index[session_id] = [
                    mid for mid in self.session_index[session_id] if mid != memory_id
                ]
            
            self._save_indexes()
            return True
            
        except Exception as e:
            print(f"Failed to delete memory {memory_id}: {e}")
            return False
    
    async def cleanup_expired_memories(self, cutoff_date: datetime) -> int:
        """Clean up expired memory files"""
        expired_count = 0
        
        for memory_id in list(self.memory_index.keys()):
            try:
                memory = await self._load_memory(memory_id)
                if memory and memory.timestamp < cutoff_date:
                    await self.delete_memory(memory_id)
                    expired_count += 1
            except Exception as e:
                print(f"Failed to check memory {memory_id} for expiration: {e}")
        
        return expired_count
    
    async def _load_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Load memory from file"""
        if memory_id not in self.memory_index:
            return None
        
        try:
            file_path = Path(self.memory_index[memory_id])
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            memory = MemoryEntry(
                id=data['id'],
                content=data['content'],
                memory_type=data['memory_type'],
                agent_id=data['agent_id'],
                session_id=data['session_id'],
                importance=data['importance'],
                access_count=data['access_count'],
                metadata=data['metadata'],
                embedding=data.get('embedding')
            )
            
            memory.timestamp = datetime.fromisoformat(data['timestamp'])
            if data.get('last_accessed'):
                memory.last_accessed = datetime.fromisoformat(data['last_accessed'])
            
            return memory
            
        except Exception as e:
            print(f"Failed to load memory {memory_id}: {e}")
            return None
    
    def _load_indexes(self):
        """Load memory indexes from file"""
        index_file = self.storage_path / "indexes.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                self.memory_index = data.get('memory_index', {})
                self.agent_index = data.get('agent_index', {})
                self.session_index = data.get('session_index', {})
            except Exception as e:
                print(f"Failed to load indexes: {e}")
    
    def _save_indexes(self):
        """Save memory indexes to file"""
        index_file = self.storage_path / "indexes.json"
        try:
            with open(index_file, 'w') as f:
                json.dump({
                    'memory_index': self.memory_index,
                    'agent_index': self.agent_index,
                    'session_index': self.session_index
                }, f, indent=2)
        except Exception as e:
            print(f"Failed to save indexes: {e}")


class ContextManager:
    """
    Context and memory manager for ICPY agents
    
    Provides session-based memory management, context sharing between agents,
    and integration with vector stores for semantic memory retrieval.
    """
    
    def __init__(self, memory_store: Optional[MemoryStore] = None, storage_path: Optional[str] = None):
        self.memory_store = memory_store or (FileBasedStore(storage_path) if storage_path else InMemoryStore())
        self.sessions: Dict[str, ContextSession] = {}
        self.shared_contexts: Dict[str, SharedContext] = {}
        self.retention_policies = {
            'fifo': self._apply_fifo_retention,
            'importance': self._apply_importance_retention,
            'recency': self._apply_recency_retention
        }
    
    async def initialize(self) -> bool:
        """Initialize the context manager"""
        try:
            # Initialize memory store if needed
            if hasattr(self.memory_store, 'initialize'):
                await self.memory_store.initialize()
            
            return True
        except Exception as e:
            print(f"Failed to initialize context manager: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the context manager"""
        try:
            # End all active sessions
            for session_id in list(self.sessions.keys()):
                await self.end_session(session_id)
            
            # Clear shared contexts
            self.shared_contexts.clear()
            
            # Shutdown memory store if needed
            if hasattr(self.memory_store, 'shutdown'):
                await self.memory_store.shutdown()
                
        except Exception as e:
            print(f"Error during context manager shutdown: {e}")
        
    async def create_session(self, agent_id: str, session_type: str = "conversation",
                           max_context_length: int = 4000, retention_policy: str = "fifo") -> str:
        """Create a new context session for an agent"""
        session = ContextSession(
            agent_id=agent_id,
            session_type=session_type,
            max_context_length=max_context_length,
            retention_policy=retention_policy
        )
        
        self.sessions[session.session_id] = session
        return session.session_id
    
    async def end_session(self, session_id: str) -> bool:
        """End a context session"""
        if session_id not in self.sessions:
            return False
        
        self.sessions[session_id].active = False
        return True
    
    async def store_memory(self, agent_id: str, content: str, memory_type: str = "episodic",
                         session_id: Optional[str] = None, importance: float = 1.0,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a memory entry"""
        memory = MemoryEntry(
            content=content,
            memory_type=memory_type,
            agent_id=agent_id,
            session_id=session_id or "",
            importance=importance,
            metadata=metadata or {}
        )
        
        await self.memory_store.store_memory(memory)
        
        # Apply retention policy if session exists
        if session_id and session_id in self.sessions:
            await self._apply_retention_policy(session_id)
        
        return memory.id
    
    async def retrieve_memories(self, agent_id: str, session_id: Optional[str] = None,
                              memory_type: Optional[str] = None, limit: int = 100) -> List[MemoryEntry]:
        """Retrieve memories for an agent"""
        memories = await self.memory_store.retrieve_memories(
            agent_id=agent_id,
            session_id=session_id,
            memory_type=memory_type,
            limit=limit
        )
        
        # Update access statistics
        for memory in memories:
            memory.access_count += 1
            memory.last_accessed = datetime.utcnow()
        
        return memories
    
    async def search_memories(self, agent_id: str, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memories by content similarity"""
        return await self.memory_store.search_memories(query, agent_id, limit)
    
    async def get_session_context(self, session_id: str, include_shared: bool = True) -> List[MemoryEntry]:
        """Get all context for a session"""
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        memories = await self.retrieve_memories(session.agent_id, session_id)
        
        # Include shared context if requested
        if include_shared:
            for context_id, shared_context in self.shared_contexts.items():
                if session.agent_id in shared_context.participant_agents:
                    shared_memories = await self._get_shared_memories(context_id)
                    memories.extend(shared_memories)
        
        return memories
    
    async def create_shared_context(self, name: str, description: str = "",
                                  participant_agents: Optional[List[str]] = None,
                                  expires_in: Optional[timedelta] = None) -> str:
        """Create a shared context between multiple agents"""
        shared_context = SharedContext(
            name=name,
            description=description,
            participant_agents=set(participant_agents or [])
        )
        
        if expires_in:
            shared_context.expires_at = datetime.utcnow() + expires_in
        
        self.shared_contexts[shared_context.context_id] = shared_context
        return shared_context.context_id
    
    async def add_agent_to_shared_context(self, context_id: str, agent_id: str) -> bool:
        """Add an agent to a shared context"""
        if context_id not in self.shared_contexts:
            return False
        
        self.shared_contexts[context_id].participant_agents.add(agent_id)
        return True
    
    async def share_memory(self, context_id: str, memory_id: str) -> bool:
        """Share a memory in a shared context"""
        if context_id not in self.shared_contexts:
            return False
        
        self.shared_contexts[context_id].shared_memories.append(memory_id)
        return True
    
    async def cleanup_expired_data(self, retention_days: int = 30) -> Dict[str, int]:
        """Clean up expired memories and contexts"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Clean up expired memories
        expired_memories = await self.memory_store.cleanup_expired_memories(cutoff_date)
        
        # Clean up expired shared contexts
        expired_contexts = 0
        for context_id in list(self.shared_contexts.keys()):
            context = self.shared_contexts[context_id]
            if context.expires_at and context.expires_at < datetime.utcnow():
                del self.shared_contexts[context_id]
                expired_contexts += 1
        
        return {
            'expired_memories': expired_memories,
            'expired_contexts': expired_contexts
        }
    
    async def get_agent_context_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get a summary of an agent's context and memory usage"""
        # Get recent memories
        recent_memories = await self.retrieve_memories(agent_id, limit=50)
        
        # Calculate statistics
        memory_types = {}
        total_importance = 0
        for memory in recent_memories:
            memory_types[memory.memory_type] = memory_types.get(memory.memory_type, 0) + 1
            total_importance += memory.importance
        
        # Get active sessions
        active_sessions = [
            session.session_id for session in self.sessions.values()
            if session.agent_id == agent_id and session.active
        ]
        
        # Get shared contexts
        shared_context_ids = [
            context_id for context_id, context in self.shared_contexts.items()
            if agent_id in context.participant_agents
        ]
        
        return {
            'agent_id': agent_id,
            'total_memories': len(recent_memories),
            'memory_types': memory_types,
            'average_importance': total_importance / len(recent_memories) if recent_memories else 0,
            'active_sessions': active_sessions,
            'shared_contexts': len(shared_context_ids),
            'last_activity': max(memory.timestamp for memory in recent_memories) if recent_memories else None
        }
    
    # Private methods
    async def _apply_retention_policy(self, session_id: str):
        """Apply retention policy to session memories"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        memories = await self.retrieve_memories(session.agent_id, session_id)
        
        if len(memories) > session.max_context_length:
            retention_func = self.retention_policies.get(session.retention_policy, self._apply_fifo_retention)
            await retention_func(session_id, memories, session.max_context_length)
    
    async def _apply_fifo_retention(self, session_id: str, memories: List[MemoryEntry], max_length: int):
        """Apply FIFO retention policy"""
        if len(memories) <= max_length:
            return
        
        # Sort by timestamp (oldest first)
        memories.sort(key=lambda m: m.timestamp)
        
        # Delete oldest memories
        memories_to_delete = memories[:len(memories) - max_length]
        for memory in memories_to_delete:
            await self.memory_store.delete_memory(memory.id)
    
    async def _apply_importance_retention(self, session_id: str, memories: List[MemoryEntry], max_length: int):
        """Apply importance-based retention policy"""
        if len(memories) <= max_length:
            return
        
        # Sort by importance (lowest first)
        memories.sort(key=lambda m: m.importance)
        
        # Delete least important memories
        memories_to_delete = memories[:len(memories) - max_length]
        for memory in memories_to_delete:
            await self.memory_store.delete_memory(memory.id)
    
    async def _apply_recency_retention(self, session_id: str, memories: List[MemoryEntry], max_length: int):
        """Apply recency-based retention policy"""
        if len(memories) <= max_length:
            return
        
        # Sort by last accessed (oldest access first)
        memories.sort(key=lambda m: m.last_accessed or m.timestamp)
        
        # Delete least recently accessed memories
        memories_to_delete = memories[:len(memories) - max_length]
        for memory in memories_to_delete:
            await self.memory_store.delete_memory(memory.id)
    
    async def _get_shared_memories(self, context_id: str) -> List[MemoryEntry]:
        """Get memories from a shared context"""
        if context_id not in self.shared_contexts:
            return []
        
        shared_context = self.shared_contexts[context_id]
        shared_memories = []
        
        for memory_id in shared_context.shared_memories:
            # This would need to be implemented based on the memory store
            # For now, we'll skip this part
            pass
        
        return shared_memories


# Global context manager instance
_context_manager: Optional[ContextManager] = None


async def get_context_manager() -> ContextManager:
    """Get the global context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
        await _context_manager.initialize()
    return _context_manager


async def shutdown_context_manager():
    """Shutdown the global context manager"""
    global _context_manager
    if _context_manager:
        await _context_manager.shutdown()
        _context_manager = None
