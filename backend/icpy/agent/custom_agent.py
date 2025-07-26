"""
Custom Agent for ICUI Framework
"""


from icui.agent.base_agent import BaseAgent
from icui.agent.custom_agent_config import CustomAgentConfig    

CUSTOM_AGENTS = [
    "OpenAIDemoAgent",
]

class OpenAIDemoAgent(BaseAgent):
    """
    OpenAI Demo Agent for ICUI Framework
    """
    
    def __init__(self, config: CustomAgentConfig):
        super().__init__(config)
        self.name = "OpenAI Demo Agent"
        self.description = "An agent that demonstrates OpenAI capabilities within the ICUI framework."
    
    def input(self, input_data):
        # Process the input data for the OpenAI demo agent
        pass
    def run(self, input_data):
        # Implement the logic for the OpenAI demo agent here
        pass

async def auto_initialize_chat_agent():
    """Automatically create a default agent and configure chat service on startup."""
    try:
        logger.info("🚀 Auto-initializing chat agent...")
        
        # Get agent and chat services
        agent_service = await get_agent_service()
        chat_service = get_chat_service()
        
        # Check if an agent is already configured
        if chat_service.config.agent_id:
            logger.info(f"✅ Chat agent already configured: {chat_service.config.agent_id}")
            return
        
        # Check if there are existing agent sessions
        existing_sessions = agent_service.get_agent_sessions()
        if existing_sessions:
            # Use the first available agent
            first_agent = existing_sessions[0]
            logger.info(f"🔄 Using existing agent: {first_agent.agent_name} ({first_agent.agent_id})")
            await chat_service.update_config({"agent_id": first_agent.agent_id})
            return
        
        # Create a new default agent using AgentConfig
        logger.info("🤖 Creating default OpenAI agent...")
        
        # Import AgentConfig
        from icpy.agent.base_agent import AgentConfig
        
        agent_config = AgentConfig(
            name="default_chat_agent",
            framework="openai",
            role="assistant",
            goal="Help users with questions, code assistance, and general tasks",
            backstory="I am a helpful AI assistant powered by OpenAI's GPT-4o-mini model",
            capabilities=["chat", "reasoning", "code_generation"],
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2000,
            custom_config={
                "stream": True
            }
        )
        
        # Create the agent
        agent_session_id = await agent_service.create_agent(agent_config)
        
        # Get the agent ID from the session
        sessions = agent_service.get_agent_sessions()
        agent_id = None
        for session in sessions:
            if session.session_id == agent_session_id:
                agent_id = session.agent_id
                break
        
        if agent_id:
            logger.info(f"✅ Created default agent: {agent_id}")
            
            # Configure chat service to use this agent
            await chat_service.update_config({"agent_id": agent_id})
            logger.info(f"✅ Chat service configured with agent: {agent_id}")
        else:
            logger.error("❌ Failed to get agent ID after creation")
            
    except Exception as e:
        logger.error(f"💥 Error during auto-initialization: {e}")
        logger.exception("Full traceback:")