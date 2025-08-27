"""
Agent Creator - An AI agent that helps create other custom agents

This agent specializes in:
1. Creating custom agent code using file tools
2. Agent architecture design
3. Integration patterns with tool system
4. Best practices for agent development
5. Using tools to edit files and create working agents

Enhanced with tool integration capabilities for file operations.
"""

import json
import os
import logging
from typing import Dict, List, Any, AsyncGenerator

# Configure logging
logger = logging.getLogger(__name__)

# Model selection identifier for UI/router consumption
# Frontend can read this via config/status endpoints and switch helpers accordingly
AGENT_MODEL_ID = "gpt5"

# Import required modules
try:
    import sys
    backend_path = os.environ.get("ICOTES_BACKEND_PATH")
    if not backend_path:
        # Find the icotes root directory (should contain backend/ directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir and current_dir != '/':
            backend_candidate = os.path.join(current_dir, 'backend')
            if os.path.isdir(backend_candidate) and os.path.isdir(os.path.join(backend_candidate, 'icpy')):
                backend_path = backend_candidate
                break
            current_dir = os.path.dirname(current_dir)
        
        if not backend_path:
            # Fallback to relative path
            backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    
    sys.path.append(backend_path)
    
    from icpy.agent.clients import get_openai_client
    from icpy.agent.helpers import (
        create_agent_chat_function, 
        get_available_tools_summary,
        ToolDefinitionLoader,
        ToolExecutor,
        OpenAIStreamingHandler,
        create_standard_agent_metadata,
        create_environment_reload_function,
        create_agent_context,
        add_context_to_agent_prompt,
        format_agent_context_for_prompt
    )
    
    DEPENDENCIES_AVAILABLE = True
    logger.info("All dependencies available for AgentCreator")
    
    # Agent metadata using helper (after import)
    AGENT_METADATA = create_standard_agent_metadata(
        name="AgentCreator",
        description="An AI agent that helps you create other custom agents using file editing tools",
    version="2.1.1", 
        author="Hot Reload System",
    model=AGENT_MODEL_ID
    )
    
    # Individual metadata fields for backward compatibility
    MODEL_NAME = AGENT_METADATA["MODEL_NAME"]
    AGENT_NAME = AGENT_METADATA["AGENT_NAME"]
    AGENT_DESCRIPTION = AGENT_METADATA["AGENT_DESCRIPTION"] 
    AGENT_VERSION = AGENT_METADATA["AGENT_VERSION"]
    AGENT_AUTHOR = AGENT_METADATA["AGENT_AUTHOR"]
    
    # Create standardized reload function using helper
    reload_env = create_environment_reload_function([
        "icpy.agent.helpers",
        "icpy.agent.clients"
    ])
    
