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

# Agent metadata
AGENT_NAME = "AgentCreator"
AGENT_DESCRIPTION = "An AI agent that helps you create other custom agents using file editing tools"
AGENT_VERSION = "2.0.0"
AGENT_AUTHOR = "Hot Reload System"

# Import OpenAI client
try:
    import sys
    backend_path = os.environ.get("ICOTES_BACKEND_PATH")
    if not backend_path:
        # Default to ../backend relative to this file
        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
    sys.path.append(backend_path)
    from icpy.agent.clients import get_openai_client
    OPENAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OpenAI client not available: {e}")
    OPENAI_AVAILABLE = False

# Tool system integration (will be available after Phase 1 implementation)
TOOLS_AVAILABLE = False
try:
    # These imports will work after Phase 1 implementation
    from icpy.agent.tools import get_tool_registry
    from icpy.agent.tools.base_tool import ToolResult
    TOOLS_AVAILABLE = True
    logger.info("Tool system available for AgentCreator")
except ImportError as e:
    logger.info(f"Tool system not yet available: {e}")

def get_tools():
    """
    Get available tools for AgentCreator
    
    Returns OpenAI function calling compatible tool definitions
    """
    tools = []
    
    if TOOLS_AVAILABLE:
        # Use the tool registry to get all available tools
        try:
            registry = get_tool_registry()
            for tool in registry.get_all_tools():
                tools.append({
                    "type": "function", 
                    "function": tool.to_openai_function()
                })
        except Exception as e:
            logger.warning(f"Failed to load tools from registry: {e}")
    
    # Fallback: Define the 5 core tools manually for now
    # This will be replaced by the tool registry after Phase 1
    core_tools = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file, optionally specifying line range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filePath": {
                            "type": "string",
                            "description": "Path to the file to read"
                        },
                        "startLine": {
                            "type": "integer",
                            "description": "Starting line number (optional)"
                        },
                        "endLine": {
                            "type": "integer", 
                            "description": "Ending line number (optional)"
                        }
                    },
                    "required": ["filePath"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_file",
                "description": "Create a new file with specified content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filePath": {
                            "type": "string",
                            "description": "Path where the file should be created"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        },
                        "createDirectories": {
                            "type": "boolean",
                            "description": "Whether to create parent directories if they don't exist"
                        }
                    },
                    "required": ["filePath", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_in_terminal",
                "description": "Execute a command in the terminal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Explanation of what the command does"
                        },
                        "isBackground": {
                            "type": "boolean",
                            "description": "Whether to run the command in background"
                        }
                    },
                    "required": ["command", "explanation"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "replace_string_in_file",
                "description": "Replace a string in a file with another string",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filePath": {
                            "type": "string",
                            "description": "Path to the file to modify"
                        },
                        "oldString": {
                            "type": "string",
                            "description": "String to be replaced"
                        },
                        "newString": {
                            "type": "string",
                            "description": "String to replace with"
                        },
                        "validateContext": {
                            "type": "boolean",
                            "description": "Whether to validate context before replacement"
                        }
                    },
                    "required": ["filePath", "oldString", "newString"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "semantic_search",
                "description": "Search for code or files using natural language descriptions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language description of what to search for"
                        },
                        "scope": {
                            "type": "string",
                            "description": "Directory scope to search within (optional)"
                        },
                        "fileTypes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File extensions to filter by (optional)"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    return tools if TOOLS_AVAILABLE else core_tools

async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool call and return results
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Arguments to pass to the tool
        
    Returns:
        Dictionary with execution results
    """
    if TOOLS_AVAILABLE:
        try:
            registry = get_tool_registry()
            tool = registry.get_tool(tool_name)
            if tool:
                result = await tool.execute(**arguments)
                return {
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "metadata": result.metadata
                }
            else:
                return {
                    "success": False,
                    "error": f"Tool {tool_name} not found in registry"
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }
    else:
        # Fallback: Mock tool execution for development
        logger.info(f"Mock executing tool {tool_name} with args: {arguments}")
        return {
            "success": True,
            "data": f"Mock result for {tool_name}",
            "message": "Tool system not yet implemented - this is a mock response"
        }

def chat(message, history):
    """
    Agent Creator streaming chat function with tool integration
    
    Args:
        message: str - User message
        history: List[Dict] or str (JSON) - Conversation history
        
    Yields:
        str - Response chunks for streaming
    """
    if not OPENAI_AVAILABLE:
        yield "🚫 OpenAI client not available. Please check your OPENAI_API_KEY configuration."
        return
    
    try:
        # Handle JSON string history (gradio compatibility)
        if isinstance(history, str):
            history = json.loads(history)
        
        # Build conversation messages with enhanced system prompt
        system_message = {
            "role": "system", 
            "content": """You are AgentCreator, an expert AI agent specialized in helping developers create custom agents for icotes using powerful file editing tools.

