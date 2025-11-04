"""
Claude Agent Creator - An AI agent that helps create other custom agents (Anthropic Claude)

This agent mirrors AgentCreator but uses Anthropic Claude Sonnet for reasoning
and tool-use streaming.

Capabilities:
1. Creating custom agent code using file tools
2. Agent architecture design
3. Integration patterns with tool system
4. Best practices for agent development
5. Using tools to edit files and create working agents

Enhanced with tool integration capabilities for file operations.
"""

import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger(__name__)

# Model selection identifier for UI/router consumption
# Update to your preferred Claude Sonnet variant if needed
MODEL_NAME = "claude-sonnet-4-20250514"

# Import required modules and backend helpers
from icpy.agent.core.llm.anthropic_client import AnthropicClientAdapter
from icpy.agent.core.runtime.general_agent import GeneralAgent
from icpy.agent.core.runtime.message_utils import build_safe_messages
from icpy.agent.helpers import (
    create_standard_agent_metadata,
    create_environment_reload_function,
    get_available_tools_summary,
    ToolDefinitionLoader,
    add_context_to_agent_prompt,
)

# Agent metadata using helper
AGENT_METADATA = create_standard_agent_metadata(
    name="ClaudeAgentCreator",
    description="An AI agent (Claude) that helps you create other custom agents using file editing tools",
    version="1.0.0",
    author="Hot Reload System",
    model=MODEL_NAME,
)

# Individual metadata fields for backward compatibility
AGENT_NAME = AGENT_METADATA["AGENT_NAME"]
AGENT_DESCRIPTION = AGENT_METADATA["AGENT_DESCRIPTION"]
AGENT_VERSION = AGENT_METADATA["AGENT_VERSION"]
AGENT_AUTHOR = AGENT_METADATA["AGENT_AUTHOR"]

# Create standardized reload function using helper
reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.anthropic_client",
    "icpy.agent.core.runtime.general_agent",
    "icpy.agent.core.runtime.message_utils",
])


def get_tools():
    """
    Get available tools for ClaudeAgentCreator using the helper class.

    Returns Anthropic function/tool calling compatible tool definitions.
    Falls back to OpenAI-compatible tool schema if Anthropic-specific export
    is not available in the current backend version.
    """
    try:
        loader = ToolDefinitionLoader()
        # Prefer OpenAI tool schema; backend maps these for Claude calls
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
    Claude Agent Creator streaming chat function with tool integration using helpers.

    Args:
        message: str - User message
        history: List[Dict] or str (JSON) - Conversation history

    Yields:
        str - Response chunks for streaming
    """
    # Enhanced system prompt with tools information and context
    base_system_prompt = f"""You are ClaudeAgentCreator, an expert AI agent specialized in helping developers create custom agents for icotes using powerful file editing tools.

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
1. All custom agents should be created under backend/icpy/agent/ directory.
2. all your code is under backend/icpy/agent/claude_agent_creator_agent.py you can use this as implementation reference. when I refer to you or your code, this is the file I am refering to.
3. agents should use this convention: <AGENT_NAME>_agent.py
4. after a new agent is created, you also need to add a config update to workspace/.icotes/agents.json for this agent to be properly registered with the hot reload system.
5. before you modify the agent.json, make sure you read it and understand its structure before updating it, always update with the same structure as the original.

IMPORTANT AGENT STRUCTURE:
- Your workspace root is: <workspace_root>
- Agent files go in: <workspace_root>/backend/icpy/agent/<AGENT_NAME>_agent.py
- Configuration goes in: <workspace_root>/workspace/.icotes/agents.json
- The backend/icpy/agent/ directory is the correct location for all built-in agent files

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
        # Prepare messages using shared utility
        safe_messages = build_safe_messages(message, history)

        # Delegate to generalized agent using Anthropic adapter
        adapter = AnthropicClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("ClaudeAgentCreator: Starting chat with tools using GeneralAgent")
        tools = []
        try:
            tools = ToolDefinitionLoader().get_openai_tools()
        except Exception:
            pass
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages, tools=tools)
        logger.info("ClaudeAgentCreator: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in ClaudeAgentCreator streaming: {e}")
        yield f"🚫 Error processing request with Claude: {str(e)}\n\nPlease check your Anthropic API key configuration."


if __name__ == "__main__":
    # Simple local test harness (non-streaming print)
    print("Testing ClaudeAgentCreator wiring (dry-run)...")
    print("Test completed! (Use the UI to chat and stream responses)")
