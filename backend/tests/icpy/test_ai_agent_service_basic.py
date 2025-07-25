"""
Basic integration tests for AI Agent Integration Service
Tests core AI agent functionality with simplified setup
"""

import pytest
import asyncio
import time
import uuid
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# Import the service and related classes
from icpy.services.ai_agent_service import (
    AIAgentService,
    AgentCapability,
    AgentActionType,
    AgentContext,
    AgentAction,
    AgentEvent
)
from icpy.services.code_execution_service import Language


class TestAIAgentServiceBasic:
    """Test AI Agent Integration Service core functionality"""

    @pytest.fixture
    def mock_message_broker(self):
        """Create mock message broker"""
        broker = Mock()
        broker.publish = AsyncMock()
        broker.subscribe = Mock()
        return broker

    @pytest.fixture
    def ai_agent_service(self, mock_message_broker):
        """Create AI agent service instance"""
        return AIAgentService(mock_message_broker)

    @pytest.fixture
    def sample_agent_id(self):
        """Generate sample agent ID"""
        return f"test_agent_{uuid.uuid4().hex[:8]}"

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_message_broker):
        """Test that the service initializes correctly"""
        service = AIAgentService(mock_message_broker)
        
        assert service.message_broker == mock_message_broker
        assert isinstance(service.active_agents, dict)
        assert len(service.active_agents) == 0
        assert isinstance(service.action_history, list)
        assert len(service.action_history) == 0
        assert isinstance(service.event_subscribers, dict)

    @pytest.mark.asyncio
    async def test_service_initialization_without_broker(self):
        """Test that the service can be initialized without a message broker"""
        service = AIAgentService(None)
        
        assert service.message_broker is None
        assert isinstance(service.active_agents, dict)
        assert isinstance(service.action_history, list)
        assert isinstance(service.event_subscribers, dict)

    @pytest.mark.asyncio
    async def test_agent_registration(self, ai_agent_service, sample_agent_id):
        """Test agent registration process"""
        capabilities = {AgentCapability.FILE_OPERATIONS, AgentCapability.CODE_EXECUTION}
        metadata = {"version": "1.0", "author": "test"}
        
        context = await ai_agent_service.register_agent(
            sample_agent_id,
            capabilities=capabilities,
            metadata=metadata
        )
        
        assert isinstance(context, AgentContext)
        assert context.agent_id == sample_agent_id
        assert context.capabilities == capabilities
        assert context.metadata == metadata
        assert sample_agent_id in ai_agent_service.active_agents

    @pytest.mark.asyncio
    async def test_duplicate_agent_registration(self, ai_agent_service, sample_agent_id):
        """Test that duplicate agent registration raises error"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        with pytest.raises(ValueError, match="already registered"):
            await ai_agent_service.register_agent(sample_agent_id)

    @pytest.mark.asyncio
    async def test_agent_unregistration(self, ai_agent_service, sample_agent_id):
        """Test agent unregistration process"""
        await ai_agent_service.register_agent(sample_agent_id)
        assert sample_agent_id in ai_agent_service.active_agents
        
        result = await ai_agent_service.unregister_agent(sample_agent_id)
        assert result is True
        assert sample_agent_id not in ai_agent_service.active_agents

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_agent(self, ai_agent_service):
        """Test unregistering non-existent agent returns False"""
        result = await ai_agent_service.unregister_agent("nonexistent_agent")
        assert result is False

    @pytest.mark.asyncio
    async def test_context_updates(self, ai_agent_service, sample_agent_id):
        """Test updating agent context"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        updated_context = await ai_agent_service.update_context(
            sample_agent_id,
            active_file="/test/file.py",
            cursor_position=(10, 5),
            workspace_path="/test/workspace"
        )
        
        assert updated_context.active_file == "/test/file.py"
        assert updated_context.cursor_position == (10, 5)
        assert updated_context.workspace_path == "/test/workspace"

    @pytest.mark.asyncio
    async def test_get_context(self, ai_agent_service, sample_agent_id):
        """Test retrieving agent context"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        context = await ai_agent_service.get_context(sample_agent_id)
        assert context is not None
        assert context.agent_id == sample_agent_id
        
        # Test non-existent agent
        none_context = await ai_agent_service.get_context("nonexistent")
        assert none_context is None

    @pytest.mark.asyncio
    async def test_event_subscription(self, ai_agent_service, sample_agent_id):
        """Test event subscription mechanism"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        event_types = ["fs.file_created", "terminal.output"]
        result = await ai_agent_service.subscribe_to_events(sample_agent_id, event_types)
        
        assert result is True
        for event_type in event_types:
            assert sample_agent_id in ai_agent_service.event_subscribers[event_type]

    @pytest.mark.asyncio
    async def test_event_unsubscription(self, ai_agent_service, sample_agent_id):
        """Test event unsubscription mechanism"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        event_types = ["fs.file_created", "terminal.output"]
        await ai_agent_service.subscribe_to_events(sample_agent_id, event_types)
        
        result = await ai_agent_service.unsubscribe_from_events(sample_agent_id, event_types)
        assert result is True
        
        for event_type in event_types:
            assert sample_agent_id not in ai_agent_service.event_subscribers.get(event_type, set())

    @pytest.mark.asyncio
    async def test_context_action_execution(self, ai_agent_service, sample_agent_id):
        """Test context-related action execution"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        # Test SET_ACTIVE_FILE
        action = await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.SET_ACTIVE_FILE,
            {"file_path": "/test/example.py"}
        )
        
        assert action.status == "completed"
        assert action.result["active_file"] == "/test/example.py"
        
        # Test GET_ACTIVE_FILE
        action = await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.GET_ACTIVE_FILE,
            {}
        )
        
        assert action.status == "completed"
        assert action.result["active_file"] == "/test/example.py"

    @pytest.mark.asyncio
    async def test_cursor_position_actions(self, ai_agent_service, sample_agent_id):
        """Test cursor position action execution"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        action = await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.SET_CURSOR_POSITION,
            {"line": 15, "character": 20}
        )
        
        assert action.status == "completed"
        assert action.result["cursor_position"] == [15, 20]
        
        # Verify context was updated
        context = await ai_agent_service.get_context(sample_agent_id)
        assert context.cursor_position == (15, 20)

    @pytest.mark.asyncio
    async def test_unregistered_agent_action(self, ai_agent_service):
        """Test action execution with unregistered agent"""
        with pytest.raises(ValueError, match="not registered"):
            await ai_agent_service.execute_action(
                "unregistered_agent",
                AgentActionType.GET_ACTIVE_FILE,
                {}
            )

    @pytest.mark.asyncio
    async def test_service_mock_integration(self, ai_agent_service, sample_agent_id):
        """Test action execution with mocked services"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        # Mock filesystem service
        mock_fs_service = AsyncMock()
        mock_fs_service.read_file.return_value = "file content"
        ai_agent_service._filesystem_service = mock_fs_service
        
        action = await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.READ_FILE,
            {"path": "/test/file.txt"}
        )
        
        assert action.status == "completed"
        assert action.result == "file content"
        mock_fs_service.read_file.assert_called_once_with("/test/file.txt")

    @pytest.mark.asyncio
    async def test_action_error_handling(self, ai_agent_service, sample_agent_id):
        """Test action execution error handling"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        # Mock service that raises an error
        mock_fs_service = AsyncMock()
        mock_fs_service.read_file.side_effect = Exception("File not found")
        ai_agent_service._filesystem_service = mock_fs_service
        
        action = await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.READ_FILE,
            {"path": "/nonexistent/file.txt"}
        )
        
        assert action.status == "failed"
        assert "File not found" in action.error

    @pytest.mark.asyncio
    async def test_workspace_intelligence_gathering(self, ai_agent_service, sample_agent_id):
        """Test workspace intelligence gathering"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        # Mock LSP service
        mock_lsp_service = AsyncMock()
        mock_lsp_service.get_diagnostics.return_value = [{"line": 1, "message": "Error"}]
        mock_lsp_service.get_document_symbols.return_value = [{"name": "function1"}]
        ai_agent_service._lsp_service = mock_lsp_service
        
        result = await ai_agent_service.get_workspace_intelligence(
            sample_agent_id,
            "/test/file.py",
            "all"
        )
        
        assert "diagnostics" in result
        assert "symbols" in result
        assert result["diagnostics"] == [{"line": 1, "message": "Error"}]
        assert result["symbols"] == [{"name": "function1"}]

    @pytest.mark.asyncio
    async def test_code_execution_with_context(self, ai_agent_service, sample_agent_id):
        """Test code execution with context files"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        # Mock code execution service
        mock_code_service = AsyncMock()
        mock_code_service.execute_code.return_value = {
            "status": "completed",
            "output": "Hello World"
        }
        ai_agent_service._code_execution_service = mock_code_service
        
        # Mock filesystem service for context files
        mock_fs_service = AsyncMock()
        mock_fs_service.read_file.return_value = "# Helper functions"
        ai_agent_service._filesystem_service = mock_fs_service
        
        result = await ai_agent_service.execute_code_with_context(
            sample_agent_id,
            'print("Hello World")',
            Language.PYTHON,
            context_files=["/test/helpers.py"]
        )
        
        assert result["status"] == "completed"
        assert result["output"] == "Hello World"

    @pytest.mark.asyncio
    async def test_get_active_agents_info(self, ai_agent_service):
        """Test getting active agents information"""
        # Register multiple agents
        agent1_id = f"agent1_{uuid.uuid4().hex[:8]}"
        agent2_id = f"agent2_{uuid.uuid4().hex[:8]}"
        
        await ai_agent_service.register_agent(
            agent1_id,
            capabilities={AgentCapability.FILE_OPERATIONS},
            metadata={"type": "file_agent"}
        )
        await ai_agent_service.register_agent(
            agent2_id,
            capabilities={AgentCapability.CODE_EXECUTION},
            metadata={"type": "code_agent"}
        )
        
        agents_info = await ai_agent_service.get_active_agents()
        
        assert len(agents_info) == 2
        agent_ids = [info["agent_id"] for info in agents_info]
        assert agent1_id in agent_ids
        assert agent2_id in agent_ids

    @pytest.mark.asyncio
    async def test_action_history_tracking(self, ai_agent_service, sample_agent_id):
        """Test action history tracking"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        # Execute some actions
        await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.SET_ACTIVE_FILE,
            {"file_path": "/test/file1.py"}
        )
        await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.SET_ACTIVE_FILE,
            {"file_path": "/test/file2.py"}
        )
        
        # Get all history
        history = await ai_agent_service.get_action_history()
        assert len(history) >= 2
        
        # Get history for specific agent
        agent_history = await ai_agent_service.get_action_history(sample_agent_id)
        assert len(agent_history) == 2
        assert all(action["agent_id"] == sample_agent_id for action in agent_history)

    def test_enum_and_dataclass_definitions(self):
        """Test enum and dataclass definitions"""
        # Test AgentCapability enum
        assert AgentCapability.FILE_OPERATIONS.value == "file_operations"
        assert AgentCapability.CODE_EXECUTION.value == "code_execution"
        
        # Test AgentActionType enum
        assert AgentActionType.READ_FILE.value == "read_file"
        assert AgentActionType.EXECUTE_CODE.value == "execute_code"
        
        # Test AgentContext dataclass
        context = AgentContext("test_agent")
        assert context.agent_id == "test_agent"
        assert context.active_file is None
        assert isinstance(context.capabilities, set)
        assert isinstance(context.metadata, dict)
        assert isinstance(context.created_at, float)

    @pytest.mark.asyncio
    async def test_service_lazy_initialization(self, ai_agent_service):
        """Test that services are lazily initialized"""
        # Services should start as None
        assert ai_agent_service._filesystem_service is None
        assert ai_agent_service._code_execution_service is None
        assert ai_agent_service._lsp_service is None

    @pytest.mark.asyncio
    async def test_activity_tracking(self, ai_agent_service, sample_agent_id):
        """Test that agent activity is properly tracked"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        original_activity = ai_agent_service.active_agents[sample_agent_id].last_activity
        
        # Wait a bit to ensure timestamp difference
        await asyncio.sleep(0.01)
        
        # Execute an action
        await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.SET_ACTIVE_FILE,
            {"file_path": "/test/file.py"}
        )
        
        # Check that last_activity was updated
        new_activity = ai_agent_service.active_agents[sample_agent_id].last_activity
        assert new_activity > original_activity

    @pytest.mark.asyncio
    async def test_action_storage_in_history(self, ai_agent_service, sample_agent_id):
        """Test that actions are properly stored in history"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        initial_history_length = len(ai_agent_service.action_history)
        
        action = await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.SET_ACTIVE_FILE,
            {"file_path": "/test/file.py"}
        )
        
        # Verify action was added to history
        assert len(ai_agent_service.action_history) == initial_history_length + 1
        assert ai_agent_service.action_history[-1].action_id == action.action_id

    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, ai_agent_service, sample_agent_id):
        """Test service error handling when services are unavailable"""
        await ai_agent_service.register_agent(sample_agent_id)
        
        # Ensure service is None (not initialized)
        ai_agent_service._filesystem_service = None
        
        # Execute action that requires filesystem service
        action = await ai_agent_service.execute_action(
            sample_agent_id,
            AgentActionType.READ_FILE,
            {"path": "/test/file.txt"}
        )
        
        # Action should complete but with no result since service unavailable
        assert action.status == "completed"
        assert action.result is None

    @pytest.mark.asyncio
    async def test_message_broker_integration(self, ai_agent_service, mock_message_broker):
        """Test message broker integration"""
        sample_agent_id = "test_agent"
        await ai_agent_service.register_agent(sample_agent_id)
        
        # Verify message broker was used for agent registration
        assert mock_message_broker.publish.called
        
        # Check that the publish call was made with correct structure
        call_args = mock_message_broker.publish.call_args
        assert 'topic' in call_args.kwargs
        assert 'payload' in call_args.kwargs
        assert call_args.kwargs['topic'] == 'ai_agent.agent.registered'
