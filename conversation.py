"""
Inter-agent conversation orchestration.
"""

import uuid
from typing import List, Dict, Any, Optional

from python_a2a import Message, TextContent, MessageRole

from config import logger

class ConversationOrchestrator:
    """
    Orchestrates conversations between multiple agents.
    Allows for agent-to-agent communication in a structured workflow.
    """
    
    def __init__(self, agent_network):
        """
        Initialize the conversation orchestrator.
        
        Args:
            agent_network: The agent network to use for conversations
        """
        self.agent_network = agent_network
        self.conversations = {}  # Conversation ID -> conversation history
    
    def start_conversation(self, initial_query: str, workflow: List[str]) -> str:
        """
        Start a new multi-agent conversation with a defined workflow.
        
        Args:
            initial_query: The initial user query that starts the conversation
            workflow: Ordered list of agent names to process the query
            
        Returns:
            Conversation ID for the new conversation
        """
        if not workflow:
            raise ValueError("Workflow must contain at least one agent")
            
        # Validate all agents in the workflow
        for agent_name in workflow:
            if agent_name not in self.agent_network.agents:
                raise ValueError(f"Agent '{agent_name}' not found in network")
        
        # Create a new conversation
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = {
            "workflow": workflow,
            "current_step": 0,
            "messages": [],
            "complete": False,
            "result": None
        }
        
        # Start the conversation with the initial query
        self._process_next_step(conversation_id, initial_query)
        
        return conversation_id
    
    def _process_next_step(self, conversation_id: str, current_input: str) -> None:
        """
        Process the next step in a conversation workflow.
        
        Args:
            conversation_id: The ID of the conversation
            current_input: The input text for the current step
        """
        if conversation_id not in self.conversations:
            logger.error(f"Conversation {conversation_id} not found")
            return
        
        conversation = self.conversations[conversation_id]
        
        # Check if the conversation is already complete
        if conversation["complete"]:
            logger.warning(f"Conversation {conversation_id} is already complete")
            return
        
        # Get the current agent in the workflow
        current_step = conversation["current_step"]
        if current_step >= len(conversation["workflow"]):
            # Workflow is complete
            conversation["complete"] = True
            conversation["result"] = current_input
            logger.info(f"Conversation {conversation_id} completed")
            return
        
        current_agent = conversation["workflow"][current_step]
        
        # Create a message for the current agent
        message = Message(
            content=TextContent(text=current_input),
            role=MessageRole.USER,
            message_id=str(uuid.uuid4()),
            conversation_id=conversation_id
        )
        
        # Add the message to the conversation history
        conversation["messages"].append({
            "role": "user" if current_step == 0 else conversation["workflow"][current_step - 1],
            "content": current_input
        })
        
        try:
            # Send the message to the current agent
            logger.info(f"Sending message to {current_agent} in conversation {conversation_id}")
            client = self.agent_network.clients[current_agent]
            response = client.send_message(message)
            
            # Extract the response text
            response_text = ""
            if response and hasattr(response, "content"):
                if hasattr(response.content, "text"):
                    response_text = response.content.text
                else:
                    response_text = str(response.content)
            
            # Add the response to the conversation history
            conversation["messages"].append({
                "role": current_agent,
                "content": response_text
            })
            
            # Move to the next step in the workflow
            conversation["current_step"] += 1
            
            # Process the next step with the response from the current agent
            self._process_next_step(conversation_id, response_text)
            
        except Exception as e:
            logger.error(f"Error in conversation {conversation_id} with agent {current_agent}: {e}")
            # Mark the conversation as complete with an error
            conversation["complete"] = True
            conversation["result"] = f"Error in conversation with agent {current_agent}: {str(e)}"
    
    def get_conversation_result(self, conversation_id: str) -> Optional[str]:
        """
        Get the result of a completed conversation.
        
        Args:
            conversation_id: The ID of the conversation
            
        Returns:
            The final result of the conversation, or None if not complete
        """
        if conversation_id not in self.conversations:
            return None
        
        conversation = self.conversations[conversation_id]
        if not conversation["complete"]:
            return None
        
        return conversation["result"]
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Get the full history of a conversation.
        
        Args:
            conversation_id: The ID of the conversation
            
        Returns:
            List of message dictionaries
        """
        if conversation_id not in self.conversations:
            return []
        
        return self.conversations[conversation_id]["messages"] 