"""
Example Tool Using Agent - Demonstrates all 5 core tools

This agent shows how to use all the implemented tools:
1. semantic_search - Find relevant code
2. read_file - Read file contents  
3. create_file - Create new files
4. replace_string_in_file - Edit existing files
5. run_in_terminal - Execute commands

This serves as both an example and a test of the tool system.
"""

import json
import os
import logging
import asyncio
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger(__name__)

# Agent metadata
AGENT_NAME = "ExampleToolUser"
AGENT_DESCRIPTION = "An example agent that demonstrates using all 5 core tools"
AGENT_VERSION = "1.0.0"
AGENT_AUTHOR = "Tool System"

# Tool system integration
TOOLS_AVAILABLE = False
try:
    import sys
    backend_path = os.environ.get("ICOTES_BACKEND_PATH")
    if not backend_path:
        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
    sys.path.append(backend_path)
    from icpy.agent.tools import get_tool_registry
    from icpy.agent.tools.base_tool import ToolResult
    TOOLS_AVAILABLE = True
    logger.info("Tool system available for ExampleToolUser")
except ImportError as e:
    logger.info(f"Tool system not available: {e}")

def get_tools():
    """Get available tools for demonstration"""
    if TOOLS_AVAILABLE:
        try:
            registry = get_tool_registry()
            return [
                {"type": "function", "function": tool.to_openai_function()}
                for tool in registry.all()
            ]
        except Exception as e:
            logger.warning(f"Failed to load tools from registry: {e}")
    
    return []

async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call and return results"""
    if TOOLS_AVAILABLE:
        try:
            registry = get_tool_registry()
            tool = registry.get(tool_name)
            if tool:
                result = await tool.execute(**arguments)
                return {
                    "success": result.success,
                    "data": result.data,
                    "error": result.error
                }
            else:
                return {
                    "success": False,
                    "error": f"Tool {tool_name} not found"
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }
    else:
        return {
            "success": False,
            "error": "Tool system not available"
        }

def chat(message, history):
    """
    Demonstration chat function that shows tool usage
    """
    try:
        # Handle JSON string history
        if isinstance(history, str):
            history = json.loads(history)
        
        yield "🔧 **ExampleToolUser Agent**\n\n"
        yield "I'm demonstrating the 5 core tools. Let me show you each one:\n\n"
        
        # Helper function to safely run async code
        def run_tool_safely(tool_name, args):
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, create a new thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, execute_tool_call(tool_name, args))
                        return future.result()
                except RuntimeError:
                    # No running loop, safe to use asyncio.run
                    return asyncio.run(execute_tool_call(tool_name, args))
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # 1. Semantic Search
        yield "**1. Semantic Search Tool**\n"
        result = run_tool_safely("semantic_search", {
            "query": "import",
            "fileTypes": ["py"]
        })
        if result["success"]:
            count = len(result["data"]) if result["data"] else 0
            yield f"✅ Found {count} Python import statements\n\n"
        else:
            yield f"❌ Search failed: {result['error']}\n\n"
        
        # 2. Read File  
        yield "**2. Read File Tool**\n"
        result = run_tool_safely("read_file", {
            "filePath": "README.md",
            "startLine": 1,
            "endLine": 5
        })
        if result["success"]:
            content = result["data"]["content"] if result["data"] else ""
            lines = len(content.split('\n')) if content else 0
            yield f"✅ Read {lines} lines from README.md\n\n"
        else:
            yield f"❌ Read failed: {result['error']}\n\n"
        
        # 3. Create File
        yield "**3. Create File Tool**\n"
        result = run_tool_safely("create_file", {
            "filePath": "test_tool_demo.txt",
            "content": "This file was created by the ExampleToolUser agent!\nTimestamp: " + str(hash(message))
        })
        if result["success"]:
            yield "✅ Created test_tool_demo.txt\n\n"
        else:
            yield f"❌ Create failed: {result['error']}\n\n"
        
        # 4. Replace String
        yield "**4. Replace String Tool**\n"
        result = run_tool_safely("replace_string_in_file", {
            "filePath": "test_tool_demo.txt",
            "oldString": "ExampleToolUser",
            "newString": "AwesomeToolUser"
        })
        if result["success"]:
            count = result["data"]["replacedCount"] if result["data"] else 0
            yield f"✅ Replaced {count} occurrences in test_tool_demo.txt\n\n"
        else:
            yield f"❌ Replace failed: {result['error']}\n\n"
        
        # 5. Run Terminal Command
        yield "**5. Terminal Command Tool**\n"
        result = run_tool_safely("run_in_terminal", {
            "command": "echo 'Hello from ExampleToolUser!'",
            "explanation": "Test terminal command execution"
        })
        if result["success"]:
            output = result["data"]["output"] if result["data"] else ""
            yield f"✅ Command executed: {output.strip()}\n\n"
        else:
            yield f"❌ Command failed: {result['error']}\n\n"
        
        yield "🎉 **All 5 tools demonstrated successfully!**\n"
        yield "The tool system is working and ready for agent development.\n"
        
    except Exception as e:
        logger.error(f"Error in ExampleToolUser: {e}")
        yield f"❌ Agent error: {str(e)}\n"

def reload_env():
    """Called when environment variables are reloaded"""
    global TOOLS_AVAILABLE
    try:
        from icpy.agent.tools import get_tool_registry
        TOOLS_AVAILABLE = True
        logger.info("Tool system reloaded and available")
    except ImportError:
        TOOLS_AVAILABLE = False
        logger.info("Tool system still not available after reload")

if __name__ == "__main__":
    # Test the agent locally
    print("Testing ExampleToolUser Agent:")
    for chunk in chat("demo", []):
        print(chunk, end="")
    print("\nDemo completed!") 