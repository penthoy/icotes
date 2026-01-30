"""
Helper functions for agent development that can be reused across different agents.

This module provides common functionality for:
- Tool execution and management
- OpenAI streaming with tool call handling
- Tool result formatting
- Error handling for agent operations
- Agent context bootstrapping with environmental information

These helpers abstract away complex boilerplate code so that custom agents 
can focus on their specific logic and domain expertise.
"""

import json
import logging
import asyncio
import concurrent.futures
import copy
import os
import platform
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Dict, List, Any, AsyncGenerator, Optional, Tuple, Callable

from .tools import get_tool_registry, ToolResult
from .debug_interceptor import get_interceptor, get_context_snapshot

# Phase 2: Context variable to store vendor-specific metadata across async calls
_vendor_metadata: ContextVar[Optional[Dict[str, Any]]] = ContextVar('vendor_metadata', default=None)


def set_vendor_metadata(vendor_parts: Optional[List[Dict]], vendor_model: Optional[str]):
    """Store vendor-specific metadata in context for later retrieval by chat service."""
    if vendor_parts or vendor_model:
        _vendor_metadata.set({
            'vendor_parts': vendor_parts,
            'vendor_model': vendor_model
        })
    else:
        _vendor_metadata.set(None)


def get_vendor_metadata() -> Optional[Dict[str, Any]]:
    """Retrieve vendor-specific metadata from context."""
    return _vendor_metadata.get()


def clear_vendor_metadata():
    """Clear vendor-specific metadata from context."""
    _vendor_metadata.set(None)


def get_openai_token_param(model_name: str, max_tokens: int) -> dict:
    """
    Get the correct token parameter for OpenAI API calls based on model family.
    
    GPT-5 and o1 models use 'max_completion_tokens', while GPT-4 and earlier use 'max_tokens'.
    
    Args:
        model_name: The OpenAI model name
        max_tokens: The token limit value
        
    Returns:
        dict: Dictionary containing the appropriate parameter key and value
    """
    name = (model_name or "").lower()
    # OpenAI GPT-5+ and o1-style models
    if "gpt-5" in name or name.startswith("o1"):
        return {"max_completion_tokens": max_tokens}
    # Cerebras chat-completions models use max_completion_tokens per docs
    if name.startswith("qwen-3-") or name.startswith("llama-") or name.startswith("gpt-oss-"):
        return {"max_completion_tokens": max_tokens}
    # Default OpenAI-compatible chat.completions
    return {"max_tokens": max_tokens}

# Public API exports
__all__ = [
    # OpenAI utilities
    'get_openai_token_param',
    
    # Tool execution and management
    'ToolExecutor',
    'ToolDefinitionLoader', 
    'ToolResultFormatter',
    'OpenAIStreamingHandler',
    
    # Agent factory functions
    'create_agent_chat_function',
    'create_simple_agent_chat_function',
    
    # Metadata and environment helpers
    'create_standard_agent_metadata',
    'create_environment_reload_function',
    'get_model_name_for_agent',
    
    # Context bootstrapping functions
    'create_agent_context',
    'format_agent_context_for_prompt',
    'add_context_to_agent_prompt',
    
    # Utility functions
    'get_available_tools_summary',
    'validate_tool_arguments',
    # Content/history utilities
    'flatten_message_content',
    'normalize_history',
    # Prompt templates
    'BASE_SYSTEM_PROMPT_TEMPLATE',
    # Vendor metadata (Phase 2)
    'set_vendor_metadata',
    'get_vendor_metadata',
    'clear_vendor_metadata',
]

logger = logging.getLogger(__name__)
# -----------------------------
# Prompt templates
# -----------------------------
# Generic base system prompt template for agents. Inject the agent name and tools summary at runtime.
BASE_SYSTEM_PROMPT_TEMPLATE = """You are {AGENT_NAME}, a helpful and versatile AI assistant.

**Available Tools:**
{TOOLS_SUMMARY}

**When asked to create an app:**
- create it under workspace which is your work root unless specified otherwise.
- Create it using html/css/js by default unless the user specifies otherwise.

**When asked to create or edit images:**
- Don't ask for clarifying questions unless you absolutely not sure what to do.
- When the user attaches an image with a file path hint (shown in brackets like "[Image attached: filename (path: ...)]"), use that EXACT path in the generate_image tool's image_data parameter
- The file paths may include hop contexts (e.g., "hop1:/path/to/file.png") which the tool handles automatically
- When editing attached images, combine the user's edit instructions with a reference to the source image: pass the file path to image_data parameter and describe the edits in the prompt parameter

**File Operations Best Practices:**
- Always save generated files (images, documents, code) to the workspace directory
- Use the `get_workspace_path()` helper function from `icpy.agent.helpers` to get the correct workspace path
- Never hardcode workspace paths - use the helper function for proper path detection
- The workspace directory is automatically detected and is the proper location for all user-facing files

**Namespace-aware paths (hop support):**
- File paths may be prefixed with a namespace to indicate the target context: `<namespace>:/absolute/path`.
- Examples: `local:/workspace/file.txt`, `hop1:/home/user/app.py`.
- If no namespace is provided, use the active context (local or current hop).
- Treat Windows drive letters like `C:/path` as plain paths, not namespaces.
- When you return paths from tools, prefer the namespaced `filePath` and/or `pathInfo.formatted_path` fields for clarity.

**Namespace defaults and guardrails (to avoid cross-context mistakes):**
- When hopped, bare paths operate in the REMOTE context. If you need the LOCAL workspace while hopped, explicitly prefix `local:/`.
- For common local-only files (e.g., `workspace/README.md`, project configs), prefer `local:/workspace/...` unless the user explicitly requests remote.
- When in doubt, echo back the target path with its namespace (e.g., `local:/...` or `hop1:/...`) before acting.

**Core Behavior:**
- Be helpful, accurate, and informative in your responses
- Use tools when appropriate to provide better assistance
- Keep internal reasoning to yourself. Do not include chain-of-thought, step-by-step planning, or meta commentary in the final answer. Provide the answer directly with any necessary brief justification.

**Tool Usage:**
- Use file tools (read_file, create_file, replace_string_in_file) for file operations
- Use run_in_terminal for executing commands and scripts
- Use semantic_search to find relevant information in the workspace
- Use web_search to find current information from the web
- Use generate_image for image generation. default to 1:1 (square) aspect ratio unless the user explicitly requests a different format or the content clearly requires a specific orientation (e.g., wide landscape, tall portrait)
- When you use tools, do not narrate detailed steps. If helpful, you may add a one-line summary of the action, but prefer letting results speak for themselves.

**Absolute paths are REQUIRED for all tools that accept file paths:**
- Never pass a relative path like `tool_tests/test.txt` or `./file.png`.
- Always pass an absolute path, and when working across contexts include the namespace (e.g., `local:/workspace/tool_tests/test.txt` or `hop1:/home/user/tool_tests/test.txt`).
- When constructing paths, use `get_workspace_path()` to resolve the absolute workspace directory, then join your filename. Echo back namespaced absolute paths in your responses so users can verify the target.

**Response Style:**
- Be concise but thorough
- Use clear formatting and structure
- Provide examples when helpful
- Acknowledge limitations when relevant

Focus on being genuinely helpful while using the available tools effectively to enhance your capabilities."""


