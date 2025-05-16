"""
Keyword-based router implementation.
"""

import random
from config import logger

class KeywordRouter:
    """Router that uses simple keyword matching to route queries."""
    
    def __init__(self, agent_network):
        """Initialize the keyword router."""
        self.agent_network = agent_network
        self.keyword_mapping = {}
        
        # Create mappings from agent information
        self._initialize_keyword_mappings()
    
    def _initialize_keyword_mappings(self):
        """Build keyword mappings from agent capabilities."""
        for name, agent in self.agent_network.agents.items():
            agent_card = self.agent_network.get_agent_card(name)
            
            if not agent_card:
                continue
            
            # Extract keywords from agent name and description
            keywords = [name.lower()]
            if hasattr(agent_card, 'name'):
                keywords.extend(agent_card.name.lower().split())
            if hasattr(agent_card, 'description'):
                # Add key phrases from description
                desc = agent_card.description.lower()
                # Split into words and remove common words
                stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'about'}
                desc_words = [w for w in desc.split() if w not in stop_words and len(w) > 3]
                keywords.extend(desc_words)
            
            # Extract keywords from skills
            if hasattr(agent_card, 'skills'):
                for skill in agent_card.skills:
                    if hasattr(skill, 'tags'):
                        keywords.extend([tag.lower() for tag in skill.tags])
                    if hasattr(skill, 'name'):
                        keywords.extend(skill.name.lower().split())
            
            # Filter unique and useful keywords
            keywords = list(set(keywords))
            
            # Map each keyword to this agent
            for keyword in keywords:
                if keyword not in self.keyword_mapping:
                    self.keyword_mapping[keyword] = []
                self.keyword_mapping[keyword].append(name)
    
    def route_query(self, query, conversation_history=None, use_cache=True):
        """
        Route a query to the most appropriate agent based on keywords.
        
        Args:
            query: The query to route
            conversation_history: Not used by keyword router
            use_cache: Not used by keyword router
            
        Returns:
            A tuple of (agent_name, confidence_score)
        """
        query_lower = query.lower()
        agent_scores = {}
        
        # Calculate scores for each agent based on keyword matches
        for keyword, agents in self.keyword_mapping.items():
            if keyword in query_lower:
                for agent in agents:
                    agent_scores[agent] = agent_scores.get(agent, 0) + 1
        
        # Find the agent with the highest score
        if agent_scores:
            best_agent = max(agent_scores.items(), key=lambda x: x[1])
            agent_name = best_agent[0]
            score = best_agent[1]
            confidence = min(score / 10, 1.0)  # Normalize confidence to [0, 1]
            return agent_name, confidence
        
        # If no keywords match, return a random agent with low confidence
        all_agents = list(self.agent_network.agents.keys())
        if all_agents:
            return random.choice(all_agents), 0.1
        
        # No agents available
        return None, 0.0 