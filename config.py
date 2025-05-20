"""
Configuration and logging setup for the agent network.
"""

import logging
import os

# Import OpenAI integrations with proper error handling
try:
    from python_a2a.client.llm import OpenAIA2AClient
    from python_a2a.client.router import AIAgentRouter
    from python_a2a.server.llm import OpenAIA2AServer

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create logger
logger = logging.getLogger("AgentNetwork")

# Global dictionary to track running agents
running_agents = {}