# -----------------------------
# Generic content/history utils
# -----------------------------
def flatten_message_content(content: Any) -> str:
    """Coerce OpenAI-style content (string, list of parts, or dict) into a plain string.

    - Arrays of parts (e.g., [{type:'text'},{type:'image_url', image_url:{url}}]) are flattened
      into human-readable text with minimal markers for non-text parts.
    - Dict content falls back to text field if present, otherwise JSON string.
    - None -> ""; primitives -> str(value).
    """
    try:
        # Handle array of content parts
        if isinstance(content, list):
            parts: List[str] = []
            for part in content:
                if not isinstance(part, dict):
                    parts.append(str(part))
                    continue
                ptype = part.get("type")
                if ptype == "text":
                    parts.append(str(part.get("text", "")))
                elif ptype == "image_url":
                    img = part.get("image_url")
                    url = None
                    if isinstance(img, dict):
                        url = img.get("url")
                    elif isinstance(img, str):
                        url = img
                    parts.append(f"[image: {url}]" if url else "[image]")
                else:
                    parts.append(f"[{ptype or 'part'}]")
            return " ".join([p for p in parts if p])
        # Dict content -> stringify safely
        if isinstance(content, dict):
            if "text" in content and isinstance(content["text"], str):
                return content["text"]
            return json.dumps(content)
        # None -> empty string
        if content is None:
            return ""
        # Primitive -> str
        return str(content)
    except Exception:
        return str(content) if content is not None else ""


def normalize_history(
    raw_history: Any,
    *,
    drop_empty_user: bool = True,
    default_role: str = "user",
) -> List[Dict[str, Any]]:
    """Normalize conversation history without destroying multimodal content.

    Behavior changes (fix regression):
    - Preserve OpenAI rich content arrays for user messages (e.g.,
      [{"type":"text",...},{"type":"image_url",...}]) so image attachments
      survive through to the model.
    - Flatten other non-string content to text via flatten_message_content.
    - Drop empty entries; for rich arrays, consider non-empty if any text has
      non-whitespace or any image_url part has a URL.
    """
    messages: List[Dict[str, Any]] = []
    if not raw_history:
        return messages
    try:
        raw = json.loads(raw_history) if isinstance(raw_history, str) else raw_history
    except Exception:
        logger.warning("normalize_history: history is a non-JSON string; ignoring")
        return messages

    if not isinstance(raw, list):
        logger.warning("normalize_history: history not a list; ignoring")
        return messages

    def _is_rich_parts(val: Any) -> bool:
        if isinstance(val, list) and val:
            # Heuristic: list of dicts with 'type' keys like text/image_url
            return all(isinstance(p, dict) and p.get("type") in ("text", "image_url") for p in val if isinstance(p, dict))
        return False

    def _rich_non_empty(val: List[Dict[str, Any]]) -> bool:
        for p in val:
            if not isinstance(p, dict):
                # Non-dict part counts as content
                return True
            t = p.get("type")
            if t == "text" and isinstance(p.get("text"), str) and p["text"].strip():
                return True
            if t == "image_url":
                img = p.get("image_url")
                url = img.get("url") if isinstance(img, dict) else (img if isinstance(img, str) else None)
                if url:
                    return True
        return False

    filtered = 0
    for idx, m in enumerate(raw):
        try:
            role = (m or {}).get("role", default_role)
            raw_content = (m or {}).get("content")

            # Preserve rich parts for user messages
            if role == "user" and _is_rich_parts(raw_content):
                if drop_empty_user and not _rich_non_empty(raw_content):
                    filtered += 1
                    logger.info(
                        f"normalize_history: Dropping empty rich user message at index {idx}"
                    )
                    continue
                content = raw_content
            else:
                # Fallback to flattened string content
                content = flatten_message_content(raw_content)
                is_empty = not content or not str(content).strip()
                if is_empty and (role == "user" and drop_empty_user):
                    filtered += 1
                    logger.info(
                        f"normalize_history: Dropping empty user message at index {idx}"
                    )
                    continue
            messages.append({"role": role, "content": content})
        except Exception as e:
            logger.warning(f"normalize_history: Failed to normalize history item {idx}: {e}")
    if filtered:
        logger.info(f"normalize_history: Filtered {filtered} empty history messages")
    return messages


