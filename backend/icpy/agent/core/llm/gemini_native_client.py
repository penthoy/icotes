"""
Native Gemini SDK client adapter for tool calling with automatic thought signature handling.

Uses the google-genai SDK directly instead of the OpenAI compatibility layer.
This properly handles Gemini 3's thought signatures automatically.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Generator, Iterable, List, Optional

from .base import BaseLLMClient, ProviderNotConfigured, ProviderError

logger = logging.getLogger(__name__)


def _get_native_gemini_client():
    """Get the native google-genai client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ProviderNotConfigured("GOOGLE_API_KEY environment variable is not set.")
    
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError as e:
        raise ProviderNotConfigured(
            "google-genai SDK is not installed. Install it with: pip install google-genai"
        ) from e


def _convert_openai_tools_to_gemini(openai_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert OpenAI-format tool definitions to Gemini function declarations.
    
    OpenAI format:
    {
        "type": "function",
        "function": {
            "name": "...",
            "description": "...",
            "parameters": {...}
        }
    }
    
    Gemini format (function declaration):
    {
        "name": "...",
        "description": "...",
        "parameters": {...}
    }
    """
    function_declarations = []
    for tool in openai_tools:
        if tool.get("type") == "function" and "function" in tool:
            func = tool["function"]
            function_declarations.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {})
            })
    return function_declarations


def _convert_messages_to_gemini_contents(
    messages: List[Dict[str, Any]],
    system_instruction: Optional[str] = None
) -> List[Any]:
    """
    Convert OpenAI-format messages to Gemini contents format.
    
    Returns a list suitable for passing to client.models.generate_content().
    System messages are extracted separately since Gemini handles them differently.
    """
    from google.genai import types
    
    contents = []
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            # System messages are handled via system_instruction config, skip here
            continue
        elif role == "user":
            # Handle multimodal content
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            parts.append(types.Part(text=part.get("text", "")))
                        elif part.get("type") == "image_url":
                            # Handle image URLs - for now just include as text reference
                            # Full image support would need more complex handling
                            image_url = part.get("image_url", {}).get("url", "")
                            if image_url.startswith("data:"):
                                # Base64 image - extract and include
                                try:
                                    import base64
                                    # Parse data URL: data:mime;base64,data
                                    header, b64_data = image_url.split(",", 1)
                                    mime_type = header.split(":")[1].split(";")[0]
                                    image_bytes = base64.b64decode(b64_data)
                                    parts.append(types.Part.from_bytes(
                                        data=image_bytes,
                                        mime_type=mime_type
                                    ))
                                except Exception as e:
                                    logger.warning(f"Failed to parse image data URL: {e}")
                                    parts.append(types.Part(text=f"[Image: {image_url[:50]}...]"))
                            else:
                                # URL reference
                                parts.append(types.Part(text=f"[Image URL: {image_url}]"))
                    elif isinstance(part, str):
                        parts.append(types.Part(text=part))
                contents.append(types.Content(role="user", parts=parts))
            else:
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=str(content))]
                ))
        elif role == "assistant":
            # Check for tool calls in assistant message
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                parts = []
                if content:
                    parts.append(types.Part(text=str(content)))
                for tc in tool_calls:
                    if tc.get("type") == "function":
                        func = tc.get("function", {})
                        try:
                            args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            args = {}
                        parts.append(types.Part.from_function_call(
                            name=func.get("name", ""),
                            args=args
                        ))
                contents.append(types.Content(role="model", parts=parts))
            else:
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part(text=str(content) if content else "")]
                ))
        elif role == "tool":
            # Tool result - create function response
            tool_call_id = msg.get("tool_call_id", "")
            tool_content = msg.get("content", "")
            
            # Try to parse JSON content
            try:
                result_data = json.loads(tool_content) if tool_content else {}
            except json.JSONDecodeError:
                result_data = {"result": tool_content}
            
            # We need the function name from the tool_call_id or context
            # For now, use a placeholder - the SDK should handle matching
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_function_response(
                    name=tool_call_id,  # Will be matched by SDK
                    response={"result": result_data}
                )]
            ))
    
    return contents


class GeminiNativeClientAdapter(BaseLLMClient):
    """
    Native Gemini SDK adapter that handles tool calling with automatic thought signature management.
    
    This adapter uses the google-genai SDK directly, which automatically handles:
    - Thought signatures for multi-turn conversations
    - Function calling with proper response formatting
    - Streaming with thinking support
    """
    
    def __init__(self):
        self._client = None
        self._tool_registry = None
    
    def _get_client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            self._client = _get_native_gemini_client()
        return self._client
    
    def _get_tool_registry(self):
        """Get the tool registry for executing tools."""
        if self._tool_registry is None:
            try:
                from ...tools import get_tool_registry
                self._tool_registry = get_tool_registry()
            except Exception as e:
                logger.warning(f"Failed to load tool registry: {e}")
                self._tool_registry = None
        return self._tool_registry
    
    def stream_chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterable[str]:
        """
        Stream chat completions using the native Gemini SDK.
        
        Handles tool calling automatically with thought signature support.
        """
        try:
            from google.genai import types
        except ImportError as e:
            raise ProviderNotConfigured(
                "google-genai SDK is not installed. Install it with: pip install google-genai"
            ) from e
        
        client = self._get_client()
        
        # Extract system instruction from messages
        system_instruction = None
        for msg in messages:
            if msg.get("role") == "system":
                system_instruction = msg.get("content", "")
                break
        
        # Convert messages to Gemini format
        contents = _convert_messages_to_gemini_contents(messages, system_instruction)
        
        # Build configuration
        config_kwargs = {}
        
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        
        # Add tools if provided
        gemini_tools = None
        if tools:
            function_declarations = _convert_openai_tools_to_gemini(tools)
            if function_declarations:
                gemini_tools = [types.Tool(function_declarations=function_declarations)]
                config_kwargs["tools"] = gemini_tools
                # Disable automatic function calling - we handle it ourselves
                # Note: When disable=True, don't set maximum_remote_calls
                config_kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(
                    disable=True,
                    maximum_remote_calls=None
                )
        
        # Thinking configuration for Gemini 3
        # Note: ThinkingConfig only accepts include_thoughts (bool), not thinking_level
        include_thoughts = os.getenv("GEMINI_INCLUDE_THOUGHT_SUMMARIES", "false").lower() in ("true", "1")
        if model.startswith("gemini-3"):
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                include_thoughts=include_thoughts
            )
        
        config = types.GenerateContentConfig(**config_kwargs)
        
        # Use the chat interface for multi-turn with automatic thought signature handling
        logger.info(f"[GEMINI-NATIVE] Starting chat with model={model}, tools={len(tools) if tools else 0}")
        
        # Create a generator that handles the conversation loop
        yield from self._run_conversation_loop(
            client=client,
            model=model,
            contents=contents,
            config=config,
            tools=tools
        )
    
    def _run_conversation_loop(
        self,
        client,
        model: str,
        contents: List,
        config,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tool_rounds: int = 10
    ) -> Generator[str, None, None]:
        """
        Run the conversation loop, handling tool calls and responses.
        
        The native SDK automatically handles thought signatures when we use
        the chat interface and pass back the complete response.
        """
        from google.genai import types
        
        tool_round = 0
        current_contents = list(contents)
        
        while tool_round < max_tool_rounds:
            tool_round += 1
            
            logger.info(f"[GEMINI-NATIVE] API call round {tool_round}, contents={len(current_contents)}")
            
            try:
                # Use streaming for text output
                response_text = ""
                function_calls = []
                model_response_content = None
                
                # Stream the response
                for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=current_contents,
                    config=config
                ):
                    # Process each chunk
                    if chunk.candidates:
                        candidate = chunk.candidates[0]
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                # Check for text content
                                if hasattr(part, 'text') and part.text:
                                    yield part.text
                                    response_text += part.text
                                
                                # Check for function calls
                                if hasattr(part, 'function_call') and part.function_call:
                                    function_calls.append(part.function_call)
                            
                            # Keep the full response content for conversation history
                            model_response_content = candidate.content
                
                # If no function calls, we're done
                if not function_calls:
                    logger.info(f"[GEMINI-NATIVE] Conversation complete, no more function calls")
                    break
                
                # Handle function calls
                logger.info(f"[GEMINI-NATIVE] Processing {len(function_calls)} function call(s)")
                yield "\n\n🔧 **Executing tools...**\n"
                
                # Add the model's response to conversation history
                # CRITICAL: This preserves thought signatures automatically
                if model_response_content:
                    current_contents.append(model_response_content)
                
                # Execute each function call and collect results
                function_responses = []
                for fc in function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}
                    
                    # Use proper format that frontend parser expects
                    # Format: 📋 **tool_name**: {args}
                    args_str = json.dumps(tool_args) if tool_args else "{}"
                    yield f"\n📋 **{tool_name}**: {args_str}\n"
                    
                    # Execute the tool
                    result = self._execute_tool(tool_name, tool_args)
                    
                    # Format result using proper format for frontend widgets
                    # Format: ✅ **Success**: result or ❌ **Error**: error
                    if result.get("success"):
                        data = result.get('data', 'Operation completed')
                        # For JSON-serializable data, include it
                        if isinstance(data, dict):
                            try:
                                data_str = json.dumps(data)
                            except:
                                data_str = str(data)
                        else:
                            data_str = str(data) if data else 'Operation completed'
                        # Truncate very long results
                        if len(data_str) > 500:
                            data_str = data_str[:500] + "... (truncated)"
                        yield f"✅ **Success**: {data_str}\n"
                    else:
                        yield f"❌ **Error**: {result.get('error', 'Unknown error')}\n"
                    
                    # Create function response part
                    function_responses.append(types.Part.from_function_response(
                        name=tool_name,
                        response={"result": result}
                    ))
                
                # Add function responses to conversation
                current_contents.append(types.Content(
                    role="user",
                    parts=function_responses
                ))
                
                yield "\n🔧 **Tool execution complete. Continuing...**\n\n"
                
            except Exception as e:
                logger.error(f"[GEMINI-NATIVE] Error in conversation loop: {e}", exc_info=True)
                yield f"\n🚫 Error: {str(e)}\n"
                break
        
        if tool_round >= max_tool_rounds:
            logger.warning(f"[GEMINI-NATIVE] Reached max tool rounds ({max_tool_rounds})")
            yield "\n⚠️ Reached maximum tool-call attempts. Stopping to prevent a loop.\n"
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        import asyncio
        import inspect
        
        registry = self._get_tool_registry()
        
        if registry is None:
            return {"success": False, "error": "Tool registry not available"}
        
        tool = registry.get(tool_name)
        if tool is None:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}
        
        try:
            # Execute the tool
            result = tool.execute(**arguments)
            
            # Handle coroutines (async tools)
            if inspect.iscoroutine(result):
                try:
                    # Try to get existing event loop
                    loop = asyncio.get_running_loop()
                    # If we're in an async context, we need to run in a thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, result)
                        result = future.result(timeout=60)
                except RuntimeError:
                    # No running loop, safe to use asyncio.run()
                    result = asyncio.run(result)
            
            # Handle ToolResult objects
            if hasattr(result, 'success'):
                return {
                    "success": result.success,
                    "data": result.data if hasattr(result, 'data') else None,
                    "error": result.error if hasattr(result, 'error') else None
                }
            
            # Handle dict results
            if isinstance(result, dict):
                return result
            
            # Wrap other results
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return {"success": False, "error": str(e)}
