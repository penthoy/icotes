
class CustomAgentBase(ABC):
    """
    Base class for custom agents with chat input/output capabilities
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def process_chat_input(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process chat input and return chat output
        
        Args:
            input_message: The user's chat message
            context: Optional context information
            
        Returns:
            The agent's response message
        """
        pass
    
    @abstractmethod
    async def process_chat_stream(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """
        Process chat input and return streaming chat output
        
        Args:
            input_message: The user's chat message
            context: Optional context information
            
        Yields:
            Chunks of the agent's response message
        """
        pass


class OpenAIDemoAgent(CustomAgentBase):
    """
    OpenAI Demo Agent for ICUI Framework
    
    This agent demonstrates OpenAI capabilities within the ICUI framework
    with support for tool/function calling and streaming responses.
    """
    
    def __init__(self):
        super().__init__(
            name="OpenAI Demo Agent",
            description="An agent that demonstrates OpenAI capabilities within the ICUI framework with tool calling support."
        )
        self.capabilities = ["chat", "reasoning", "code_generation", "tool_calling"]
        self.model = "gpt-4o-mini"
        self.temperature = 0.7
        self.max_tokens = 2000
    
    async def process_chat_input(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process chat input using OpenAI API with tool calling capabilities
        """
        try:
            # For now, return a simple response - this will be enhanced with actual OpenAI API calls
            # and tool calling in future iterations
            response = f"OpenAI Demo Agent received: {input_message}\n\n"
            response += "This is a demonstration response. In a full implementation, this would:\n"
            response += "1. Use OpenAI API for intelligent responses\n"
            response += "2. Support tool/function calling\n"
            response += "3. Maintain conversation context\n"
            response += "4. Handle code generation and reasoning tasks"
            
            logger.info(f"OpenAI Demo Agent processed input: {input_message[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error in OpenAI Demo Agent: {e}")
            return f"Error processing request: {str(e)}"
    
    async def process_chat_stream(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """
        Process chat input and return streaming response
        """
        try:
            # Simulate streaming response - in a full implementation this would use OpenAI's streaming API
            response_parts = [
                "OpenAI Demo Agent is processing your request...\n\n",
                f"Input received: {input_message}\n\n",
                "This is a streaming demonstration. ",
                "Each chunk would come from the OpenAI API. ",
                "The agent supports:\n",
                "• Tool and function calling\n",
                "• Code generation and analysis\n",
                "• Reasoning and problem solving\n",
                "• Context-aware responses\n\n",
                "Ready for full implementation with actual AI capabilities!"
            ]
            
            for part in response_parts:
                yield part
                # Small delay to simulate streaming
                import asyncio
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in OpenAI Demo Agent streaming: {e}")
            yield f"Error processing streaming request: {str(e)}"
