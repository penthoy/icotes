"""
OpenRouter Agent Creator - An AI agent that helps create other custom agents (OpenRouter)

This agent mirrors AgentCreator but uses OpenRouter for reasoning
and tool-use streaming.

Capabilities:
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
# Configure logging
logger = logging.getLogger(__name__)

# Model selection identifier for UI/router consumption
# Update to your preferred OpenRouter model if needed
AGENT_MODEL_ID = "qwen/qwen3-coder"

# Import required modules and backend helpers
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
            # Fallback to relative path from workspace/.icotes/plugins/
            backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))
    
    sys.path.append(backend_path)

    # Import OpenRouter client and streaming handler + shared helpers
    from icpy.agent.clients import get_openrouter_client
    from icpy.agent.helpers import (
        create_standard_agent_metadata,
        create_environment_reload_function,
        get_available_tools_summary,
        ToolDefinitionLoader,
        OpenAIStreamingHandler,
        add_context_to_agent_prompt,
    )

    DEPENDENCIES_AVAILABLE = True
    logger.info("All dependencies available for OpenRouterAgentCreator")

    # Agent metadata using helper (after import)
    AGENT_METADATA = create_standard_agent_metadata(
        name="OpenRouterAgentCreator",
        description="An AI agent (OpenRouter) that helps you create other custom agents using file editing tools",
        version="1.0.0",
        author="Hot Reload System",
        model=AGENT_MODEL_ID,
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
        "icpy.agent.clients",
    ])

except ImportError as e:
    logger.warning(f"Dependencies not available for OpenRouterAgentCreator: {e}")
    DEPENDENCIES_AVAILABLE = False

    # Fallback metadata if helpers are not available
    MODEL_NAME = AGENT_MODEL_ID
    AGENT_NAME = "OpenRouterAgentCreator"
    AGENT_DESCRIPTION = "An AI agent (OpenRouter) that helps you create other custom agents using file editing tools"
    AGENT_VERSION = "1.0.0"
    AGENT_AUTHOR = "Hot Reload System"

    # Fallback reload function
    def reload_env():
        global DEPENDENCIES_AVAILABLE
        DEPENDENCIES_AVAILABLE = False
        logger.info("Dependencies still not available after reload")
        return False

    # Fallback metadata object with standard keys
    AGENT_METADATA = {
        "AGENT_NAME": AGENT_NAME,
        "AGENT_DESCRIPTION": AGENT_DESCRIPTION,
        "AGENT_VERSION": AGENT_VERSION,
        "AGENT_AUTHOR": AGENT_AUTHOR,
        "MODEL_NAME": MODEL_NAME,
        "AGENT_MODEL_ID": AGENT_MODEL_ID,
        "status": "error",
        "error": f"Dependencies not available: {e}",
    }


def get_tools():
    """
    Get available tools for OpenRouterAgentCreator using the helper class.

    Returns OpenAI-compatible tool definitions for OpenRouter.
    """
    if not DEPENDENCIES_AVAILABLE:
        logger.warning("Dependencies not available, returning empty tools list")
        return []

    try:
        loader = ToolDefinitionLoader()
        # Use OpenAI tool schema for OpenRouter compatibility
        if hasattr(loader, "get_openai_tools"):
            tools = loader.get_openai_tools()
            logger.info(f"Loaded {len(tools)} tools via helper")
            return tools
        logger.warning("ToolDefinitionLoader has no compatible export; returning empty list")
        return []
    except Exception as e:
        logger.warning(f"Failed to load tools via helper: {e}")
        return []


def chat(message, history):
    """
    OpenRouter Agent Creator streaming chat function with tool integration using helpers.

    Args:
        message: str - User message
        history: List[Dict] or str (JSON) - Conversation history

    Yields:
        str - Response chunks for streaming
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 Dependencies not available for OpenRouterAgentCreator. Please check your OpenRouter configuration."
        return

    # Enhanced system prompt with tools information and context
    base_system_prompt = f"""You are OpenRouterAgentCreator, an expert AI agent specialized in helping developers create custom agents for icotes using powerful file editing tools.

Your capabilities include:
- File Operations: Read, create, and modify files using integrated tools
- Code Generation: Write clean, maintainable agent code with proper structure
- Agent Architecture: Design robust agent systems with tool integration
- Testing: Create comprehensive tests following TDD principles

{get_available_tools_summary()}

You help users:
1. Design Agent Architecture: Plan agent structure and capabilities
2. Write Agent Code: Create working agents with proper tool integration
3. Implement Tool Usage: Show how agents can use tools effectively
4. Create Tests: Write comprehensive test suites using TDD approach
5. Debug and Fix: Analyze and fix agent code issues
6. Follow Best Practices: Ensure code follows icotes conventions

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
2. all your code is under workspace/.icotes/plugins/openrouter_agent_creator_agent.py you can use this as implementation reference. when I refer to you or your code, this is the file I am refering to.
3. agents should use this convention: <AGENT_NAME>_agent.py
4. after a new agent is created, you also need to add a config update to workspace/.icotes/agents.json for this agent to be properly registered with the hot reload system.
5. before you modify the agent.json, make sure you read it and understand its structure before updating it, always update with the same structure as the original.

IMPORTANT WORKSPACE STRUCTURE:
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
    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        # Initialize OpenRouter client
        client = get_openrouter_client()

        # Handle JSON string history (gradio compatibility)
        if isinstance(history, str):
            try:
                history = json.loads(history) or []
            except json.JSONDecodeError:
                logger.warning("Invalid JSON for history; defaulting to empty list")
                history = []
        if not isinstance(history, list):
            logger.warning(f"Unexpected history type {type(history)}; defaulting to []")
            history = []

        # Build conversation messages
        system_message = {"role": "system", "content": system_prompt}
        messages = [system_message, *history, {"role": "user", "content": message}]

        # Create streaming handler and process (OpenAI-style for OpenRouter compatibility)
        handler = OpenAIStreamingHandler(client, MODEL_NAME)
        logger.info("OpenRouterAgentCreator: Starting chat with tools using OpenRouter")
        yield from handler.stream_chat_with_tools(messages)
        logger.info("OpenRouterAgentCreator: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in OpenRouterAgentCreator streaming: {e}")
        yield f"🚫 Error processing request with OpenRouter: {str(e)}\n\nPlease check your OpenRouter API key configuration."


if __name__ == "__main__":
    # Simple local test harness (non-streaming print)
    print("Testing OpenRouterAgentCreator wiring (dry-run)...")
    print("Test completed! (Use the UI to chat and stream responses)")