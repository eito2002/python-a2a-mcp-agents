"""
Client for interacting with Agent Network through CLI
"""

from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from python_a2a.client import A2AClient
from python_a2a.models import (Conversation, ErrorContent, Message,
                               MessageRole, TextContent)

from server import AgentServer
from utils import find_free_port


class A2AAgentClient(A2AClient):
    """A2A-compatible client for a specific agent"""

    def __init__(self, endpoint_url: str, agent_name: str):
        """
        Initialize a client for a specific agent

        Args:
            endpoint_url: The URL of the A2A-compatible agent
            agent_name: The name of the agent
        """
        super().__init__(endpoint_url)
        self.agent_name = agent_name

    def test_connection(self) -> bool:
        """
        Test if this agent is reachable

        Returns:
            True if agent is reachable, False otherwise
        """
        try:
            # Use GET request instead of HEAD to check if the endpoint is reachable
            # Many FastAPI implementations don't explicitly handle HEAD requests
            response = requests.get(self.endpoint_url, timeout=2)
            return response.status_code < 400  # Any success or redirect status
        except requests.RequestException:
            return False


class A2ANetworkClient:
    """Client for interacting with a network of A2A-compatible agents"""

    def __init__(self, agent_endpoints: Optional[Dict[str, str]] = None):
        """
        Initialize a network client

        Args:
            agent_endpoints: Dict mapping agent names to endpoint URLs
        """
        self.agents = {}  # name -> A2AAgentClient

        # Add provided endpoints
        if agent_endpoints:
            for name, endpoint in agent_endpoints.items():
                self.add_agent(name, endpoint)

    def add_agent(self, name: str, endpoint_url: str) -> None:
        """
        Add an agent to the network

        Args:
            name: The name of the agent
            endpoint_url: The URL of the A2A-compatible agent
        """
        self.agents[name] = A2AAgentClient(endpoint_url, name)

    def discover_agents(self, known_ports: Optional[Dict[str, int]] = None) -> None:
        """
        Discover running agents and add them to the network

        Args:
            known_ports: Optional dictionary mapping agent names to known ports
        """
        try:
            # First try using AgentServer if running in the same process
            running_agents = AgentServer.list_running_agents()
            for agent_name in running_agents:
                info = AgentServer.get_agent_info(agent_name)
                if info:
                    self.add_agent(agent_name, info["endpoint"])
        except Exception:
            pass  # Continue to next method if this fails

        # Add agents from known ports (provided or default)
        if not known_ports:
            known_ports = {"weather": 59983, "knowledge": 59984}

        # Update with provided ports or use defaults for missing ones
        for name, port in known_ports.items():
            endpoint = f"http://localhost:{port}/a2a"
            self.add_agent(name, endpoint)

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all available agents

        Returns:
            List of agent information dictionaries
        """
        result = []
        for name, client in self.agents.items():
            is_available = client.test_connection()
            result.append(
                {
                    "name": name,
                    "endpoint": client.endpoint_url,
                    "available": is_available,
                }
            )
        return result

    def test_connection(self, agent_name: str) -> bool:
        """
        Test if an agent is reachable

        Args:
            agent_name: Name of the agent to test

        Returns:
            True if agent is reachable, False otherwise
        """
        if agent_name not in self.agents:
            return False

        return self.agents[agent_name].test_connection()

    def _create_error_message(
        self, error_text: str, original_message: Optional[Message] = None
    ) -> Message:
        """
        Create an error message

        Args:
            error_text: The error text
            original_message: The original message that caused the error

        Returns:
            Error message
        """
        parent_id = None
        conversation_id = None

        if original_message:
            parent_id = original_message.message_id
            conversation_id = original_message.conversation_id

        return Message(
            content=ErrorContent(message=error_text),
            role=MessageRole.SYSTEM,
            parent_message_id=parent_id,
            conversation_id=conversation_id,
        )

    def send_message(
        self, message: Message, agent_name: Optional[str] = None
    ) -> Message:
        """
        Send a message to a specific agent or route it

        Args:
            message: The message to send
            agent_name: Name of the agent to send to (if None, will use routing)

        Returns:
            The agent's response message
        """
        # Auto-discover if no agents
        if not self.agents:
            self.discover_agents()

        # Check if we have any agents
        if not self.agents:
            error_text = "No agents available. Please start agent servers first or provide agent endpoints."
            return self._create_error_message(error_text, message)

        if agent_name:
            if agent_name not in self.agents:
                error_text = f"Agent '{agent_name}' not found"
                return self._create_error_message(error_text, message)

            # Test connection before sending
            if not self.test_connection(agent_name):
                error_text = f"Cannot connect to agent '{agent_name}'. Please ensure the agent server is running."
                return self._create_error_message(error_text, message)

            # Send to the specified agent
            return self.agents[agent_name].send_message(message)
        else:
            # Simple routing: pick first available agent
            for name, client in self.agents.items():
                if client.test_connection():
                    return client.send_message(message)

            # If we get here, no agents are available
            error_text = "No available agents could be reached. Please ensure agent servers are running."
            return self._create_error_message(error_text, message)

    def run_workflow(
        self, initial_message: Message, workflow: List[str]
    ) -> Conversation:
        """
        Run a workflow conversation through multiple agents

        Args:
            initial_message: The initial message
            workflow: List of agent names to process in sequence

        Returns:
            The final conversation
        """
        # Initialize conversation
        conversation = Conversation()
        conversation.add_message(initial_message)

        # Test all connections first
        unavailable_agents = []
        for agent_name in workflow:
            if agent_name not in self.agents:
                conversation.create_error_message(
                    f"Agent '{agent_name}' not found in the network"
                )
                return conversation

            if not self.test_connection(agent_name):
                unavailable_agents.append(agent_name)

        if unavailable_agents:
            conversation.create_error_message(
                f"Cannot connect to the following agents: {', '.join(unavailable_agents)}. "
                "Please ensure all agent servers are running."
            )
            return conversation

        # Process through each agent in the workflow
        for agent_name in workflow:
            client = self.agents[agent_name]
            try:
                # Send conversation to current agent
                updated_conversation = client.send_conversation(conversation)
                conversation = updated_conversation
            except Exception as e:
                conversation.create_error_message(
                    f"Error communicating with {agent_name} agent: {str(e)}"
                )
                break

        return conversation
