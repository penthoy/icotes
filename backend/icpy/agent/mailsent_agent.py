import asyncio
import os
from dotenv import load_dotenv
import requests
# Load environment variables from the root .env file FIRST
load_dotenv(dotenv_path="../.env")

from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict

from tools.mailsent_tools import send_email
load_dotenv(override=True)


def sales_agent_as_tools():
    # Recreate agents for the function tool test
    instructions1 = "You are a sales agent working for ComplAI, \
    a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
    You write professional, serious cold emails."

    instructions2 = "You are a humorous, engaging sales agent working for ComplAI, \
    a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
    You write witty, engaging cold emails that are likely to get a response."

    instructions3 = "You are a busy sales agent working for ComplAI, \
    a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
    You write concise, to the point cold emails."

    sales_agent1 = Agent(
        name="Professional Sales Agent",
        instructions=instructions1,
        model="gpt-4o-mini",
    )

    sales_agent2 = Agent(
        name="Engaging Sales Agent",
        instructions=instructions2,
        model="gpt-4o-mini",
    )

    sales_agent3 = Agent(
        name="Busy Sales Agent",
        instructions=instructions3,
        model="gpt-4o-mini",
    )

    print("\nTesting sales manager with tools...")
    description = "Write a cold sales email"

    tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description=description)
    tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description=description)
    tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description=description)

    tools = [tool1, tool2, tool3, send_email]
    return tools


def sales_manager_agent(tools):
    instructions ="You are a sales manager working for ComplAI. You use the tools given to you to generate cold sales emails. \
    You never generate sales emails yourself; you always use the tools. \
    You try all 3 sales_agent tools once before choosing the best one. \
    You pick the single best email and use the send_email tool to send the best email (and only the best email) to the user."

    sales_manager = Agent(name="Sales Manager", instructions=instructions, tools=tools, model="gpt-4o-mini")

    return sales_manager

async def main():
    """Main async function that runs all the demo agent functionality"""

    tools = sales_agent_as_tools()

    sales_manager = sales_manager_agent(tools)

    message = "Send a cold sales email addressed to 'Dear CEO'"

    with trace("Sales manager"):
        result = await Runner.run(sales_manager, message)
        print(f"Sales manager result: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
