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
from .helpers import (
    create_simple_agent_chat_function, 
    create_standard_agent_metadata,
)

# Agent metadata using helper
AGENT_METADATA = create_standard_agent_metadata(
    name="PersonalAgent",
    description="Personal Assistant with tool use capabilities",
    version="2.0.0",
    author="icotes"
)


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

# Tool call functions have been replaced by the helper classes in helpers.py
# The OpenAIStreamingHandler handles tool execution automatically


def get_system_prompt():
    """Get a STABLE system prompt for the Personal Assistant demo agent (no dynamic context)."""
    base_prompt = (
        "You are a Personal Assistant AI, designed to demonstrate tool use capabilities.\n\n"
        "This is a proof-of-concept agent that showcases how AI agents can use tools to:\n"
        "1. Record user contact information when they express interest\n"
        "2. Log questions that you cannot answer for future improvement\n\n"
        "Key behaviors:\n"
        "- Be helpful and professional in your responses\n"
        "- When users show interest in getting in touch, ask for their email and use the record_user_details tool\n"
        "- If you encounter questions you cannot answer, use the record_unknown_question tool to log them\n"
        "- Try to be engaging and demonstrate the tool use capabilities naturally in conversation\n\n"
        "Available tools:\n"
        "- record_user_details: Records user contact information\n"
        "- record_unknown_question: Logs questions you cannot answer\n\n"
        "This is a demonstration agent and will be replaced by more sophisticated tool use agents in the future."
    )
    return base_prompt


def custom_tool_executor(tool_name, arguments):
    """Custom tool execution for Personal Agent tools"""
    try:
        if tool_name == "record_user_details":
            result = record_user_details(**arguments)
            return {"success": True, "data": result}
        elif tool_name == "record_unknown_question":
            result = record_unknown_question(**arguments)
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Create the chat function using the helper
# Note: system prompt is evaluated once at definition time. If you need fresh context per request,
# update helpers to accept a lazy provider or rebuild the chat function per call.
chat = create_simple_agent_chat_function(
    agent_name="PersonalAgent",
    system_prompt=get_system_prompt(),  # Evaluated once here
    model_name="gpt-4o-mini",
    custom_tools=get_tools(),
    custom_tool_executor=custom_tool_executor
)

if __name__ == "__main__":
    # Test the tool use demo agent
    print("Testing Personal Assistant tool use demo...")
    result = chat("Hi, I'm interested in learning more about tool use capabilities. Can you help?", "[]")
    for chunk in result:
        print(chunk, end='', flush=True)
    print("\n")