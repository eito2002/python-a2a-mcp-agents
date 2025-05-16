"""
MCP-enabled agent base class.
"""

import json
import time
import asyncio
import requests
from typing import Dict, List, Any, Optional, Union, Set

from python_a2a import A2AServer, AgentCard, AgentSkill, Message, TextContent, MessageRole, Task, TaskStatus, TaskState
from python_a2a.models import FunctionCallContent, FunctionResponseContent
from python_a2a.mcp.agent import MCPEnabledAgent as BaseMCPEnabledAgent
from config import logger
from agents.base_agent import BaseAgent

class MCPEnabledAgent(BaseAgent, BaseMCPEnabledAgent):
    """Base class for MCP-enabled agents in the network."""
    
    def __init__(
        self, 
        agent_card: AgentCard,
        mcp_servers: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        tool_discovery: bool = True,
        max_concurrent_calls: int = 5
    ):
        """
        Initialize the MCP-enabled agent with a card and MCP servers.
        
        Args:
            agent_card: The agent card containing metadata
            mcp_servers: Dictionary mapping server names to URLs or config dicts
            tool_discovery: Whether to automatically discover tools on initialization
            max_concurrent_calls: Maximum number of concurrent MCP tool calls
        """
        # Initialize both parent classes
        BaseAgent.__init__(self, agent_card=agent_card)
        BaseMCPEnabledAgent.__init__(
            self, 
            mcp_servers=mcp_servers, 
            tool_discovery=tool_discovery,
            max_concurrent_calls=max_concurrent_calls
        )
        
        # Add MCP capabilities to agent card
        self._update_agent_card_with_mcp_capabilities()
    
    def _update_agent_card_with_mcp_capabilities(self):
        """Update the agent card with MCP tool capabilities."""
        # This will be called after MCP servers are initialized
        pass
    
    async def initialize(self):
        """Initialize the agent including MCP servers."""
        await self.initialize_mcp_servers()
        # Now we can update the agent card with tool capabilities
        await self._update_agent_card_with_mcp_tools()
    
    async def _update_agent_card_with_mcp_tools(self):
        """Update the agent card with discovered MCP tools."""
        # Get all tools from MCP servers
        all_tools = self.get_all_mcp_tools()
        
        # Add tools as skills to the agent card
        for server_name, tools in all_tools.items():
            for tool in tools:
                # Create a skill from the tool
                skill = AgentSkill(
                    name=f"{server_name}_{tool['name']}",
                    description=tool['description'],
                    tags=[server_name, "mcp", "tool"]
                )
                
                # Add to agent card
                self.agent_card.skills.append(skill)
        
        logger.info(f"Updated agent card with {len(self.agent_card.skills)} skills from MCP tools")
    
    async def handle_message_async(self, message: Message) -> Message:
        """
        Handle incoming message asynchronously, supporting MCP function calls.
        
        This method should be implemented by subclasses to handle messages
        with potential MCP function calls.
        """
        # Default implementation just calls the synchronous version
        return self.handle_message(message)
    
    async def handle_task_async(self, task: Task) -> Task:
        """
        Handle task asynchronously, supporting MCP function calls.
        
        This method should be implemented by subclasses to handle tasks
        with potential MCP function calls.
        """
        # Default implementation just calls the synchronous version
        return self.handle_task(task)
    
    async def close(self):
        """Close the agent including MCP connections."""
        await self.close_mcp_connections()
    
    def run(self, host="0.0.0.0", port=5000, debug=False):
        """
        Run the agent as a server, initializing MCP connections first.
        
        Args:
            host: Host to bind to (default: "0.0.0.0")
            port: Port to listen on (default: 5000)
            debug: Enable debug mode (default: False)
        """
        # Create event loop for initialization
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.initialize())
        
        # Run the server
        from python_a2a.server.http import run_server
        run_server(self, host=host, port=port, debug=debug) 