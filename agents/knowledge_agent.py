"""
Knowledge agent implementation.
"""

import time
import random
from python_a2a import AgentCard, AgentSkill, Message, TextContent, MessageRole, Task, TaskStatus, TaskState
from config import logger
from agents.base_agent import BaseAgent

class KnowledgeAgent(BaseAgent):
    """Agent that answers general knowledge questions."""
    
    def __init__(self):
        """Initialize the knowledge agent with its capabilities."""
        agent_card = AgentCard(
            name="Knowledge Agent",
            description="Provides factual information and answers to general knowledge questions across various domains",
            url="http://localhost:0",  # Will be updated when server starts
            version="1.0.0",
            skills=[
                AgentSkill(
                    name="Facts and Information",
                    description="Answer factual questions about history, science, geography, and other general topics",
                    tags=["knowledge", "facts", "information", "questions", "general"],
                    examples=["What is the capital of Japan?", "When was the Declaration of Independence signed?"]
                ),
                AgentSkill(
                    name="Definitions and Concepts",
                    description="Explain and define terms, concepts, and ideas",
                    tags=["definition", "meaning", "concept", "explanation", "define"],
                    examples=["What is photosynthesis?", "Define quantum physics"]
                )
            ]
        )
        super().__init__(agent_card=agent_card)
    
    def handle_message(self, message: Message) -> Message:
        """Handle incoming message with a knowledge request."""
        query = message.content.text if hasattr(message.content, "text") else ""
        
        # Add a delay to simulate processing and research
        logger.info("[Knowledge Agent] Researching information...")
        time.sleep(0.8)
        
        answer = self._answer_question(query)
        
        logger.info("[Knowledge Agent] Answer found")
        
        return Message(
            content=TextContent(text=answer),
            role=MessageRole.AGENT,
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id
        )
    
    def handle_task(self, task: Task) -> Task:
        """Handle task-based knowledge request."""
        query = self._extract_query_from_task(task)
        
        # Add a delay to simulate processing and research
        logger.info("[Knowledge Agent] Researching information...")
        time.sleep(0.8)
        
        answer = self._answer_question(query)
        
        logger.info("[Knowledge Agent] Answer found")
        
        # Update task with the knowledge information
        task.artifacts = [{
            "parts": [{"type": "text", "text": answer}]
        }]
        task.status = TaskStatus(state=TaskState.COMPLETED)
        return task
    
    def _answer_question(self, query: str) -> str:
        """Answer a knowledge question with simulated information."""
        query_lower = query.lower()
        
        # Simple knowledge base with a few predefined answers
        knowledge_base = {
            # Geography
            "capital of japan": "The capital of Japan is Tokyo, which is also the largest city in Japan with a population of over 13 million people.",
            "capital of france": "The capital of France is Paris, often called the 'City of Light' (La Ville Lumière).",
            
            # Science
            "photosynthesis": "Photosynthesis is the process used by plants, algae, and certain bacteria to convert light energy, usually from the sun, into chemical energy in the form of glucose or other sugars. The basic equation is: 6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂.",
            
            # Technology
            "artificial intelligence": "Artificial Intelligence (AI) refers to systems or machines that mimic human intelligence to perform tasks and can iteratively improve themselves based on the information they collect. Common AI applications include machine learning, natural language processing, computer vision, and robotics."
        }
        
        # Check for direct matches in the knowledge base
        for key, answer in knowledge_base.items():
            if key in query_lower:
                return answer
        
        # No match found, generate a generic response
        return "I don't have specific information on that question in my knowledge base. As a simulated agent, I have access to only a limited set of predefined answers." 