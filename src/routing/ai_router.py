"""
AI-based router implementation.
"""

import json

from config import OPENAI_AVAILABLE, logger

if OPENAI_AVAILABLE:
    from python_a2a.client.router import AIAgentRouter


class AIRouter:
    """Router that uses AI to determine the best agent for a query."""

    def __init__(self, agent_network, model=None):
        """
        Initialize the AI router.

        Args:
            agent_network: The agent network to route queries within
            model: The LLM model to use for routing (defaults to gpt-3.5-turbo-0613)
        """
        self.agent_network = agent_network
        self.model = model or "gpt-3.5-turbo-0613"
        self.router = None
        self.routing_cache = {}

        # Check if OpenAI is available
        if not OPENAI_AVAILABLE:
            logger.warning(
                "OpenAI integration not available. AI routing will not work."
            )
            return

        # Initialize the router
        try:
            self._initialize_router()
        except Exception as e:
            logger.error(f"Failed to initialize AI router: {e}")

    def _initialize_router(self):
        """Initialize the AI router with agent information."""
        if not OPENAI_AVAILABLE:
            return

        # Get agent cards
        agent_skills = {}
        for name, agent in self.agent_network.agents.items():
            try:
                agent_card = self.agent_network.get_agent_card(name)
                if agent_card:
                    skills_info = []
                    if hasattr(agent_card, "skills"):
                        for skill in agent_card.skills:
                            skill_info = {
                                "name": (
                                    skill.name
                                    if hasattr(skill, "name")
                                    else "Unknown skill"
                                ),
                                "description": (
                                    skill.description
                                    if hasattr(skill, "description")
                                    else ""
                                ),
                                "tags": skill.tags if hasattr(skill, "tags") else [],
                            }
                            skills_info.append(skill_info)

                    agent_skills[name] = {
                        "agent_name": name,
                        "description": (
                            agent_card.description
                            if hasattr(agent_card, "description")
                            else ""
                        ),
                        "skills": skills_info,
                    }
            except Exception as e:
                logger.error(f"Error retrieving card for {name}: {e}")

        # Create the router
        if agent_skills:
            agent_info_json = json.dumps(agent_skills)
            self.router = AIAgentRouter(agent_info=agent_info_json, model=self.model)
            logger.info("AI router initialized successfully")

    def route_query(self, query, conversation_history=None, use_cache=True):
        """
        Route a query to the most appropriate agent based on AI analysis.

        Args:
            query: The query to route
            conversation_history: Optional history for context
            use_cache: Whether to use cached routing decisions

        Returns:
            A tuple of (agent_name, confidence_score)
        """
        # Check for cached results
        if use_cache and query in self.routing_cache:
            return self.routing_cache[query]

        # Fall back to random routing if router is not available
        if not OPENAI_AVAILABLE or not self.router:
            logger.warning("AI routing not available, falling back to random selection")
            import random

            all_agents = list(self.agent_network.agents.keys())
            if all_agents:
                result = (random.choice(all_agents), 0.1)
                self.routing_cache[query] = result
                return result
            return None, 0.0

        try:
            # Use AI to route the query
            result = self.router.route(query)

            # Parse the result
            agent_name = result.get("agent_name")
            confidence = result.get("confidence", 0.0)

            # Validate the agent exists
            if agent_name not in self.agent_network.agents:
                logger.warning(f"AI router suggested non-existent agent: {agent_name}")
                # Fall back to first available agent
                all_agents = list(self.agent_network.agents.keys())
                if all_agents:
                    agent_name = all_agents[0]
                    confidence = 0.1
                else:
                    return None, 0.0

            # Cache the result
            result = (agent_name, confidence)
            self.routing_cache[query] = result
            return result

        except Exception as e:
            logger.error(f"Error during AI routing: {e}")
            # Fall back to random selection
            import random

            all_agents = list(self.agent_network.agents.keys())
            if all_agents:
                result = (random.choice(all_agents), 0.1)
                self.routing_cache[query] = result
                return result
            return None, 0.0