Your capabilities include:
- **File Operations**: Read, create, and modify files using integrated tools
- **Code Generation**: Write clean, maintainable agent code with proper structure
- **Agent Architecture**: Design robust agent systems with tool integration
- **Testing**: Create comprehensive tests following TDD principles
- **Integration**: Seamlessly integrate with icotes hot-reload system

Available Tools:
1. **read_file** - Read file contents with optional line range
2. **create_file** - Create new files with content and directory creation
3. **run_in_terminal** - Execute terminal commands for testing and setup
4. **replace_string_in_file** - Precise string replacement with context validation
5. **semantic_search** - Find code using natural language descriptions

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
        }
        
        messages = [system_message] + history + [{"role": "user", "content": message}]
        
        # Call OpenAI streaming API with tools
        logger.info("AgentCreator: Creating OpenAI streaming call with tools")
        client = get_openai_client()
        
        # Start the conversation loop for tool calls
        while True:
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                tools=get_tools(),
                tool_choice="auto",
                stream=True
            )
            
            logger.info("AgentCreator: Starting OpenAI stream iteration")
            collected_chunks = []
            collected_tool_calls = []
            finish_reason = None
            
            for chunk in stream:
                # Capture finish reason
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                
                # Handle content streaming
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    collected_chunks.append(content)
                    yield content
                
                # Handle tool calls
                if hasattr(chunk.choices[0].delta, 'tool_calls') and chunk.choices[0].delta.tool_calls:
                    for tool_call in chunk.choices[0].delta.tool_calls:
                        if tool_call.function:
                            collected_tool_calls.append(tool_call)
            
            # If no tool calls, we're done
            if finish_reason != "tool_calls" or not collected_tool_calls:
                break
            
            # Process tool calls
            yield "\n\n🔧 **Executing tools...**\n"
            
            # Add assistant message with tool calls to conversation
            assistant_message = {
                "role": "assistant",
                "content": "".join(collected_chunks),
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in collected_tool_calls
                ]
            }
            messages.append(assistant_message)
            
            # Execute each tool call
            for tool_call in collected_tool_calls:
                try:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    yield f"\n📋 **{tool_name}**: {arguments}\n"
                    
                    # Execute the tool
                    result = await execute_tool_call(tool_name, arguments)
                    
                    if result["success"]:
                        yield f"✅ **Success**: {result.get('data', 'Operation completed')}\n"
                    else:
                        yield f"❌ **Error**: {result.get('error', 'Unknown error')}\n"
                    
                    # Add tool result to conversation
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    }
                    messages.append(tool_message)
                    
                except Exception as e:
                    error_msg = f"❌ **Tool Error**: {str(e)}\n"
                    yield error_msg
                    logger.error(f"Tool execution error: {e}")
                    
                    # Add error to conversation
                    tool_message = {
                        "role": "tool", 
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"success": False, "error": str(e)})
                    }
                    messages.append(tool_message)
            
            yield "\n🔧 **Tool execution complete. Continuing...**\n\n"
        
        logger.info("AgentCreator: OpenAI stream complete")
                
    except Exception as e:
        logger.error(f"Error in AgentCreator streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenAI API key configuration."

def reload_env():
    """Called when environment variables are reloaded"""
    global TOOLS_AVAILABLE
    try:
        # Re-check tool availability after environment reload
        from icpy.agent.tools import get_tool_registry
        TOOLS_AVAILABLE = True
        logger.info("Tool system reloaded and available")
    except ImportError:
        TOOLS_AVAILABLE = False
        logger.info("Tool system still not available after reload")

if __name__ == "__main__":
    # Test the chat function locally
    test_message = "Hello, AgentCreator! Can you help me create a simple agent that can read and create files?"
    test_history = []
    
    print("Testing AgentCreator with tool integration:")
    for chunk in chat(test_message, test_history):
        print(chunk, end="")
    print("\n\nTest completed!") 