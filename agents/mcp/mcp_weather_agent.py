"""
FastAPI based MCP-enabled weather agent implementation.
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

class AsyncMCPWeatherAgent(FastAPIAgent):
    """Weather agent that uses MCP for enhanced capabilities with FastAPI backend."""
    
    def __init__(self, mcp_servers: Optional[Dict[str, str]] = None, **kwargs):
        """Initialize the MCP-enabled weather agent with FastAPI backend."""
        agent_card = AgentCard(
            name="MCP Weather Agent (FastAPI)",
            description="Provides current weather information and forecasts with enhanced MCP capabilities using FastAPI",
            url="http://localhost:0",  # Will be updated when server starts
            version="1.0.0",
            skills=[
                AgentSkill(
                    name="Current Weather",
                    description="Get current weather conditions for a location",
                    tags=["weather", "current", "temperature", "conditions", "forecast"],
                    examples=["What's the weather in London?", "Is it raining in Tokyo?"]
                ),
                AgentSkill(
                    name="Weather Forecast",
                    description="Get weather forecast for the coming days",
                    tags=["weather", "forecast", "prediction", "upcoming", "future"],
                    examples=["What's the forecast for Paris?", "Will it rain in New York tomorrow?"]
                ),
                AgentSkill(
                    name="Weather Map",
                    description="Generate a weather map for a location",
                    tags=["weather", "map", "visualization"],
                    examples=["Show me a weather map of Europe", "Generate a precipitation map for Japan"]
                )
            ]
        )
        
        # Set up default MCP servers if none provided
        if mcp_servers is None:
            mcp_servers = {
                # Example MCP server configurations
                "weather": "http://localhost:5001",
                "maps": "http://localhost:5002"
            }
        
        # MCP-related configuration and initialization
        self.mcp_servers = mcp_servers
        self.mcp_tools = {}  # Tools discovered from servers
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
            self._initialized = True
            logger.info(f"[AsyncMCPWeatherAgent] Initialized with MCP servers: {self.mcp_servers}")
        except Exception as e:
            logger.error(f"[AsyncMCPWeatherAgent] Failed to initialize: {e}")
    
    async def _discover_mcp_tools(self):
        """Discover available MCP tools"""
        # This should be replaced with actual MCP client code
        # The following is a simplified implementation for demonstration
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
                                
                            logger.info(f"[AsyncMCPWeatherAgent] Discovered {len(self.mcp_tools[server_name])} tools from {server_name}")
                        else:
                            logger.warning(f"[AsyncMCPWeatherAgent] Failed to get tools from {server_name}: {response.status}")
            except Exception as e:
                logger.error(f"[AsyncMCPWeatherAgent] Error discovering tools from {server_name}: {e}")
    
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
        # This should be replaced with actual MCP client code
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
            logger.error(f"[AsyncMCPWeatherAgent] Error calling MCP tool {tool_name}: {e}")
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
        if function_name == "get_current_weather":
            location = params.get("location", "London")
            return await self._get_current_weather_from_mcp(location)
        elif function_name == "get_weather_forecast":
            location = params.get("location", "London")
            days = params.get("days", 3)
            return await self._get_weather_forecast_from_mcp(location, days)
        elif function_name == "generate_weather_map":
            location = params.get("location", "London")
            map_type = params.get("type", "temperature")
            return await self.call_mcp_tool("maps", "generate_weather_map", location=location, type=map_type)
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
                    role=MessageRole.AGENT,
                    parent_message_id=message.message_id,
                    conversation_id=message.conversation_id
                )
            except Exception as e:
                # Handle function call errors
                logger.error(f"Error processing function call: {e}")
                return Message(
                    content=TextContent(text=f"Error processing function call: {str(e)}"),
                    role=MessageRole.AGENT,
                    parent_message_id=message.message_id,
                    conversation_id=message.conversation_id
                )
        
        # Handle text messages
        if hasattr(message.content, "text"):
            query = message.content.text
            
            # Handle map requests
            if "map" in query.lower():
                try:
                    city = self._extract_city(query)
                    logger.info(f"[AsyncMCPWeatherAgent] Generating weather map for {city}...")
                    
                    # Generate weather map using MCP tool
                    map_data = await self.call_mcp_tool(
                        server_name="maps", 
                        tool_name="generate_weather_map",
                        location=city
                    )
                    
                    # Parse map data and format for display
                    try:
                        map_json = json.loads(map_data)
                        if isinstance(map_json, dict) and "content" in map_json and len(map_json["content"]) > 0:
                            map_text = map_json["content"][0].get("text", "")
                        else:
                            map_text = str(map_json)
                    except json.JSONDecodeError:
                        # If not valid JSON, use as-is
                        map_text = map_data
                    
                    # Return response with formatted map data
                    return Message(
                        content=TextContent(text=f"Weather map for {city}:\n\n{map_text}"),
                        role=MessageRole.AGENT,
                        parent_message_id=message.message_id,
                        conversation_id=message.conversation_id
                    )
                except Exception as e:
                    logger.error(f"Error generating weather map: {e}")
                    # Fallback in case of error
            
            # Handle weather information requests
            if any(term in query.lower() for term in ["weather", "temperature", "forecast", "rain"]):
                try:
                    city = self._extract_city(query)
                    
                    # Determine if this is a forecast request
                    if any(term in query.lower() for term in ["forecast", "prediction", "tomorrow", "next", "future"]):
                        days = 3  # Default 3 days
                        forecast = await self._get_weather_forecast_from_mcp(city, days)
                        
                        return Message(
                            content=TextContent(text=forecast),
                            role=MessageRole.AGENT,
                            parent_message_id=message.message_id,
                            conversation_id=message.conversation_id
                        )
                    else:
                        # Get current weather
                        weather = await self._get_current_weather_from_mcp(city)
                        
                        return Message(
                            content=TextContent(text=weather),
                            role=MessageRole.AGENT,
                            parent_message_id=message.message_id,
                            conversation_id=message.conversation_id
                        )
                except Exception as e:
                    logger.error(f"Error getting weather information: {e}")
                    # Fallback in case of error
        
        # Default response
        return Message(
            content=TextContent(text=f"I'm a weather agent. You can ask about weather conditions, forecasts, or request weather maps."),
            role=MessageRole.AGENT,
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id
        )
    
    async def handle_task_async(self, task: Task) -> Task:
        """
        Asynchronous task handler
        
        Args:
            task: Received A2A task
            
        Returns:
            Processed task
        """
        # Initialize if needed
        if not self._initialized:
            await self.initialize()
        
        # Extract query from task
        query = self._extract_query_from_task(task)
        
        # Handle map requests
        if "map" in query.lower():
            try:
                city = self._extract_city(query)
                logger.info(f"[AsyncMCPWeatherAgent] Generating weather map for {city}...")
                
                # Generate weather map using MCP tool
                map_data = await self.call_mcp_tool(
                    server_name="maps", 
                    tool_name="generate_weather_map",
                    location=city
                )
                
                # Parse map data and format for display
                try:
                    map_json = json.loads(map_data)
                    if isinstance(map_json, dict) and "content" in map_json and len(map_json["content"]) > 0:
                        map_text = map_json["content"][0].get("text", "")
                    else:
                        map_text = str(map_json)
                except json.JSONDecodeError:
                    # If not valid JSON, use as-is
                    map_text = map_data
                
                # Update the task
                task.artifacts = [{
                    "parts": [{"type": "text", "text": f"Weather map for {city}:\n\n{map_text}"}]
                }]
                task.status = TaskStatus(state=TaskState.COMPLETED)
                return task
            except Exception as e:
                logger.error(f"Error generating weather map: {e}")
                # Fallback in case of error
        
        # Process task as a message and reflect results in the task
        try:
            # Extract message from task
            message_data = task.message or {}
            
            # Convert to Message object
            message = None
            
            if isinstance(message_data, dict):
                # Check for Google A2A format
                if "parts" in message_data and "role" in message_data and "content" not in message_data:
                    try:
                        message = Message.from_google_a2a(message_data)
                    except Exception:
                        pass
                
                # Try standard format
                if message is None:
                    try:
                        message = Message.from_dict(message_data)
                    except Exception:
                        # Create basic message
                        text = ""
                        if "content" in message_data and isinstance(message_data["content"], dict):
                            content = message_data["content"]
                            if "text" in content:
                                text = content["text"]
                        elif "parts" in message_data:
                            for part in message_data["parts"]:
                                if isinstance(part, dict) and part.get("type") == "text" and "text" in part:
                                    text = part["text"]
                                    break
                        
                        message = Message(
                            content=TextContent(text=text),
                            role=MessageRole.USER
                        )
            else:
                message = message_data
            
            # Call message handler
            response = await self.handle_message_async(message)
            
            # Reflect response content in the task
            if hasattr(response, "content"):
                content_type = getattr(response.content, "type", None)
                
                if content_type == "text":
                    task.artifacts = [{
                        "parts": [{"type": "text", "text": response.content.text}]
                    }]
                elif content_type == "function_response":
                    task.artifacts = [{
                        "parts": [
                            {"type": "text", "text": f"Function response from {response.content.name}:"},
                            {"type": "text", "text": response.content.response}
                        ]
                    }]
                elif content_type == "error":
                    task.artifacts = [{
                        "parts": [{"type": "error", "message": response.content.message}]
                    }]
                else:
                    task.artifacts = [{
                        "parts": [{"type": "text", "text": str(response.content)}]
                    }]
            else:
                task.artifacts = [{
                    "parts": [{"type": "text", "text": str(response)}]
                }]
            
            # Mark task as completed
            task.status = TaskStatus(state=TaskState.COMPLETED)
            return task
        except Exception as e:
            # Error handling
            logger.error(f"[AsyncMCPWeatherAgent] Error handling task: {e}")
            task.artifacts = [{
                "parts": [{"type": "error", "message": f"Error processing task: {str(e)}"}]
            }]
            task.status = TaskStatus(state=TaskState.FAILED)
            return task
    
    def _extract_city(self, query: str) -> str:
        """Extract city name from query"""
        query = query.lower()
        
        # Check for city names in the query
        cities = ["london", "paris", "new york", "tokyo", "sydney", 
                 "berlin", "rome", "madrid", "cairo", "mumbai"]
        
        for city in cities:
            if city in query:
                return city.title()
        
        # Log when no city is found
        logger.info(f"[AsyncMCPWeatherAgent] No city found in query: '{query}', using default")
        
        # Default city if none found
        return "London"
    
    async def _get_current_weather_from_mcp(self, city: str) -> str:
        """Get current weather for a city from MCP server"""
        logger.info(f"[AsyncMCPWeatherAgent] Getting current weather for: '{city}'")
        try:
            # Call MCP tool to get current weather
            weather_json = await self.call_mcp_tool(
                server_name="weather",
                tool_name="get_current_weather",
                location=city.lower()
            )
            
            # Parse JSON response
            weather_data = json.loads(weather_json)
            
            # Format weather information
            return f"""Current Weather in {weather_data['location']}:
