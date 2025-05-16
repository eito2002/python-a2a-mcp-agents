"""
Base agent class and shared agent functionality.
"""

from python_a2a import A2AServer, AgentCard, AgentSkill, Message, TextContent, MessageRole, Task, TaskStatus, TaskState

class BaseAgent(A2AServer):
    """Base class for all agents in the network."""
    
    def __init__(self, agent_card):
        """
        Initialize the base agent with a card.
        
        Args:
            agent_card: The agent card containing metadata
        """
        super().__init__(agent_card=agent_card)
    
    def _extract_query_from_task(self, task: Task) -> str:
        """
        Extract the query text from a task.
        
        Args:
            task: The task object
            
        Returns:
            The extracted query text
        """
        if task.message:
            if isinstance(task.message, dict):
                content = task.message.get("content", {})
                if isinstance(content, dict):
                    return content.get("text", "")
        return ""
        
    def run(self, host="0.0.0.0", port=5000, debug=False):
        """
        Run the agent as a server.
        
        Args:
            host: Host to bind to (default: "0.0.0.0")
            port: Port to listen on (default: 5000)
            debug: Enable debug mode (default: False)
        """
        from python_a2a.server.http import run_server
        run_server(self, host=host, port=port, debug=debug)