class ToolExecutor:
    """
    Helper class for executing tools in agents with proper error handling
    and async support.
    """
    
    def __init__(self):
        self.registry = get_tool_registry()
    
    async def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call and return results with proper error handling.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            
        Returns:
            Dictionary with execution results in format:
            {
                "success": bool,
                "data": Any,
                "error": Optional[str]
            }
        """
        try:
            tool = self.registry.get(tool_name)
            if not tool:
                return {
                    "success": False,
                    "error": f"Tool {tool_name} not found in registry"
                }
            
            # Execute the tool
            result = await tool.execute(**arguments)
            
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }
    
    def execute_tool_call_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous wrapper for tool execution that handles event loop properly.
        
        This is useful when calling from within an existing event loop context.
        Works correctly whether called from main thread, async context, or executor thread.
        """
        try:
            # Try to get the running loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context with a running loop
                # We need to run in a new thread to avoid blocking
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._run_async_in_new_loop, tool_name, arguments)
                    return future.result()
            except RuntimeError:
                # No running loop - we can create one safely
                return asyncio.run(self.execute_tool_call(tool_name, arguments))
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_async_in_new_loop(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to run async code in a new event loop (for executor threads)"""
        # Create a new event loop for this thread
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(self.execute_tool_call(tool_name, arguments))
        finally:
            new_loop.close()


class ToolDefinitionLoader:
    """
    Helper class for loading tool definitions in OpenAI function calling format.
    """
    
    def __init__(self):
        self.registry = get_tool_registry()
    
    def get_openai_tools(self, exclude_tools: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available tools in OpenAI function calling format.
        
        Args:
            exclude_tools: Optional list of tool names to exclude
        
        Returns:
            List of tool definitions compatible with OpenAI function calling
        """
        tools = []
        exclude_tools = exclude_tools or []
        
        try:
            for tool in self.registry.all():
                if tool.name not in exclude_tools:
                    tools.append({
                        "type": "function", 
                        "function": tool.to_openai_function()
                    })
            logger.info(f"Loaded {len(tools)} tools from registry (excluded: {exclude_tools})")
            return tools
        except Exception as e:
            logger.warning(f"Failed to load tools from registry: {e}")
            return []
    
    def get_tool_names(self) -> List[str]:
        """Get list of all available tool names."""
        return [tool.name for tool in self.registry.all()]
    
    def get_openai_tools_compact(self, exclude_tools: List[str] = None) -> List[Dict[str, Any]]:
        """Get tools with minimal descriptions for context-limited providers.
        
        This version strips verbose descriptions and examples from parameter docs
        to save tokens while preserving full functionality.
        
        Args:
            exclude_tools: Optional list of tool names to exclude
        
        Returns:
            List of compact tool definitions
        """
        tools = []
        exclude_tools = exclude_tools or []
        
        try:
            for tool in self.registry.all():
                if tool.name not in exclude_tools:
                    # Get base tool definition without mutating registry's cached schema
                    func_def = copy.deepcopy(tool.to_openai_function())
                    
                    # Compact the description (keep first sentence only)
                    if 'description' in func_def:
                        desc = func_def['description']
                        first_sentence = desc.split('.')[0] + '.' if '.' in desc else desc
                        func_def['description'] = first_sentence[:100]  # Cap at 100 chars
                    
                    # Compact parameter descriptions
                    if 'parameters' in func_def and 'properties' in func_def['parameters']:
                        for param_name, param_def in func_def['parameters']['properties'].items():
                            if isinstance(param_def, dict) and 'description' in param_def:
                                desc = param_def['description']
                                # Keep first sentence only, max 80 chars
                                first_sentence = desc.split('.')[0] + '.' if '.' in desc else desc
                                param_def['description'] = first_sentence[:80]
                    
                    tools.append({
                        "type": "function",
                        "function": func_def
                    })
            
            logger.info(f"Loaded {len(tools)} compact tools (excluded: {exclude_tools})")
            return tools
        except Exception as e:
            logger.warning(f"Failed to load compact tools: {e}")
            # Fallback to regular tools
            return self.get_openai_tools(exclude_tools)


class ToolResultFormatter:
    """
    Helper class for formatting tool execution results in a user-friendly way.
    """
    
    @staticmethod
    def format_tool_call_start(tool_name: str, arguments: Dict[str, Any]) -> str:
        """Format the start of a tool call execution."""
        return f"\n📋 **{tool_name}**: {arguments}\n"
    
    @staticmethod
    def format_tool_result(tool_name: str, result: Dict[str, Any]) -> str:
        """
        Format tool execution result for display to user.
        
        Args:
            tool_name: Name of the tool that was executed
            result: Result dictionary from tool execution
            
        Returns:
            Formatted string for display
        """
        if result["success"]:
            data = result.get('data', 'Operation completed')
            
            # Format based on tool type for better readability
            if tool_name == 'read_file' and isinstance(data, dict) and 'content' in data:
                # For read_file, show summary instead of full content
                file_path = data.get('filePath', 'file')
                content_lines = len(data['content'].split('\n')) if data['content'] else 0
                content_size = len(data['content']) if data['content'] else 0
                return f"✅ **Success**: Read {file_path} ({content_lines} lines, {content_size} characters)\n"
            
            elif tool_name == 'create_file' and isinstance(data, dict):
                # For create_file, show confirmation with namespaced path if available
                path = data.get('filePath') or data.get('absolutePath') or 'file'
                msg = data.get('message') or 'File created successfully'
                return f"✅ **Success**: {msg} at {path}\n"
            
            elif tool_name == 'replace_string_in_file' and isinstance(data, dict):
                # For replace_string_in_file, show explicit counts
                count = data.get('replacedCount')
                changed = data.get('changed')
                path = data.get('filePath', 'file')
                if count is None:
                    return "\u2705 **Success**: Replacement completed\n"
                if count == 0:
                    return f"\u2139\ufe0f No matches found in {path}. Nothing changed.\n"
                if changed is False:
                    return f"\u2139\ufe0f {count} match(es) found in {path}, but content unchanged (newString identical).\n"
                return f"\u2705 **Success**: Replaced {count} occurrence(s) in {path}.\n"
            
            elif tool_name == 'run_in_terminal' and isinstance(data, dict):
                # For terminal commands, show output summary
                output = data.get('output', '')
                if len(output) > 200:
                    output = output[:200] + "... (truncated)"
                return f"✅ **Success**: Command executed\nOutput: {output}\n"
            
            elif tool_name == 'generate_image' and isinstance(data, dict):
                # Always return the JSON data structure for widget compatibility
                # The widget expects structured data in toolCall.output field
                # Phase 1 conversion in chat_service will convert imageData to ImageReference during storage
                json_str = json.dumps(data)
                try:
                    abs_path = data.get('absolutePath') or (
                        (data.get('imageReference') or {}).get('absolute_path') if isinstance(data.get('imageReference'), dict) else None
                    )
                    logger.info(
                        "ToolResultFormatter: image result emit | savedToWorkspace=%s | absolutePath=%s | filePath=%s | context=%s",
                        data.get('savedToWorkspace'),
                        abs_path,
                        data.get('filePath'),
                        data.get('context')
                    )
                except Exception:
                    # Non-fatal logging failure
                    pass
                return f"✅ **Success**: {json_str}\n"
            
            else:
                # For other tools, show data as-is but truncate if too long
                data_str = str(data)
                if len(data_str) > 200:
                    data_str = data_str[:200] + "... (truncated)"
                return f"✅ **Success**: {data_str}\n"
        else:
            return f"❌ **Error**: {result.get('error', 'Unknown error')}\n"


class OpenAIStreamingHandler:
    """
    Helper class for handling OpenAI streaming responses with tool calls.
    
    This abstracts the complex logic of handling streaming responses,
    tool call accumulation, execution, and conversation continuation.
    """
    
    def __init__(self, client, model_name: str, exclude_tools: List[str] = None, use_compact_tools: bool = False, session_id: Optional[str] = None):
        """
        Initialize the streaming handler.
        
        Args:
            client: OpenAI client instance
            model_name: Model name to use for completions
            exclude_tools: Optional list of tool names to exclude (e.g., for API compatibility)
            use_compact_tools: If True, use compact tool schemas to save tokens (for context-limited providers)
            session_id: Optional session ID for debug logging
        """
        self.client = client
        self.model_name = model_name
        self.exclude_tools = exclude_tools or []
        self.use_compact_tools = use_compact_tools
        self.tool_executor = ToolExecutor()
        self.tool_loader = ToolDefinitionLoader()
        self.formatter = ToolResultFormatter()
        self.session_id = session_id
        self.debug_interceptor = get_interceptor(session_id) if session_id else None
        # Phase 2: Store vendor-specific metadata from last streaming response
        self.last_vendor_parts: Optional[List[Dict]] = None
        self.last_vendor_model: Optional[str] = None
    
    def stream_chat_with_tools(self, messages: List[Dict[str, Any]], 
                              max_tokens: int | None = None,
                              auto_continue: bool | None = None,
                              max_continue_rounds: int | None = None,
                              extra_params: Dict[str, Any] | None = None) -> AsyncGenerator[str, None]:
        """
        Handle streaming chat with tool calls.
        
        This method handles the complete flow:
        1. Send messages to OpenAI with tools
        2. Stream the response 
        3. Handle tool calls if they occur
        4. Execute tools and add results to conversation
        5. Continue the conversation until completion
        
        Args:
            messages: Conversation messages
            max_tokens: Maximum tokens for completion (defaults from env AGENT_MAX_TOKENS or 3500)
            auto_continue: When response stops due to token limit, automatically continue (env AGENT_AUTO_CONTINUE, default True)
            max_continue_rounds: Maximum number of auto-continue follow-ups (env AGENT_MAX_CONTINUE_ROUNDS, default 3)
            
        Yields:
            str: Response chunks for streaming
        """
        try:
            # Resolve configuration with environment overrides
            if max_tokens is None:
                try:
                    max_tokens = int(os.environ.get("AGENT_MAX_TOKENS", "3500"))
                except ValueError:
                    max_tokens = 2000
            if auto_continue is None:
                auto_continue = os.environ.get("AGENT_AUTO_CONTINUE", "1") not in ("0", "false", "False")
            if max_continue_rounds is None:
                try:
                    max_continue_rounds = int(os.environ.get("AGENT_MAX_CONTINUE_ROUNDS", "10"))
                except ValueError:
                    max_continue_rounds = 10

            # Preflight: sanitize messages to avoid provider validation errors
            def _coerce_content_to_text(val: Any) -> str:
                try:
                    if val is None:
                        return ""
                    if isinstance(val, str):
                        return val
                    if isinstance(val, list):
                        # Keep arrays intact for user messages; this helper is only used
                        # for non-user messages just before request. For safety, we merge
                        # text for previewing/logging but should not be called for user arrays.
                        acc: List[str] = []
                        for part in val:
                            if isinstance(part, dict) and part.get("type") == "text":
                                acc.append(str(part.get("text", "")))
                        return " ".join([x for x in acc if x])
                    if isinstance(val, dict):
                        if "text" in val and isinstance(val["text"], str):
                            return val["text"]
                        return json.dumps(val)
                    return str(val)
                except Exception:
                    return str(val) if val is not None else ""

            # Build a canonical conversation list we'll mutate throughout the loop
            conv: List[Dict[str, Any]] = []
            dropped_users = 0
            def _is_rich_parts(val: Any) -> bool:
                return isinstance(val, list) and any(isinstance(p, dict) and p.get("type") in ("text", "image_url") for p in val)

            def _rich_non_empty(val: List[Dict[str, Any]]) -> bool:
                for p in val:
                    if not isinstance(p, dict):
                        return True
                    t = p.get("type")
                    if t == "text" and isinstance(p.get("text"), str) and p["text"].strip():
                        return True
                    if t == "image_url":
                        img = p.get("image_url")
                        url = img.get("url") if isinstance(img, dict) else (img if isinstance(img, str) else None)
                        if url:
                            return True
                return False

            for idx, m in enumerate(messages or []):
                if not isinstance(m, dict):
                    logger.warning(f"OpenAIStreamingHandler: Non-dict message at index {idx} dropped")
                    continue
                role = m.get("role") or "user"
                raw_content = m.get("content")
                if role == "user" and _is_rich_parts(raw_content):
                    # Preserve rich content for user. Check non-empty via helper.
                    if not _rich_non_empty(raw_content):
                        dropped_users += 1
                        logger.warning(f"OpenAIStreamingHandler: Dropping empty user rich message at index {idx}")
                        continue
                    content = raw_content
                else:
                    content = _coerce_content_to_text(raw_content)
                if role == "user" and (not isinstance(content, str)):
                    # For OpenAI API, user content can be array; keep as-is
                    pass
                elif role == "user" and not (content and str(content).strip()):
                    dropped_users += 1
                    logger.warning(f"OpenAIStreamingHandler: Dropping empty user message at index {idx}")
                    continue
                conv.append({**m, "role": role, "content": content})
            if dropped_users:
                logger.info(f"OpenAIStreamingHandler: Dropped {dropped_users} empty user message(s) before request")

            # Log a brief preview at INFO for easier troubleshooting
            try:
                preview = "\n".join([f"{i}: {m.get('role')} len={len(m.get('content','') or '')}" for i, m in enumerate(conv)])
                logger.info("OpenAIStreamingHandler: Outbound messages preview\n" + preview)
            except Exception as ex:
                logger.debug("OpenAIStreamingHandler: preview generation failed: %s", ex)

            # Get available tools (excluding incompatible ones)
            if self.use_compact_tools:
                tools = self.tool_loader.get_openai_tools_compact(exclude_tools=self.exclude_tools)
            else:
                tools = self.tool_loader.get_openai_tools(exclude_tools=self.exclude_tools)
            
            # Start the conversation loop for tool calls
            continue_round = 0
            # Optional safeguard against runaway tool-call loops (only if env is set)
            max_tool_loops: Optional[int]
            try:
                val = os.environ.get("AGENT_MAX_TOOL_LOOPS")
                max_tool_loops = int(val) if val is not None else None
                if max_tool_loops is not None and max_tool_loops <= 0:
                    # Non-positive disables the cap
                    max_tool_loops = None
            except Exception:
                max_tool_loops = None
            tool_loop_count = 0
            while True:
                # Determine the correct max tokens parameter based on model
                api_params = {
                    "model": self.model_name,
                    "messages": conv,
                    "tools": tools if tools else None,
                    "tool_choice": "auto" if tools else None,
                    "stream": True
                }
                
                # Add the appropriate token parameter
                if max_tokens is not None:
                    api_params.update(get_openai_token_param(self.model_name, max_tokens))
                
                # Apply any extra parameters (e.g., thinking mode for Kimi K2.5)
                # Use extra_body for custom parameters not in OpenAI SDK signature
                if extra_params:
                    api_params["extra_body"] = extra_params
                
                # Log API request to debug interceptor (non-blocking)
                if self.debug_interceptor:
                    try:
                        # Create async task to log without blocking the generator
                        async def _log_request():
                            try:
                                context_info = await get_context_snapshot()
                                await self.debug_interceptor.log_openai_request(api_params, context_info)
                            except Exception as e:
                                logger.debug(f"Failed to log API request: {e}")
                        asyncio.create_task(_log_request())
                    except Exception as e:
                        logger.debug(f"Failed to create log task: {e}")
                
                # Mark request start for timing diagnostics
                _req_start_ts = datetime.now().timestamp()
                
                # Enhanced debug logging for Gemini troubleshooting
                try:
                    from icpy.utils.gemini_debug_logger import get_gemini_debug_logger
                    gemini_debug = get_gemini_debug_logger()
                    # Use session_id as request_id if available, otherwise create one
                    api_request_id = self.session_id if self.session_id else f"api_{int(_req_start_ts)}"
                    gemini_debug.log_api_call(api_request_id, self.model_name, len(conv))
                except Exception as log_err:
                    logger.debug(f"Failed to log API call: {log_err}")
                    api_request_id = None
                
                try:
                    stream = self.client.chat.completions.create(**api_params)
                    
                    # Log successful API response
                    if api_request_id:
                        try:
                            gemini_debug.log_api_response(api_request_id, 200)
                        except Exception:
                            pass
                except Exception as api_error:
                    # Log API call failure
                    if api_request_id:
                        try:
                            gemini_debug.log_error(api_request_id, type(api_error).__name__, str(api_error))
                        except Exception:
                            pass
                    # Re-raise the original error
                    raise
                
                logger.info("Starting OpenAI stream iteration with tools")
                
                # Process the stream and collect tool calls
                collected_chunks, tool_calls_list, finish_reason, vendor_parts = yield from self._process_stream(stream)
                _req_end_ts = datetime.now().timestamp()
                
                # Phase 2: Store vendor_parts in context variable for retrieval by chat service
                # Check if this is a Gemini model and vendor_parts are present
                if vendor_parts and 'gemini' in self.model_name.lower():
                    set_vendor_metadata(vendor_parts, self.model_name)
                    logger.info(f"[GEMINI-DEBUG] Stored {len(vendor_parts)} vendor parts for model {self.model_name}")
                else:
                    # Clear for non-Gemini models or when no parts
                    clear_vendor_metadata()
                
                # Log API response to debug interceptor (non-blocking)
                if self.debug_interceptor:
                    try:
                        async def _log_response():
                            try:
                                await self.debug_interceptor.log_openai_response({
                                    "chunks_preview": "".join(collected_chunks)[:500] if collected_chunks else "",
                                    "duration_sec": round(_req_end_ts - _req_start_ts, 3)
                                }, finish_reason)
                            except Exception as e:
                                logger.debug(f"Failed to log API response: {e}")
                        asyncio.create_task(_log_response())
                    except Exception as e:
                        logger.debug(f"Failed to create log task: {e}")
                
                # If tool calls are present, handle them and then continue loop
                # NOTE: Gemini's OpenAI-compat endpoint returns finish_reason="stop" even with tool calls
                # So we check for tool_calls_list presence regardless of finish_reason
                if tool_calls_list:
                    tool_loop_count += 1
                    logger.info(f"[GEMINI-DEBUG] Tool calls detected | count={len(tool_calls_list)} | finish_reason={finish_reason}")
                    # Handle tool calls
                    yield from self._handle_tool_calls(conv, collected_chunks, tool_calls_list)
                    
                    yield "\n🔧 **Tool execution complete. Continuing...**\n\n"
                    if max_tool_loops is not None and tool_loop_count >= max_tool_loops:
                        logger.warning(
                            f"OpenAIStreamingHandler: Reached max tool-call loops ({max_tool_loops}). Aborting to prevent infinite loop."
                        )
                        yield "\n⚠️ Reached maximum tool-call attempts. Stopping to prevent a loop.\n"
                        break
                    continue

                # For non-tool responses, append assistant content to the conversation
                if collected_chunks:
                    conv.append({"role": "assistant", "content": "".join(collected_chunks)})
                
                # Auto-continue on token limit
                if finish_reason == "length" and auto_continue and continue_round < max_continue_rounds:
                    continue_round += 1
                    logger.info(f"[GEMINI-DEBUG] Token limit hit, auto-continuing | round={continue_round}/{max_continue_rounds}")
                    yield "\n⏭️ Output truncated by token limit. Continuing...\n\n"
                    conv.append({
                        "role": "user",
                        "content": "Continue exactly where you left off. Do not repeat previous text. Resume immediately and finish the response."
                    })
                    continue
                
                # Otherwise, we're done (stop/content_filter/etc.)
                logger.info(f"[GEMINI-DEBUG] Stream loop ending | finish_reason={finish_reason} | tool_loops={tool_loop_count} | continue_rounds={continue_round}")
                break
                
        except Exception as e:
            logger.error(f"Error in OpenAI streaming with tools: {e}")
            yield f"🚫 Error processing request: {str(e)}\n\nPlease check your configuration."
    
    def _process_stream(self, stream) -> Tuple[List[str], List[Dict], Optional[str], Optional[List[Dict]]]:
        """
        Process OpenAI stream and collect content and tool calls.
        
        Returns:
            Tuple of (collected_chunks, tool_calls_list, finish_reason, vendor_parts)
            vendor_parts is a list of raw parts from the provider (for Gemini thought signatures)
        """
        collected_chunks = []
        collected_tool_calls = {}  # Use dict to accumulate tool calls by index
        finish_reason = None
        
        # Phase 0: Track thought signatures for Gemini debugging
        thought_signature_seen = False
        parts_with_signatures = []
        total_parts_count = 0
        
        # Phase 2: Collect vendor-specific parts for preservation
        vendor_parts = []
        
        for chunk in stream:
            # Phase 0: Check for thought_signature or thinking fields in chunk
            # Inspect chunk structure for vendor-specific fields
            chunk_dict = chunk.model_dump() if hasattr(chunk, 'model_dump') else {}
            if chunk_dict:
                # Check choices for thought-related fields
                for choice in chunk_dict.get('choices', []):
                    delta = choice.get('delta', {})
                    
                    # Phase 2: Collect the entire delta as a vendor part if it contains relevant fields
                    # We want to preserve: content, tool_calls, thought_signature, thinking, function_call, etc.
                    if delta and any(key in delta for key in ['content', 'tool_calls', 'thought_signature', 'thinking', 'function_call']):
                        vendor_parts.append({
                            'delta': delta,
                            'index': choice.get('index', 0),
                            'finish_reason': choice.get('finish_reason')
                        })
                    
                    # Look for thought_signature or thinking fields
                    if 'thought_signature' in delta:
                        thought_signature_seen = True
                        parts_with_signatures.append({
                            'type': 'thought_signature',
                            'index': total_parts_count
                        })
                        logger.info(f"[GEMINI-DEBUG] Thought signature detected in delta | chunk_index={total_parts_count}")
                    
                    if 'thinking' in delta:
                        thought_signature_seen = True
                        parts_with_signatures.append({
                            'type': 'thinking',
                            'index': total_parts_count
                        })
                        logger.info(f"[GEMINI-DEBUG] Thinking field detected in delta | chunk_index={total_parts_count}")
                    
                    total_parts_count += 1
            
            # Capture finish reason
            if chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason
            
            # Handle content streaming
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                collected_chunks.append(content)
                yield content
            
            # Handle tool calls (streaming format - they come in chunks)
            if hasattr(chunk.choices[0].delta, 'tool_calls') and chunk.choices[0].delta.tool_calls:
                for tool_call_delta in chunk.choices[0].delta.tool_calls:
                    index = tool_call_delta.index
                    
                    # Initialize tool call if not exists
                    if index not in collected_tool_calls:
                        collected_tool_calls[index] = {
                            'id': '',
                            'type': 'function',
                            'function': {
                                'name': '',
                                'arguments': ''
                            },
                            'extra_content': None  # For Gemini 3 thought signatures
                        }
                    
                    # Accumulate tool call data
                    if tool_call_delta.id:
                        collected_tool_calls[index]['id'] = tool_call_delta.id
                    
                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            collected_tool_calls[index]['function']['name'] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            collected_tool_calls[index]['function']['arguments'] += tool_call_delta.function.arguments
                    
                    # Capture extra_content for Gemini 3 thought signatures (OpenAI compat format)
                    # The thought signature comes in extra_content.google.thought_signature
                    if hasattr(tool_call_delta, 'extra_content') and tool_call_delta.extra_content:
                        collected_tool_calls[index]['extra_content'] = tool_call_delta.extra_content
                        logger.info(f"[GEMINI-DEBUG] Captured extra_content for tool call {index}")
                    # Also try to get it from model_dump if direct access doesn't work
                    elif chunk_dict:
                        try:
                            for choice in chunk_dict.get('choices', []):
                                delta = choice.get('delta', {})
                                for tc in delta.get('tool_calls', []):
                                    if tc.get('index') == index and tc.get('extra_content'):
                                        collected_tool_calls[index]['extra_content'] = tc['extra_content']
                                        logger.info(f"[GEMINI-DEBUG] Captured extra_content from model_dump for tool call {index}")
                        except Exception as e:
                            logger.debug(f"[GEMINI-DEBUG] Could not extract extra_content from model_dump: {e}")
        
        # Convert collected tool calls to list format
        # For Gemini models, we must include the provider-specific extra_content.google.thought_signature
        # field on each tool call when sending tool results back. Other providers do not
        # understand this field, so we only attach it when the model name indicates Gemini.
        model_name_lower = (self.model_name or "").lower()
        is_gemini_model = model_name_lower.startswith("gemini-")

        tool_calls_list = []
        for index in sorted(collected_tool_calls.keys()):
            tc = collected_tool_calls[index]
            tool_call_entry = {
                "id": tc['id'],
                "type": "function",
                "function": {
                    "name": tc['function']['name'],
                    "arguments": tc['function']['arguments']
                }
            }

            extra_content = tc.get('extra_content')
            if extra_content:
                # Always log for debugging
                logger.info(f"[GEMINI-DEBUG] Tool call {index} has extra_content")

                # Only send extra_content back to the API for Gemini models, where
                # thought signatures are required for tool calls.
                if is_gemini_model:
                    tool_call_entry['extra_content'] = extra_content
                    logger.info(f"[GEMINI-DEBUG] Including extra_content on tool call {index} for Gemini model {self.model_name}")

            tool_calls_list.append(tool_call_entry)
        
        # Enhanced debug logging - log finish reason and thought signature presence
        logger.info(
            f"[GEMINI-DEBUG] Stream processing complete | "
            f"finish_reason={finish_reason} | "
            f"chunks={len(collected_chunks)} | "
            f"tool_calls={len(tool_calls_list)} | "
            f"thought_signatures_seen={thought_signature_seen} | "
            f"parts_with_signatures={len(parts_with_signatures)} | "
            f"total_parts={total_parts_count} | "
            f"vendor_parts_collected={len(vendor_parts)}"
        )
        
        return collected_chunks, tool_calls_list, finish_reason, vendor_parts
    
    def _sanitize_tool_result_for_llm(self, tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize tool results before sending to LLM.
        
        Removes large binary data (like base64 images) that would:
        1. Waste tokens
        2. Cause API errors with providers that don't support binary data
        
        Args:
            tool_name: Name of the tool that was executed
            result: Raw tool result
            
        Returns:
            Sanitized result safe for LLM consumption
        """
        # For image generation, keep lightweight reference data (already optimized)
        # New streaming-optimized format already excludes large imageData
        if tool_name == 'generate_image' and result.get('success'):
            data = result.get('data', {})
            
            # Check if it's the new streaming-optimized format (has imageReference)
            if 'imageReference' in data:
                # Keep lightweight reference for LLM context
                # IMPORTANT: Do NOT include imageData here - LLM should use imageUrl (file://) for editing
                # imageData (thumbnail) is only for frontend widget display
                
                # Log to track path discrepancies
                ref_abs_path = (data.get('imageReference') or {}).get('absolute_path') if isinstance(data.get('imageReference'), dict) else None
                tool_abs_path = data.get('absolutePath')
                if ref_abs_path != tool_abs_path:
                    logger.info(
                        f"[ToolResultFormatter] Path mismatch detected: "
                        f"imageReference.absolute_path={ref_abs_path}, "
                        f"tool absolutePath={tool_abs_path}"
                    )
                
                sanitized = {
                    "success": True,
                    "data": {
                        "imageReference": data.get('imageReference'),  # Lightweight reference metadata
                        "imageUrl": data.get('imageUrl'),  # file:// URL for agent editing (REQUIRED for edit mode)
                        "absolutePath": data.get('absolutePath'),  # CRITICAL: Actual save path (may differ from imageReference path)
                        "filePath": data.get('filePath'),  # Relative path for display
                        "message": data.get('message', 'Image generated successfully'),
                        "prompt": data.get('prompt', ''),
                        "model": data.get('model', ''),
                        "timestamp": data.get('timestamp', ''),
                        "mode": data.get('mode'),
                        "size": data.get('size'),
                        "width": data.get('width'),
                        "height": data.get('height'),
                        "context": data.get('context'),
                        "contextHost": data.get('contextHost')
                        # Intentionally omit imageData, thumbnailUrl, fullImageUrl - not needed by LLM
                        # These URLs are in the unsanitized version sent to frontend widget
                    }
                }
                
                logger.info(f"[ToolResultFormatter] Sanitized image result: absolutePath={sanitized['data'].get('absolutePath')}")
                
                return sanitized
            else:
                # Legacy format - strip out large base64 data
                sanitized = {
                    "success": True,
                    "data": {
                        "message": data.get('message', 'Image generated successfully'),
                        "prompt": data.get('prompt', ''),
                        "filePath": data.get('filePath', ''),
                        "model": data.get('model', ''),
                        "timestamp": data.get('timestamp', '')
                        # Intentionally omit imageData, imageUrl to keep response small
                    }
                }
            return sanitized
        
        # For other tools, return as-is
        return result
    
    def _handle_tool_calls(self, messages: List[Dict], collected_chunks: List[str], 
                          tool_calls_list: List[Dict]) -> AsyncGenerator[str, None]:
        """
        Handle execution of tool calls and add results to conversation.
        """
        yield "\n\n🔧 **Executing tools...**\n"
        
        # Add assistant message with tool calls to conversation
        # Per OpenAI API spec: when tool_calls are present, content should be null or empty
        # Moonshot K2.5 strictly enforces this - content must not have text when tool_calls exist
        assistant_message = {
            "role": "assistant",
            "content": None,  # Must be null when tool_calls are present
            "tool_calls": tool_calls_list
        }
        messages.append(assistant_message)
        
        # Execute each tool call
        for tc in tool_calls_list:
            try:
                tool_name = tc['function']['name']
                arguments_str = tc['function']['arguments']
                
                # Validate that we have a tool name
                if not tool_name:
                    yield f"❌ **Error**: Tool name is empty\n"
                    # Still add error response to conversation
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tc.get('id', 'unknown'),
                        "content": json.dumps({"error": "Tool name is empty"})
                    }
                    messages.append(tool_message)
                    continue
                
                # Parse arguments safely
                try:
                    arguments = json.loads(arguments_str) if arguments_str else {}
                except json.JSONDecodeError as e:
                    yield f"❌ **Error**: Invalid JSON arguments for {tool_name}: {str(e)}\n"
                    # Still add error response to conversation
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tc.get('id', 'unknown'),
                        "content": json.dumps({"error": f"Invalid JSON arguments: {str(e)}"})
                    }
                    messages.append(tool_message)
                    continue
                
                # Debug logging for image generation tool calls
                if tool_name == 'generate_image':
                    logger.info(f"🎨 Image generation tool call - aspect_ratio: {arguments.get('aspect_ratio', 'NOT SET')}, "
                              f"mode: {arguments.get('mode', 'NOT SET')}, image_data: {bool(arguments.get('image_data'))}")
                
                # Show tool call start
                yield self.formatter.format_tool_call_start(tool_name, arguments)
                
                # Execute the tool
                result = self.tool_executor.execute_tool_call_sync(tool_name, arguments)
                
                # Log tool execution to debug interceptor (non-blocking)
                if self.debug_interceptor:
                    try:
                        async def _log_tool():
                            try:
                                await self.debug_interceptor.log_tool_execution(tool_name, arguments, result)
                            except Exception as e:
                                logger.debug(f"Failed to log tool execution: {e}")
                        asyncio.create_task(_log_tool())
                    except Exception as e:
                        logger.debug(f"Failed to create log task: {e}")
                
                # Format and display result - yield in smaller chunks for large responses
                formatted_result = self.formatter.format_tool_result(tool_name, result)
                
                # For large responses (>1KB), stream in chunks to avoid WebSocket/buffer truncation
                if len(formatted_result) > 1024:
                    chunk_size = 1024  # 1KB chunks
                    total_chunks = (len(formatted_result) + chunk_size - 1) // chunk_size
                    logger.info(f"Streaming large tool result in {total_chunks} chunks ({len(formatted_result)} chars total)")
                    for i in range(0, len(formatted_result), chunk_size):
                        chunk = formatted_result[i:i+chunk_size]
                        logger.debug(f"Yielding chunk {i//chunk_size + 1}/{total_chunks}: {len(chunk)} chars")
                        yield chunk
                    logger.info(f"Finished streaming {total_chunks} chunks for {tool_name}")
                else:
                    yield formatted_result
                
                # Sanitize result for LLM (remove large binary data like images)
                sanitized_result = self._sanitize_tool_result_for_llm(tool_name, result)
                
                # Add tool result to conversation
                # OpenAI expects the tool content to be the data payload, not the wrapper object
                tool_content = sanitized_result.get('data') if sanitized_result.get('success') else {
                    "error": sanitized_result.get('error', 'Unknown error')
                }
                
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tc['id'],
                    "content": json.dumps(tool_content)
                }
                messages.append(tool_message)
                
            except Exception as e:
                error_msg = f"❌ **Tool Error**: {str(e)}\n"
                yield error_msg
                logger.error(f"Tool execution error: {e}")
                
                # Add error to conversation
                tool_message = {
                    "role": "tool", 
                    "tool_call_id": tc.get('id', 'unknown'),
                    "content": json.dumps({"success": False, "error": str(e)})
                }
                messages.append(tool_message)


def create_agent_chat_function(agent_name: str, system_prompt: str, model_name: str):
    """
    Factory function to create a standardized chat function for agents.
    
    This helper creates a complete chat function with tool support, streaming,
    and proper error handling. Custom agents can use this to avoid boilerplate.
    
    Args:
        agent_name: Name of the agent for logging
        system_prompt: System prompt for the agent
        model_name: OpenAI model name to use
        
    Returns:
        Chat function that can be used as the main agent entry point
    """
    def chat(message: str, history):
        """
        Generated chat function with tool integration and streaming.
        
        Args:
            message: str - User message
            history: List[Dict] or str (JSON) - Conversation history
            
        Yields:
            str - Response chunks for streaming
        """
        # Import here to avoid circular imports
        from .clients import get_openai_client
        
        try:
            client = get_openai_client()
        except Exception as e:
            yield f"🚫 OpenAI client not available. Please check your OPENAI_API_KEY configuration."
            return
        
        try:
            # Handle JSON string history (gradio compatibility)
            if isinstance(history, str):
                history = json.loads(history)
            
            # Build conversation messages
            system_message = {"role": "system", "content": system_prompt}
            messages = [system_message] + history + [{"role": "user", "content": message}]
            
            # Create streaming handler and process
            handler = OpenAIStreamingHandler(client, model_name)
            
            logger.info(f"{agent_name}: Starting chat with tools")
            yield from handler.stream_chat_with_tools(messages)
            logger.info(f"{agent_name}: Chat completed successfully")
                    
        except Exception as e:
            logger.error(f"Error in {agent_name} streaming: {e}")
            yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenAI API key configuration."
    
    return chat


# Convenience functions for common agent patterns
def get_available_tools_summary() -> str:
    """Get a formatted summary of available tools for agent system prompts."""
    loader = ToolDefinitionLoader()
    tools = loader.get_openai_tools()
    
    if not tools:
        return "No tools available."
    
    summary = ""
    for i, tool in enumerate(tools, 1):
        func = tool['function']
        summary += f"{i}. **{func['name']}** - {func['description']}\n"
    
    return summary.rstrip()  # Remove trailing newline


def validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate tool arguments against the tool's parameter schema.
    
    Args:
        tool_name: Name of the tool
        arguments: Arguments to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        registry = get_tool_registry()
        tool = registry.get(tool_name)
        
        if not tool:
            return False, f"Tool {tool_name} not found"
        
        # Get required parameters from tool definition
        params = tool.to_openai_function().get('parameters', {})
        required = params.get('required', [])
        
        # Check required parameters are present
        for req_param in required:
            if req_param not in arguments:
                return False, f"Required parameter '{req_param}' missing"
        
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def create_simple_agent_chat_function(agent_name: str, system_prompt: str, model_name: str, 
                                    custom_tools: Optional[List[Dict]] = None,
                                    custom_tool_executor: Optional[Callable] = None):
    """
    Factory function to create a standardized chat function for simple agents.
    
    This is useful for agents that don't use the full tool registry but have their own
    custom tools (like personal_agent with its pushover tools).
    
    Args:
        agent_name: Name of the agent for logging
        system_prompt: System prompt for the agent
        model_name: OpenAI model name to use
        custom_tools: Optional list of custom tool definitions in OpenAI format
        custom_tool_executor: Optional custom tool executor function
        
    Returns:
        Chat function that can be used as the main agent entry point
    """
    def chat(message: str, history):
        """
        Generated chat function with optional custom tool integration.
        
        Args:
            message: str - User message
            history: List[Dict] or str (JSON) - Conversation history
            
        Yields:
            str - Response chunks for streaming
        """
        # Import here to avoid circular imports
        from .clients import get_openai_client
        
        try:
            client = get_openai_client()
        except Exception as e:
            yield f"🚫 OpenAI client not available. Please check your OPENAI_API_KEY configuration."
            return
        
        try:
            # Handle JSON string history (gradio compatibility)
            if isinstance(history, str):
                history = json.loads(history)
            
            # Build conversation messages
            system_message = {"role": "system", "content": system_prompt}
            messages = [system_message] + history + [{"role": "user", "content": message}]
            
            if custom_tools and custom_tool_executor:
                # Create streaming handler for custom tools
                handler = OpenAIStreamingHandler(client, model_name)
                
                # Override tool loading to use custom tools
                handler.tool_loader.get_openai_tools = lambda: custom_tools
                
                # Override tool execution to use custom executor  
                handler.tool_executor.execute_tool_call_sync = custom_tool_executor
                
                logger.info(f"{agent_name}: Starting chat with custom tools")
                yield from handler.stream_chat_with_tools(messages)
            else:
                # Simple streaming without tools
                # Determine token and continuation behavior
                try:
                    default_max_tokens = int(os.environ.get("AGENT_MAX_TOKENS", "3500"))
                except ValueError:
                    default_max_tokens = 3500

                # Determine the correct max tokens parameter based on model
                api_params = {
                    "model": model_name,
                    "messages": messages,
                    "stream": True
                }
                
                # Add the appropriate token parameter
                api_params.update(get_openai_token_param(model_name, default_max_tokens))

                stream = client.chat.completions.create(**api_params)
                
                logger.info(f"{agent_name}: Starting simple chat without tools")
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                        
            logger.info(f"{agent_name}: Chat completed successfully")
                    
        except Exception as e:
            logger.error(f"Error in {agent_name} streaming: {e}")
            yield f"🚫 Error processing request: {str(e)}\n\nPlease check your configuration."
    
    return chat


def get_model_name_for_agent(agent_name: str, fallback_model: str) -> str:
    """
    Get the model name for an agent with priority:
    1. modelName from agents.json (if configured)
    2. Fallback to the default MODEL_NAME from the agent file
    
    This allows easy model switching via agents.json without modifying agent code.
    
    Args:
        agent_name: The name of the agent (e.g., "OpenAIAgent")
        fallback_model: The default model name to use if not configured in agents.json
        
    Returns:
        The model name to use for the agent
    """
    try:
        from icpy.services.agent_config_service import get_agent_config_service
        config_service = get_agent_config_service()
        display_config = config_service.get_agent_display_config(agent_name)
        
        if display_config.model_name:
            logger.info(f"Using model from agents.json for {agent_name}: {display_config.model_name}")
            return display_config.model_name
    except Exception as e:
        logger.debug(f"Could not get model from config for {agent_name}: {e}")
    
    logger.debug(f"Using fallback model for {agent_name}: {fallback_model}")
    return fallback_model


def create_standard_agent_metadata(name: str, description: str, version: str = "1.0.0", 
                                  author: str = "ICPY Agent System", model: str = "gpt-4o-mini"):
    """
    Create standard agent metadata dictionary.
    
    Args:
        name: Agent name
        description: Agent description
        version: Agent version
        author: Agent author
        model: Default model to use
        
    Returns:
        Dictionary with standard agent metadata
    """
    return {
        "AGENT_NAME": name,
        "AGENT_DESCRIPTION": description,
        "AGENT_VERSION": version,
        "AGENT_AUTHOR": author,
        "MODEL_NAME": model,
        "AGENT_MODEL_ID": model.replace("-", "").replace(".", "").lower()
    }


def create_environment_reload_function(dependencies_to_check: List[str]):
    """
    Create a standardized reload_env function for agents.
    
    Args:
        dependencies_to_check: List of module names to check for availability
        
    Returns:
        reload_env function that can be used in agents
    """
    def reload_env():
        """Called when environment variables are reloaded"""
        available = True
        
        for dep in dependencies_to_check:
            try:
                __import__(dep)
                logger.info(f"Dependency {dep} is available after reload")
            except ImportError:
                logger.info(f"Dependency {dep} still not available after reload")
                available = False
        
        return available
    
    return reload_env


def create_agent_context(workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a comprehensive context object for agents that provides essential information
    about the current environment, time, and workspace.
    
    This function bootstraps agents with contextual information including:
    1. Current date/time with timezone
    2. Workspace root directory 
    3. System information
    4. Environment variables relevant to agent operation
    5. Available resources and capabilities
    
    Args:
        workspace_root: Optional explicit workspace root path. If not provided, 
                       will attempt to detect automatically.
    
    Returns:
        Dictionary containing comprehensive context information for agents
    """
    
    # 1. Time and date information
    now = datetime.now(timezone.utc)
    local_now = datetime.now()
    
    # 2. Workspace detection
    if workspace_root is None:
        # Try to detect workspace root automatically
        workspace_root = _detect_workspace_root()
    
    # Ensure workspace root is absolute
    if workspace_root:
        workspace_root = os.path.abspath(workspace_root)
    
    # 3. System and environment information
    system_info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "hostname": platform.node()
    }
    
    # 4. ICOTES-specific environment
    icotes_env = {
        "backend_path": os.environ.get("ICOTES_BACKEND_PATH"),
        "workspace_path": os.environ.get("ICOTES_WORKSPACE_PATH"),
        "openai_api_configured": bool(os.environ.get("OPENAI_API_KEY")),
        "agent_model_id": os.environ.get("AGENT_MODEL_ID", "gpt4o"),
        "current_working_directory": os.getcwd()
    }
    
    # 5. Tool and capability information
    try:
        registry = get_tool_registry()
        available_tools = [tool.name for tool in registry.all()]
        tool_count = len(available_tools)
    except Exception as e:
        available_tools = []
        tool_count = 0
        logger.warning(f"Could not load tool registry for context: {e}")
    
    # 6. File system context
    fs_context = {}
    if workspace_root and os.path.exists(workspace_root):
        fs_context = {
            "workspace_exists": True,
            "workspace_readable": os.access(workspace_root, os.R_OK),
            "workspace_writable": os.access(workspace_root, os.W_OK),
            "workspace_size_mb": _get_directory_size(workspace_root) / (1024 * 1024)
        }
        
        # Common project indicators
        common_files = ["package.json", "requirements.txt", "pyproject.toml", "README.md", "Dockerfile"]
        for file in common_files:
            file_path = os.path.join(workspace_root, file)
            fs_context[f"has_{file.replace('.', '_')}"] = os.path.exists(file_path)
    else:
        fs_context = {"workspace_exists": False}
    
    # Compile comprehensive context
    context = {
        # Time information
        "current_utc_time": now.isoformat(),
        "current_local_time": local_now.isoformat(), 
        "timezone_offset": local_now.strftime('%z'),
        "formatted_date": now.strftime("%A, %B %d, %Y"),
        "formatted_time": local_now.strftime("%I:%M %p %Z").strip(),
        "unix_timestamp": int(now.timestamp()),
        
        # Workspace information
        "workspace_root": workspace_root,
        "workspace_description": "The root directory where the agent should operate unless specified otherwise",
        
        # System context
        "system": system_info,
        
        # ICOTES environment
        "icotes": icotes_env,
        
        # Capabilities
        "capabilities": {
            "tools_available": tool_count > 0,
            "tool_count": tool_count,
            "available_tool_names": available_tools[:10],  # First 10 for brevity
            "openai_configured": icotes_env["openai_api_configured"],
            "file_operations": "read_file" in available_tools or "create_file" in available_tools,
            "terminal_access": "run_in_terminal" in available_tools
        },
        
        # File system context
        "filesystem": fs_context,
        
        # Context metadata
        "context_generated_at": now.isoformat(),
        "context_version": "1.0.0"
    }
    
    return context


def _detect_workspace_root() -> Optional[str]:
    """
    Attempt to automatically detect the workspace root directory.

    Resolution order (to align with FileSystemService and deployment envs):
    1) WORKSPACE_ROOT env (authoritative, set by FileSystemService/init)
    2) ICOTES_WORKSPACE_PATH env (legacy)
    3) A nearby 'workspace' directory under current or ancestor folder
    4) A detected project root (contains .git/package.json/pyproject.toml)
    5) Current working directory as last resort

    Returns:
        Detected workspace root path or None if not found
    """
    # 1) Prefer explicit WORKSPACE_ROOT set by backend initialization
    ws_env = os.environ.get("WORKSPACE_ROOT")
    if ws_env:
        return ws_env

    # 2) Legacy env var support
    legacy_env = os.environ.get("ICOTES_WORKSPACE_PATH")
    if legacy_env:
        return legacy_env

    # 3) Try to find a nearby 'workspace' directory
    current_dir = os.getcwd()

    # If we're already in a directory named 'workspace'
    if os.path.basename(current_dir) == "workspace":
        return current_dir

    # Look up the directory tree for a 'workspace' subdirectory
    check_dir = current_dir
    for _ in range(5):  # Limit search depth
        workspace_path = os.path.join(check_dir, "workspace")
        if os.path.isdir(workspace_path):
            return workspace_path

        # Check parent directory for workspace/ too
        parent = os.path.dirname(check_dir)
        if parent != check_dir:  # Not at filesystem root yet
            parent_workspace = os.path.join(parent, "workspace")
            if os.path.isdir(parent_workspace):
                return parent_workspace

        # 4) Detect common project roots if no explicit workspace dir
        root_indicators = [".git", "package.json", "pyproject.toml"]
        if any(os.path.exists(os.path.join(check_dir, indicator)) for indicator in root_indicators):
            # Use the project root as workspace base when no 'workspace' dir present
            return check_dir

        if parent == check_dir:  # Reached filesystem root
            break
        check_dir = parent

    # 5) Default fallback: current working directory
    return current_dir


def get_workspace_path() -> str:
    """
    Get the workspace directory path for saving files.
    
    This is the recommended way for agents to get the workspace path for saving
    generated files (images, documents, etc.).
    
    Returns:
        Absolute path to the workspace directory
    """
    workspace_root = _detect_workspace_root()
    if workspace_root:
        return os.path.abspath(workspace_root)
    
    # Fallback: use current directory if detection fails
    return os.getcwd()


def _get_directory_size(directory: str) -> int:
    """
    Calculate the total size of a directory in bytes.
    
    Args:
        directory: Directory path to calculate size for
        
    Returns:
        Size in bytes (0 if error or inaccessible)
    """
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    continue  # Skip files we can't access
        return total_size
    except Exception:
        return 0


def format_agent_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Format the agent context dictionary into a human-readable string 
    suitable for inclusion in agent system prompts.
    
    Args:
        context: Context dictionary from create_agent_context()
        
    Returns:
        Formatted string describing the current context
    """
    workspace_info = f"**Workspace Root**: `{context['workspace_root']}`" if context['workspace_root'] else "**Workspace**: Not detected"
    
    # Add explicit workspace structure information
    if context['workspace_root']:
        workspace_info += """
 - **Agent Files**: `<workspace_root>/.icotes/plugins/<AGENT_NAME>_agent.py`
 - **Configuration**: `<workspace_root>/.icotes/agents.json`
 - **Structure**: Use existing `.icotes/plugins/` directory, do NOT create additional subdirectories"""
    
    time_info = f"**Current Time**: {context['formatted_date']} at {context['formatted_time']}"
    
    capabilities = context['capabilities']
    caps_info = f"**Available Capabilities**: {capabilities['tool_count']} tools available"
    if capabilities['available_tool_names']:
        caps_info += f" (including: {', '.join(capabilities['available_tool_names'])})"
    
    system_info = f"**System**: {context['system']['platform']} {context['system']['architecture']}"
    
    # Include hop context if present
    hop_context_str = context.get('hop_context', '')
    
    return f"""
## Agent Context Information

{time_info}

{hop_context_str}

{workspace_info if not hop_context_str else ''}

{caps_info}

{system_info}

**Environment**: ICOTES Agent Framework with OpenAI API {"✓ configured" if context['icotes']['openai_api_configured'] else "✗ not configured"}
"""


def add_context_to_agent_prompt(base_prompt: str, workspace_root: Optional[str] = None) -> str:
    """
    Convenience function to add context information to an existing agent system prompt.
    
    Includes dynamic hop context information so agent knows current workspace location.
    Works in both sync and async contexts by using asyncio.
    
    Args:
        base_prompt: The original system prompt
        workspace_root: Optional workspace root override
        
    Returns:
        Enhanced system prompt with context information
    """
    context = create_agent_context(workspace_root)
    
    # Add dynamic hop context information
    # This needs to be async, so we handle it carefully
    try:
        import asyncio
        from .tools.context_helpers import get_current_context
        
        # Try to get current event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, but this function is sync
            # Create a task and run it
            import concurrent.futures
            import threading
            
            def get_context_sync():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(get_current_context())
                finally:
                    new_loop.close()
            
            # Run in thread pool to avoid blocking
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(get_context_sync)
                hop_context = future.result(timeout=2)  # 2 second timeout
        except RuntimeError:
            # No event loop running, we can safely create one
            hop_context = asyncio.run(get_current_context())
        
        context_id = hop_context.get('contextId', 'local')
        is_hopped = context_id != 'local' and hop_context.get('status') == 'connected'
        
        if is_hopped:
            # Agent is in a remote hop context
            # Prefer friendly credential name when available for namespace label
            friendly = hop_context.get('credentialName') or hop_context.get('credential_name') or context_id
            hop_info = f"""
**Current Context**: Hopped to remote server
- Context ID: `{context_id}` (namespace: `{friendly}`)
- Host: `{hop_context.get('host', 'unknown')}`
- Username: `{hop_context.get('username', 'unknown')}`
- Current Directory: `{hop_context.get('cwd', '/')}`
- **Active Workspace Root**: `{hop_context.get('cwd', '/')}` ⚠️ Use this for file operations!

**Important**: When working with files (saving images, creating files, etc.), use the active workspace root shown above, NOT the local workspace path. All file operations will be executed on the remote server.
"""
            context['hop_context'] = hop_info
        else:
            # Local context
            context['hop_context'] = f"""
**Current Context**: Local (no hop active)
- **Active Workspace Root**: `{context['workspace_root']}`
"""
    except Exception as e:
        logger.warning(f"Failed to get hop context for agent prompt: {e}")
        context['hop_context'] = ""
    
    context_section = format_agent_context_for_prompt(context)
    
    # Add a compact namespace notation reminder for the LLM
    ns_reminder = (
        "\n\n### Namespace notation quick guide\n"
        "Use `<namespace>:/absolute/path` when you need to be explicit. If omitted, the active context applies. "
        "Show namespaced paths back to the user using the `pathInfo.formatted_path` when available."
    )

    return f"{base_prompt}\n\n{context_section}{ns_reminder}"
