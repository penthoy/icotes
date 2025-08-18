"""
Personal Agent - Tool Use Proof of Concept

This is a demonstration agent showcasing tool use capabilities.
It serves as a POC for how agents can use tools and will be replaced
by real tool use agents in the future.
"""

import json
import os

from .clients import get_openai_client
from .tools.pushover_tools import push


def record_user_details(email, name="Name not provided", notes="not provided"):
    """Record user contact details when they express interest in getting in touch"""
    push(f"[DEMO] Recording contact from {name} (email: {email}) - Notes: {notes}")
    return {"status": "recorded", "message": f"Contact information saved for {name}"}

def record_unknown_question(question):
    """Log questions that the agent cannot answer for future improvement"""
    push(f"[DEMO] Unknown question logged: {question}")
    return {"status": "logged", "message": "Question has been recorded for review"}

def get_tools():
    """Define the tools available to the Personal Assistant demo agent"""
    record_user_details_json = {
        "name": "record_user_details",
        "description": "Record user contact information when they express interest in getting in touch or want to be contacted",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The user's email address"
                },
                "name": {
                    "type": "string",
                    "description": "The user's name, if provided"
                },
                "notes": {
                    "type": "string",
                    "description": "Any relevant context or notes about the user's interest or conversation"
                }
            },
            "required": ["email"],
            "additionalProperties": False
        }
    }

    record_unknown_question_json = {
        "name": "record_unknown_question",
        "description": "Log any question that you cannot answer for future improvement and review",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question that could not be answered"
                }
            },
            "required": ["question"],
            "additionalProperties": False
        }
    }

    tools = [
        {"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}
    ]
    return tools

# This function can take a list of tool calls, and run them. This is the IF statement!!

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)

        # THE BIG IF STATEMENT!!!

        if tool_name == "record_user_details":
            result = record_user_details(**arguments)
        elif tool_name == "record_unknown_question":
            result = record_unknown_question(**arguments)

        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
    return results

# This is a more elegant way that avoids the IF statement.

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else {}
        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
    return results


def get_system_prompt():
    """Get the system prompt for the Personal Assistant demo agent"""
    system_prompt = """You are a Personal Assistant AI, designed to demonstrate tool use capabilities.

This is a proof-of-concept agent that showcases how AI agents can use tools to:
1. Record user contact information when they express interest
2. Log questions that you cannot answer for future improvement

Key behaviors:
- Be helpful and professional in your responses
- When users show interest in getting in touch, ask for their email and use the record_user_details tool
- If you encounter questions you cannot answer, use the record_unknown_question tool to log them
- Try to be engaging and demonstrate the tool use capabilities naturally in conversation

Available tools:
- record_user_details: Records user contact information
- record_unknown_question: Logs questions you cannot answer

This is a demonstration agent and will be replaced by more sophisticated tool use agents in the future."""
    
    return system_prompt


def chat(message, history):
    """Streaming chat function with tool support for real-time responses"""
    if isinstance(history, str):
        history = json.loads(history)
    messages = [{"role": "system", "content": get_system_prompt()}] + history + [{"role": "user", "content": message}]

    done = False
    while not done:
        client = get_openai_client()
        
        # Use streaming for the main response
        stream = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=messages, 
            tools=get_tools(),
            stream=True
        )
        
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
            if chunk.choices[0].delta.tool_calls:
                for tool_call_delta in chunk.choices[0].delta.tool_calls:
                    # Initialize new tool call if needed
                    while tool_call_delta.index >= len(collected_tool_calls):
                        collected_tool_calls.append({
                            "id": "",
                            "function": {"name": "", "arguments": ""}
                        })
                    
                    # Update tool call data
                    if tool_call_delta.id:
                        collected_tool_calls[tool_call_delta.index]["id"] = tool_call_delta.id
                    if tool_call_delta.function and tool_call_delta.function.name:
                        collected_tool_calls[tool_call_delta.index]["function"]["name"] = tool_call_delta.function.name
                    if tool_call_delta.function and tool_call_delta.function.arguments:
                        collected_tool_calls[tool_call_delta.index]["function"]["arguments"] += tool_call_delta.function.arguments
        
        # If tool calls were made, execute them
        if collected_tool_calls and finish_reason == "tool_calls":
            yield f"\n[Processing tools...]"
            
            # Create a proper message object for tool calls
            class ToolCall:
                def __init__(self, id, function_name, arguments):
                    self.id = id
                    self.function = type('Function', (), {'name': function_name, 'arguments': arguments})()
            
            tool_calls = [ToolCall(tc["id"], tc["function"]["name"], tc["function"]["arguments"]) 
                         for tc in collected_tool_calls]
            
            # Handle the tool calls
            results = handle_tool_calls(tool_calls)
            
            # Add assistant message with tool calls to conversation
            # Format tool_calls properly for OpenAI API (requires "type": "function")
            formatted_tool_calls = []
            for tc in collected_tool_calls:
                formatted_tool_calls.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                })
            
            assistant_message = {
                "role": "assistant", 
                "content": ''.join(collected_chunks),
                "tool_calls": formatted_tool_calls
            }
            messages.append(assistant_message)
            messages.extend(results)
            
            yield f"\n[Tools processed, generating response...]"
        else:
            done = True

if __name__ == "__main__":
    # Test the tool use demo agent
    print("Testing Personal Assistant tool use demo...")
    result = chat("Hi, I'm interested in learning more about tool use capabilities. Can you help?", "[]")
    for chunk in result:
        print(chunk, end='', flush=True)
    print("\n")