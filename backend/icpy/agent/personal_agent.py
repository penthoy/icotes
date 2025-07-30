# from dotenv import load_dotenv
# load_dotenv(override=True)
# import requests

import json
import os

from .clients import get_openai_client
from .tools.pdfreader_tools import get_pdf_reader
from .tools.pushover_tools import push


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question} asked that I couldn't answer")
    return {"recorded": "ok"}

def get_tools():
    record_user_details_json = {
        "name": "record_user_details",
        "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The email address of this user"
                },
                "name": {
                    "type": "string",
                    "description": "The user's name, if they provided it"
                }
                ,
                "notes": {
                    "type": "string",
                    "description": "Any additional information about the conversation that's worth recording to give context"
                }
            },
            "required": ["email"],
            "additionalProperties": False
        }
    }

    record_unknown_question_json = {
        "name": "record_unknown_question",
        "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question that couldn't be answered"
                },
            },
            "required": ["question"],
            "additionalProperties": False
        }
    }

    tools = [{"type": "function", "function": record_user_details_json},
            {"type": "function", "function": record_unknown_question_json}]
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


def get_system_prompt(name="Tao Zhang", linkedin=None):
    if linkedin is None:
        linkedin = get_pdf_reader("/home/penthoy/ilaborcode/backend/icpy/agent/tools/tazhang_linkedin.pdf")
    system_prompt = f"You are acting as {name}. You are answering questions on {name}'s website, \
    particularly questions related to {name}'s career, background, skills and experience. \
    Your responsibility is to represent {name} for interactions on the website as faithfully as possible. \
    You are given a summary of {name}'s background and LinkedIn profile which you can use to answer questions. \
    Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
    If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
    If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

    system_prompt += f"\n\n## LinkedIn Profile:\n{linkedin}\n\n"
    system_prompt += f"With this context, please chat with the user, always staying in character as {name}."
    
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
            assistant_message = {
                "role": "assistant", 
                "content": ''.join(collected_chunks),
                "tool_calls": collected_tool_calls
            }
            messages.append(assistant_message)
            messages.extend(results)
            
            yield f"\n[Tools processed, generating response...]"
        else:
            done = True

if __name__ == "__main__":
    result = chat("what is your name?", "[]")
    print(result)
    
#gr.ChatInterface(chat, type="messages").launch(server_name="0.0.0.0", server_port=7863, pwa=True)