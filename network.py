"""
Main Agent Network implementation.
"""

import threading
import time
import uuid
from typing import Dict, List, Tuple, Union, Optional, Any

from python_a2a import AgentNetwork as A2ANetwork
from python_a2a import Message, TextContent, MessageRole
from python_a2a.client import A2AClient

from config import logger, running_agents
from routing import KeywordRouter, AIRouter
from utils import find_free_port

class AgentNetwork:
    """
    Coordinates a network of specialized agents with intelligent routing.
    """
    
    def __init__(self, router_type="keyword"):
        """
        Initialize the agent network.
        
        Args:
            router_type: The type of router to use ('keyword' or 'ai')
        """
        self.agents = {}  # Dict of name -> endpoint
        self.clients = {}  # Dict of name -> A2AClient
        self.a2a_network = A2ANetwork()
        self.router_type = router_type
        self.router = None
        
        # Initialize the router based on the type
        self._initialize_router()
    
    def _initialize_router(self):
        """Initialize the appropriate router."""
        if self.router_type == "ai":
            self.router = AIRouter(self)
            if not self.router.router:  # AI router initialization failed
                logger.warning("AI router initialization failed, falling back to keyword router")
                self.router = KeywordRouter(self)
        else:
            self.router = KeywordRouter(self)
    
    def add(self, name: str, endpoint: str):
        """
        Add an agent to the network.
        
        Args:
            name: Name of the agent
            endpoint: URL endpoint of the agent
        """
        self.agents[name] = endpoint
        self.clients[name] = A2AClient(endpoint)
        logger.info(f"Added agent '{name}' at {endpoint}")
        
        # Re-initialize the router to include the new agent
        self._initialize_router()
    
    def remove(self, name: str):
        """
        Remove an agent from the network.
        
        Args:
            name: Name of the agent to remove
        """
        if name in self.agents:
            del self.agents[name]
            del self.clients[name]
            logger.info(f"Removed agent '{name}' from network")
            
            # Re-initialize the router after removing the agent
            self._initialize_router()
    
    def get_agent_card(self, name: str):
        """
        Get the agent card for a specific agent.
        
        Args:
            name: Name of the agent
            
        Returns:
            The agent card or None if not found
        """
        if name in self.clients:
            try:
                return self.clients[name].get_agent_card()
            except Exception as e:
                logger.error(f"Error getting card for {name}: {e}")
                return None
        return None
    
    def get_all_agent_cards(self):
        """
        Get all agent cards in the network.
        
        Returns:
            Dict of name -> agent card
        """
        cards = {}
        for name in self.agents:
            card = self.get_agent_card(name)
            if card:
                cards[name] = card
        return cards
    
    def route_query(self, query: str) -> Tuple[Optional[str], float]:
        """
        Route a query to the most appropriate agent.
        
        Args:
            query: The user query to route
            
        Returns:
            Tuple of (agent_name, confidence_score)
        """
        if not self.agents:
            logger.warning("No agents in network to route query to")
            return None, 0.0
        
        if not self.router:
            logger.warning("No router available, using first agent")
            return list(self.agents.keys())[0], 0.1
        
        return self.router.route_query(query)
    
    def process_query(self, query: str, target_agent: Optional[str] = None) -> str:
        """
        Process a query by routing to the appropriate agent.
        
        Args:
            query: The query to process
            target_agent: Optional specific agent to use
            
        Returns:
            The agent's response
        """
        if not self.agents:
            return "Error: No agents available in the network"
        
        # Use specific agent if provided
        if target_agent:
            if target_agent not in self.agents:
                return f"Error: Agent '{target_agent}' not found in network"
            agent_name = target_agent
            confidence = 1.0
        else:
            # Route the query to the best agent
            agent_name, confidence = self.route_query(query)
            if not agent_name:
                return "Error: Failed to route query to an agent"
        
        logger.info(f"Routing query to {agent_name} (confidence: {confidence:.2f})")
        
        try:
            # Create message
            message = Message(
                content=TextContent(text=query),
                role=MessageRole.USER,
                message_id=str(uuid.uuid4()),
                conversation_id=str(uuid.uuid4())
            )
            
            # Send to agent
            client = self.clients[agent_name]
            response = client.send_message(message)
            
            if response and hasattr(response, 'content'):
                if hasattr(response.content, 'text'):
                    return response.content.text
                return str(response.content)
            return f"Error: Received invalid response from {agent_name}"
        
        except Exception as e:
            logger.error(f"Error processing query with {agent_name}: {e}")
            return f"Error: Failed to process query with agent {agent_name}: {str(e)}" 