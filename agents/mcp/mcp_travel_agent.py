"""
FastAPI based MCP-enabled travel agent implementation with weather agent integration.
"""

import time
import json
import asyncio
from typing import Dict, List, Any, Optional, Union

from python_a2a import AgentCard, AgentSkill, Message, TextContent, MessageRole
from python_a2a import Task, TaskStatus, TaskState
from python_a2a.models import FunctionCallContent, FunctionResponseContent

from config import logger
from agents.mcp.async_agent import FastAPIAgent

class AsyncMCPTravelAgent(FastAPIAgent):
    """Travel agent that uses MCP for enhanced capabilities with FastAPI backend and integrates with other agents."""
    
    def __init__(self, mcp_servers: Optional[Dict[str, str]] = None, agent_connections: Optional[Dict[str, str]] = None, **kwargs):
        """Initialize the MCP-enabled travel agent with FastAPI backend."""
        agent_card = AgentCard(
            name="MCP Travel Agent (FastAPI)",
            description="Provides travel planning with weather information integration using FastAPI",
            url="http://localhost:0",  # Will be updated when server starts
            version="1.0.0",
            skills=[
                AgentSkill(
                    name="Trip Planning",
                    description="Plan a trip considering weather conditions",
                    tags=["travel", "planning", "itinerary", "vacation", "trip"],
                    examples=["Plan a 3-day trip to London considering weather", "What activities can I do in Tokyo based on weather?"]
                ),
                AgentSkill(
                    name="Weather-Based Activities",
                    description="Suggest activities based on weather forecast",
                    tags=["activities", "weather", "recommendations", "outdoor", "indoor"],
                    examples=["What should I do in Paris tomorrow if it rains?", "Outdoor activities in Sydney based on weather"]
                ),
                AgentSkill(
                    name="Travel Advisory",
                    description="Get travel advisories including weather alerts",
                    tags=["advisory", "warnings", "safety", "alerts"],
                    examples=["Any travel alerts for New York this weekend?", "Is it safe to travel to London next week?"]
                )
            ]
        )
        
        # Set up default MCP servers if none provided
        if mcp_servers is None:
            mcp_servers = {
                # Example MCP server configurations
                "travel": "http://localhost:5003",
                "maps": "http://localhost:5002"
            }
        
        # Set up agent connections if none provided
        if agent_connections is None:
            agent_connections = {
                # Default connection to weather agent
                "weather": "http://localhost:5000"
            }
        
        # MCP-related configuration and initialization
        self.mcp_servers = mcp_servers
        self.agent_connections = agent_connections
        self.mcp_tools = {}  # Tools discovered from servers
        self.conversation_history = {}  # Store conversation history with other agents
        self._initialized = False
        
        # Initialize the FastAPIAgent
        super().__init__(agent_card=agent_card, **kwargs)
    
    async def initialize(self):
        """Initialize MCP servers and discover available tools"""
        if self._initialized:
            return
        
        try:
            # Initialize MCP connections (e.g., tool discovery)
            await self._discover_mcp_tools()
            
            # Verify agent connections
            await self._verify_agent_connections()
            
            self._initialized = True
            logger.info(f"[AsyncMCPTravelAgent] Initialized with MCP servers: {self.mcp_servers}")
            logger.info(f"[AsyncMCPTravelAgent] Connected to agents: {self.agent_connections}")
        except Exception as e:
            logger.error(f"[AsyncMCPTravelAgent] Failed to initialize: {e}")
    
    async def _discover_mcp_tools(self):
        """Discover available MCP tools"""
        import aiohttp
        
        for server_name, server_url in self.mcp_servers.items():
            try:
                async with aiohttp.ClientSession() as session:
                    # Get tool information from MCP server
                    tools_url = f"{server_url}/tools"
                    async with session.get(tools_url) as response:
                        if response.status == 200:
                            tools_data = await response.json()
                            # Handle different response formats
                            if isinstance(tools_data, dict) and "tools" in tools_data:
                                # Format: {"tools": [...]}
                                self.mcp_tools[server_name] = tools_data["tools"]
                            elif isinstance(tools_data, list):
                                # Format: [...]
                                self.mcp_tools[server_name] = tools_data
                            else:
                                # Unknown format, use empty list
                                self.mcp_tools[server_name] = []
                                
                            logger.info(f"[AsyncMCPTravelAgent] Discovered {len(self.mcp_tools[server_name])} tools from {server_name}")
                        else:
                            logger.warning(f"[AsyncMCPTravelAgent] Failed to get tools from {server_name}: {response.status}")
            except Exception as e:
                logger.error(f"[AsyncMCPTravelAgent] Error discovering tools from {server_name}: {e}")

    async def _verify_agent_connections(self):
        """Verify that all connected agents are available"""
        import aiohttp
        
        for agent_name, agent_url in self.agent_connections.items():
            try:
                async with aiohttp.ClientSession() as session:
                    # Get agent information
                    async with session.get(f"{agent_url}/agent.json") as response:
                        if response.status == 200:
                            agent_info = await response.json()
                            logger.info(f"[AsyncMCPTravelAgent] Connected to {agent_name} agent: {agent_info.get('name', 'Unknown')}")
                        else:
                            logger.warning(f"[AsyncMCPTravelAgent] Failed to connect to {agent_name} agent: {response.status}")
            except Exception as e:
                logger.error(f"[AsyncMCPTravelAgent] Error connecting to {agent_name} agent: {e}")
    
    async def call_mcp_tool(self, server_name: str, tool_name: str, **kwargs):
        """
        Call a tool on the specified MCP server
        
        Args:
            server_name: MCP server name
            tool_name: Tool name
            **kwargs: Parameters to pass to the tool
            
        Returns:
            Tool execution result
        """
        import aiohttp
        
        if not self._initialized:
            await self.initialize()
        
        server_url = self.mcp_servers.get(server_name)
        if not server_url:
            raise ValueError(f"Unknown MCP server: {server_name}")
        
        tool_url = f"{server_url}/tools/{tool_name}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(tool_url, json=kwargs) as response:
                    if response.status == 200:
                        result = await response.text()
                        return result
                    else:
                        error_text = await response.text()
                        raise RuntimeError(f"Error calling MCP tool: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"[AsyncMCPTravelAgent] Error calling MCP tool {tool_name}: {e}")
            raise
    
    async def call_agent(self, agent_name: str, query: str, conversation_id: Optional[str] = None):
        """
        Call another agent with a query
        
        Args:
            agent_name: The name of the agent to call
            query: The query to send to the agent
            conversation_id: Optional conversation ID for tracking multi-turn conversations
            
        Returns:
            Agent response
        """
        import aiohttp
        
        if not self._initialized:
            await self.initialize()
        
        agent_url = self.agent_connections.get(agent_name)
        if not agent_url:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        # Create or retrieve conversation history
        if conversation_id is None:
            conversation_id = f"conv-{time.time()}"
        
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        # Prepare the message
        message_data = {
            "content": {
                "text": query,
                "type": "text"
            },
            "role": "user"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(agent_url, json=message_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Store in conversation history
                        self.conversation_history[conversation_id].append({
                            "query": query,
                            "response": result
                        })
                        
                        # Extract text from response
                        if "content" in result and "text" in result["content"]:
                            return result["content"]["text"]
                        elif "content" in result and "type" in result["content"]:
                            # Handle different content types
                            content_type = result["content"].get("type")
                            if content_type == "text":
                                return result["content"].get("text", "")
                            else:
                                return f"Received {content_type} response from {agent_name}"
                        else:
                            return str(result)
                    else:
                        error_text = await response.text()
                        raise RuntimeError(f"Error calling agent: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"[AsyncMCPTravelAgent] Error calling agent {agent_name}: {e}")
            raise
    
    async def process_function_call(self, function_call):
        """
        Process a function call
        
        Args:
            function_call: Function call information
            
        Returns:
            Function execution result
        """
        function_name = function_call.name
        # Extract parameters
        params = {param.name: param.value for param in function_call.parameters}
        
        # Process based on the function
        if function_name == "plan_trip":
            location = params.get("location", "London")
            days = params.get("days", 3)
            return await self._plan_trip(location, days)
        elif function_name == "suggest_activities":
            location = params.get("location", "London")
            weather_condition = params.get("weather_condition", None)
            return await self._suggest_activities(location, weather_condition)
        elif function_name == "get_travel_advisory":
            location = params.get("location", "London")
            return await self._get_travel_advisory(location)
        else:
            raise ValueError(f"Unknown function: {function_name}")
    
    async def handle_message_async(self, message: Message) -> Message:
        """
        Asynchronous message handler
        
        Args:
            message: Received A2A message
            
        Returns:
            Response message
        """
        # Initialize if needed
        if not self._initialized:
            await self.initialize()
        
        # Handle function calls
        if hasattr(message.content, "type") and message.content.type == "function_call":
            function_call = message.content.function_call
            
            try:
                # Process the function call
                result = await self.process_function_call(function_call)
                
                # Create response with the result
                return Message(
                    content=FunctionResponseContent(
                        name=function_call.name,
                        response=result
                    ),
                    role=MessageRole.AGENT
                )
            except Exception as e:
                # Return error message
                return Message(
                    content=TextContent(f"Error processing function {function_call.name}: {str(e)}"),
                    role=MessageRole.AGENT
                )
        
        # Regular message processing
        text = ""
        if hasattr(message.content, "text"):
            text = message.content.text
        elif isinstance(message.content, dict) and "text" in message.content:
            text = message.content["text"]
        
        # Process the message
        try:
            response_text = await self._process_travel_query(text)
            return Message(
                content=TextContent(response_text),
                role=MessageRole.AGENT
            )
        except Exception as e:
            # Return error message
            return Message(
                content=TextContent(f"Error processing message: {str(e)}"),
                role=MessageRole.AGENT
            )
    
    async def handle_task_async(self, task: Task) -> Task:
        """
        Asynchronous task handler
        
        Args:
            task: Task to handle
            
        Returns:
            Processed task
        """
        # Initialize if needed
        if not self._initialized:
            await self.initialize()
        
        # Extract query from task
        query = self._extract_query_from_task(task)
        
        # Process the query
        try:
            # Update task status to processing
            task.status = TaskStatus.PROCESSING
            task.state = TaskState(
                progress=0.1,
                status_message="Processing travel query..."
            )
            
            # Process the travel query
            response_text = await self._process_travel_query(query)
            
            # Update task with response
            task.response = Message(
                content=TextContent(response_text),
                role=MessageRole.AGENT
            )
            
            # Update task status to completed
            task.status = TaskStatus.COMPLETED
            task.state = TaskState(
                progress=1.0,
                status_message="Travel query processed successfully"
            )
        except Exception as e:
            # Update task status to failed
            error_message = f"Error processing travel task: {str(e)}"
            task.status = TaskStatus.FAILED
            task.state = TaskState(
                progress=0,
                status_message=error_message
            )
            task.response = Message(
                content=TextContent(error_message),
                role=MessageRole.AGENT
            )
        
        return task
    
    async def _process_travel_query(self, query: str) -> str:
        """
        Process a travel-related query
        
        Args:
            query: The query text
            
        Returns:
            Response text
        """
        # Extract location from query (simplified)
        location = self._extract_location(query)
        
        # Determine query type and process accordingly
        if any(keyword in query.lower() for keyword in ["plan", "trip", "visit", "itinerary"]):
            # Extract days from query (simplified)
            days = 3
            for word in query.split():
                if word.isdigit():
                    days = int(word)
                    break
            
            return await self._plan_trip(location, days)
        
        elif any(keyword in query.lower() for keyword in ["activity", "activities", "do", "recommendation"]):
            # Get weather first
            weather_info = await self._get_weather_for_location(location)
            return await self._suggest_activities(location, weather_info)
        
        elif any(keyword in query.lower() for keyword in ["advisory", "alert", "warning", "safe"]):
            return await self._get_travel_advisory(location)
        
        else:
            # Generic travel information
            # First, get weather for the location
            weather_info = await self._get_weather_for_location(location)
            
            # Then, provide basic travel info with weather
            return f"Here's some information about traveling to {location}:\n\n" \
                   f"Weather: {weather_info}\n\n" \
                   f"For a more specific response, try asking about planning a trip, recommended activities, or travel advisories for {location}."
    
    def _extract_location(self, query: str) -> str:
        """Extract location from query (simplified implementation)"""
        # List of common cities
        common_cities = ["london", "paris", "new york", "tokyo", "sydney"]
        
        # Check if any common city is in the query
        for city in common_cities:
            if city in query.lower():
                return city.title()
        
        # Log when no city is found
        logger.info(f"[AsyncMCPTravelAgent] No location found in query: '{query}', using default")
        
        # Default to London if no city found
        return "London"
    
    async def _get_weather_for_location(self, location: str) -> str:
        """Get weather information for a location from the weather agent"""
        logger.info(f"[AsyncMCPTravelAgent] Getting weather for location: '{location}'")
        try:
            # Call the weather agent
            weather_query = f"What's the weather in {location}?"
            weather_response = await self.call_agent("weather", weather_query)
            logger.info(f"[AsyncMCPTravelAgent] Received weather response for {location}: {weather_response[:100]}...")
            return weather_response
        except Exception as e:
            logger.error(f"[AsyncMCPTravelAgent] Error getting weather for {location}: {e}")
            return f"Unable to retrieve weather for {location} at this time."
    
    async def _plan_trip(self, location: str, days: int) -> str:
        """
        Plan a trip considering weather conditions
        
        Args:
            location: Destination
            days: Number of days
            
        Returns:
            Trip plan
        """
        # Get weather forecast from weather agent
        logger.info(f"[AsyncMCPTravelAgent] Planning {days}-day trip to {location}")
        
        # Format the city name (capitalize first letter, lowercase the rest)
        formatted_location = location.strip().title()
        logger.info(f"[AsyncMCPTravelAgent] Formatted location name: {formatted_location}")
        
        weather_query = f"What's the weather forecast for {formatted_location} for the next {days} days?"
        logger.info(f"[AsyncMCPTravelAgent] Querying weather agent with: '{weather_query}'")
        
        try:
            weather_forecast = await self.call_agent("weather", weather_query)
            logger.info(f"[AsyncMCPTravelAgent] Successfully received weather forecast for {formatted_location}")
        except Exception as e:
            logger.error(f"[AsyncMCPTravelAgent] Error getting weather forecast: {e}")
            logger.error(f"[AsyncMCPTravelAgent] Exception details: {str(e.__class__.__name__)} - {str(e)}")
            weather_forecast = "Weather forecast unavailable"
        
        # Generate trip plan based on weather and destination
        trip_plan = f"🧳 {days}-Day Trip Plan for {formatted_location} 🧳\n\n"
        trip_plan += f"Weather Forecast: {weather_forecast}\n\n"
        
        # Add day-by-day itinerary (simplified example)
        for day in range(1, days + 1):
            trip_plan += f"Day {day}:\n"
            if "rain" in weather_forecast.lower() or "rainy" in weather_forecast.lower():
                trip_plan += "  - Morning: Visit a museum or gallery\n"
                trip_plan += "  - Afternoon: Indoor shopping or local cafes\n"
                trip_plan += "  - Evening: Enjoy local cuisine at a restaurant\n"
            else:
                trip_plan += "  - Morning: Explore city landmarks\n"
                trip_plan += "  - Afternoon: Park visit or outdoor activities\n"
                trip_plan += "  - Evening: Sunset walk and dinner\n"
            trip_plan += "\n"
        
        trip_plan += "This plan adapts to weather conditions to ensure you have the best experience!"
        return trip_plan
    
    async def _suggest_activities(self, location: str, weather_condition: Optional[str] = None) -> str:
        """
        Suggest activities based on weather
        
        Args:
            location: Location
            weather_condition: Current weather condition or None to fetch it
            
        Returns:
            Activity suggestions
        """
        logger.info(f"[AsyncMCPTravelAgent] Suggesting activities for {location}")
        
        # Get weather if not provided
        if weather_condition is None:
            weather_query = f"What's the current weather in {location}?"
            try:
                weather_condition = await self.call_agent("weather", weather_query)
                logger.info(f"[AsyncMCPTravelAgent] Got weather condition for activities: {weather_condition[:100]}...")
            except Exception as e:
                logger.error(f"[AsyncMCPTravelAgent] Error getting weather for activities: {e}")
                weather_condition = "Weather information unavailable"
        
        # Determine activity type based on weather
        is_good_weather = any(keyword in weather_condition.lower() for keyword in 
                             ["sunny", "clear", "mild", "warm", "nice"])
        is_bad_weather = any(keyword in weather_condition.lower() for keyword in 
                            ["rain", "snow", "storm", "cold", "windy"])
        
        # Log the weather classification
        logger.info(f"[AsyncMCPTravelAgent] Weather classification - Good: {is_good_weather}, Bad: {is_bad_weather}")
        
        # Generate activity suggestions
        suggestions = f"🌈 Activity Suggestions for {location} 🌈\n\n"
        suggestions += f"Current Weather: {weather_condition}\n\n"
        
        if is_good_weather:
            suggestions += "Outdoor Activities:\n"
            suggestions += "  - City walking tour\n"
            suggestions += "  - Visit to local parks\n"
            suggestions += "  - Outdoor dining\n"
            suggestions += "  - Sightseeing at landmarks\n"
            suggestions += "  - Boat tour (if applicable)\n"
        elif is_bad_weather:
            suggestions += "Indoor Activities:\n"
            suggestions += "  - Museum visits\n"
            suggestions += "  - Shopping malls\n"
            suggestions += "  - Indoor attractions\n"
            suggestions += "  - Local cafes and restaurants\n"
            suggestions += "  - Theater or cinema\n"
        else:
            # Neutral or unknown weather
            suggestions += "Recommended Activities:\n"
            suggestions += "  - Both indoor and outdoor options available\n"
            suggestions += "  - Cultural venues\n"
            suggestions += "  - Local cuisine exploration\n"
            suggestions += "  - Landmark visits\n"
            suggestions += "  - Shopping districts\n"
        
        return suggestions
    
    async def _get_travel_advisory(self, location: str) -> str:
        """
        Get travel advisories including weather alerts
        
        Args:
            location: Location
            
        Returns:
            Travel advisory information
        """
        logger.info(f"[AsyncMCPTravelAgent] Getting travel advisory for {location}")
        
        # Get weather alerts from weather agent
        weather_query = f"Are there any weather alerts for {location}?"
        try:
            weather_alerts = await self.call_agent("weather", weather_query)
            logger.info(f"[AsyncMCPTravelAgent] Received weather alerts for {location}")
        except Exception as e:
            logger.error(f"[AsyncMCPTravelAgent] Error getting weather alerts: {e}")
            weather_alerts = "Weather alert information unavailable"
        
        # Generate travel advisory
        advisory = f"🚨 Travel Advisory for {location} 🚨\n\n"
        advisory += f"Weather Alerts: {weather_alerts}\n\n"
        
        # Add generic travel advice (simplified example)
        advisory += "General Travel Tips:\n"
        advisory += "  - Always carry identification\n"
        advisory += "  - Keep emergency contact information handy\n"
        advisory += "  - Stay informed about local news\n"
        advisory += "  - Follow local regulations and customs\n"
        
        return advisory 