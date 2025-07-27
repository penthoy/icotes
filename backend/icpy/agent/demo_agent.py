class DemoAgent(BaseAgent):
    """
    Demo Agent for ICUI Framework
    
    This agent demonstrates basic capabilities within the ICUI framework.
    """
    
    def __init__(self):
        super().__init__(
            name="Demo Agent",
            description="An agent that demonstrates basic capabilities within the ICUI framework."
        )
    
    async def process_chat_input(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process chat input and return a simple response.
        
        Args:
            input_message: The user's chat message
            context: Optional context information
            
        Returns:
            A simple response message
        """
        return f"Demo Agent received: {input_message}"