Condition: {weather_data['condition']}
Temperature: {weather_data['temperature']}°{weather_data['temperature_unit'].upper()}
Humidity: {weather_data['humidity']}%
Wind Speed: {weather_data['wind_speed']} {weather_data['wind_unit']}"""
        except Exception as e:
            logger.error(f"[AsyncMCPWeatherAgent] Error getting current weather from MCP for '{city}': {e}")
            return f"Sorry, I couldn't get the current weather information for {city}. Available cities are: London, Paris, New York, Tokyo, Sydney."
    
    async def _get_weather_forecast_from_mcp(self, city: str, days: int = 3) -> str:
        """Get weather forecast for a city from MCP server"""
        logger.info(f"[AsyncMCPWeatherAgent] Getting {days}-day forecast for: '{city}'")
        try:
            # Call MCP tool to get weather forecast
            forecast_json = await self.call_mcp_tool(
                server_name="weather",
                tool_name="get_weather_forecast",
                location=city.lower(),
                days=days
            )
            
            # Parse JSON response
            forecast_data = json.loads(forecast_json)
            
            # Format forecast as text
            result = f"{days}-Day Weather Forecast for {forecast_data['location']}:\n\n"
            for day in forecast_data['forecast']:
                result += f"{day['date']}: {day['condition']}, High: {day['temperature_high']}°C, Low: {day['temperature_low']}°C\n"
            
            return result
        except Exception as e:
            logger.error(f"[AsyncMCPWeatherAgent] Error getting weather forecast from MCP for '{city}': {e}")
            return f"Sorry, I couldn't get the weather forecast for {city}. Available cities are: London, Paris, New York, Tokyo, Sydney." 