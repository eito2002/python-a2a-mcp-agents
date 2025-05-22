"""
Agents module for the agent network.
"""

from .mcp.mcp_travel_agent import MCPTravelAgent
from .mcp.mcp_weather_agent import MCPWeatherAgent

__all__ = ["MCPTravelAgent", "MCPWeatherAgent"]