except ImportError as e:
    logger.warning(f"Dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False
    
    # Fallback metadata if helpers are not available
    MODEL_NAME = AGENT_MODEL_ID
    AGENT_NAME = "AgentCreator"
    AGENT_DESCRIPTION = "An AI agent that helps you create other custom agents using file editing tools"
    AGENT_VERSION = "2.1.0"
    AGENT_AUTHOR = "Hot Reload System"
    
    # Fallback reload function
    def reload_env():
        """Fallback reload function when helpers are not available"""
        global DEPENDENCIES_AVAILABLE
        DEPENDENCIES_AVAILABLE = False
        logger.info("Dependencies still not available after reload")
        return False

def get_tools():
    """
    Get available tools for AgentCreator using the helper class.
    
    Returns OpenAI function calling compatible tool definitions
    """
    if not DEPENDENCIES_AVAILABLE:
        logger.warning("Dependencies not available, returning empty tools list")
        return []
    
    try:
        loader = ToolDefinitionLoader()
        tools = loader.get_openai_tools()
        logger.info(f"Loaded {len(tools)} tools via helper")
        return tools
    except Exception as e:
        logger.warning(f"Failed to load tools via helper: {e}")
        return []


def chat(message, history):
    """
    Agent Creator streaming chat function with tool integration using helpers.
    
    This function is now much simpler thanks to the extracted helper functions.
    
    Args:
        message: str - User message
        history: List[Dict] or str (JSON) - Conversation history
        
    Yields:
        str - Response chunks for streaming
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 Dependencies not available. Please check your configuration."
        return
    
    # Enhanced system prompt with tools information and context
    base_system_prompt = f"""You are AgentCreator, an expert AI agent specialized in helping developers create custom agents for icotes using powerful file editing tools.

Your capabilities include:
- **File Operations**: Read, create, and modify files using integrated tools
- **Code Generation**: Write clean, maintainable agent code with proper structure
- **Agent Architecture**: Design robust agent systems with tool integration
- **Testing**: Create comprehensive tests following TDD principles

{get_available_tools_summary()}

You help users:
1. **Design Agent Architecture**: Plan agent structure and capabilities
2. **Write Agent Code**: Create working agents with proper tool integration
3. **Implement Tool Usage**: Show how agents can use tools effectively
4. **Create Tests**: Write comprehensive test suites using TDD approach
5. **Debug and Fix**: Analyze and fix agent code issues
6. **Follow Best Practices**: Ensure code follows icotes conventions

Agent Creation Process:
1. Analyze requirements and plan agent structure
2. Use semantic_search to understand existing patterns
3. Use read_file to examine similar agents for reference
4. Use create_file to write new agent code
5. Use replace_string_in_file for iterative improvements
6. Use run_in_terminal to test the agent

Agent behavior:
1. whenever you are going to execute a toolcall you should explain with a short sentence what you're doing before executing it.
2. If you are cut off due to token limits or streaming stops early, explicitly continue from the last sentence without repeating earlier content until the task is fully complete. Use concise chunking to finish.

Agent structure:
1. All custom agents should be created under workspace/.icotes/plugins/ where workspace is your workspace root directory.
2. Use this file (workspace/.icotes/plugins/agent_creator_agent.py) as a reference implementation; create new agents under workspace/.icotes/plugins/<AGENT_NAME>_agent.py.
3. agents should use this convention: <AGENT_NAME>_agent.py
4. after a new agent is created, you also need to add a config update to workspace/.icotes/agents.json for this agent to be properly registered with the hot reload system.
5. before you modify the agent.json, make sure you read it and understand its structure before updating it, always update with the same structure as the original.

**IMPORTANT WORKSPACE STRUCTURE**:
- Your workspace root is: <workspace_root> 
- Agent files go in: <workspace_root>/.icotes/plugins/<AGENT_NAME>_agent.py
- Configuration goes in: <workspace_root>/.icotes/agents.json
- The .icotes/plugins/ directory already exists and is the correct location for all agent files

Always provide practical, working examples and use tools when appropriate. Focus on:
- Clean, readable code with proper documentation
- Error handling and logging
- Integration with icotes agent system
- Test-driven development approach
- Tool usage best practices

When creating agents, always include:
- Proper metadata (AGENT_NAME, AGENT_DESCRIPTION, etc.)
- A `chat(message, history)` function that yields response chunks
- Optional `reload_env()` function for environment reloading
- Comprehensive error handling and logging
- Tool integration when needed

Be helpful, practical, and focus on creating working solutions."""
    
    # Add context information to the system prompt with dynamic workspace detection
    # The context helper will automatically detect the appropriate workspace root
    system_prompt = add_context_to_agent_prompt(base_system_prompt)
    
    try:
        # Use the helper function to create a chat function
        # But we need to handle it differently since we're already in the chat function
        client = get_openai_client()
        
        # Handle JSON string history (gradio compatibility)  
        if isinstance(history, str):
            history = json.loads(history)
        
        # Build conversation messages
        system_message = {"role": "system", "content": system_prompt}
        messages = [system_message] + history + [{"role": "user", "content": message}]
        
        # Create streaming handler and process
        handler = OpenAIStreamingHandler(client, MODEL_NAME)
        
        logger.info("AgentCreator: Starting chat with tools using helpers")
        # Enable auto-continue by default with sane limits (override via env)
        yield from handler.stream_chat_with_tools(messages)
        logger.info("AgentCreator: Chat completed successfully")
                
    except Exception as e:
        logger.error(f"Error in AgentCreator streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenAI API key configuration."


if __name__ == "__main__":
    # Test the chat function locally
    test_message = "Hello, AgentCreator! Can you help me create a simple agent that can read and create files?"
    test_history = []
    
    print("Testing AgentCreator with tool integration:")
    # for chunk in chat(test_message, test_history):
    #     print(chunk, end="")
    print("\n\nTest completed!") 