"""
FastAPI based MCP-enabled travel agent implementation with weather agent integration.
"""

import time
import json
from typing import Dict, Optional
from datetime import datetime

from python_a2a import (
    AgentCard,
    AgentSkill,
    Message,
    MessageRole,
    Task,
    TaskState,
    TaskStatus,
    TextContent,
)

from agents.mcp.mcp_agent import BaseMCPAgent
from config import logger


class MCPTravelAgent(BaseMCPAgent):
    """Travel agent that uses MCP for enhanced capabilities with FastAPI backend and integrates with other agents."""

    def __init__(
        self,
        mcp_servers: Optional[Dict[str, str]] = None,
        agent_connections: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
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
                    examples=[
                        "Plan a 3-day trip to London considering weather",
                        "What activities can I do in Tokyo based on weather?",
                    ],
                ),
                AgentSkill(
                    name="Weather-Based Activities",
                    description="Suggest activities based on weather forecast",
                    tags=[
                        "activities",
                        "weather",
                        "recommendations",
                        "outdoor",
                        "indoor",
                    ],
                    examples=[
                        "What should I do in Paris tomorrow if it rains?",
                        "Outdoor activities in Sydney based on weather",
                    ],
                ),
                AgentSkill(
                    name="Travel Advisory",
                    description="Get travel advisories including weather alerts",
                    tags=["advisory", "warnings", "safety", "alerts"],
                    examples=[
                        "Any travel alerts for New York this weekend?",
                        "Is it safe to travel to London next week?",
                    ],
                ),
            ],
        )

        # Set up default MCP servers if none provided
        if mcp_servers is None:
            mcp_servers = {
                # Example MCP server configurations
                "travel": "http://localhost:5003",
                "maps": "http://localhost:5002",
            }

        # Set up agent connections if none provided
        if agent_connections is None:
            agent_connections = {
                # Default connection to weather agent
                "weather": "http://localhost:5000"
            }

        # Agent connections for inter-agent communication
        self.agent_connections = agent_connections
        self.conversation_history = {}  # Store conversation history with other agents

        # Initialize the BaseMCPAgent
        super().__init__(agent_card=agent_card, mcp_servers=mcp_servers, **kwargs)

    async def initialize(self):
        """Initialize MCP servers, discover available tools, and verify agent connections"""
        # First, initialize MCP servers (parent implementation)
        await super().initialize()

        if not self._initialized:
            return

        try:
            # Verify agent connections
            await self._verify_agent_connections()
            logger.info(
                f"[MCPTravelAgent] Connected to agents: {self.agent_connections}"
            )
        except Exception as e:
            logger.error(f"[MCPTravelAgent] Failed to verify agent connections: {e}")

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
                            logger.info(
                                f"[MCPTravelAgent] Connected to {agent_name} agent: {agent_info.get('name', 'Unknown')}"
                            )
                        else:
                            logger.warning(
                                f"[MCPTravelAgent] Failed to connect to {agent_name} agent: {response.status}"
                            )
            except Exception as e:
                logger.error(
                    f"[MCPTravelAgent] Error connecting to {agent_name} agent: {e}"
                )

    async def call_agent(
        self, agent_name: str, query: str, conversation_id: Optional[str] = None
    ):
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
        message_data = {"content": {"text": query, "type": "text"}, "role": "user"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(agent_url, json=message_data) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Store in conversation history
                        self.conversation_history[conversation_id].append(
                            {"query": query, "response": result}
                        )

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
                        raise RuntimeError(
                            f"Error calling agent: {response.status} - {error_text}"
                        )
        except Exception as e:
            logger.error(f"[MCPTravelAgent] Error calling agent {agent_name}: {e}")
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
        elif function_name == "get_destination_info":
            location = params.get("location", "London")
            return await self._get_destination_info(location)
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

        # Handle function calls using parent implementation
        if hasattr(message.content, "type") and message.content.type == "function_call":
            return await super().handle_message_async(message)

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
                role=MessageRole.AGENT,
                parent_message_id=message.message_id,
                conversation_id=message.conversation_id,
            )
        except Exception as e:
            # Return error message
            return Message(
                content=TextContent(f"Error processing message: {str(e)}"),
                role=MessageRole.AGENT,
                parent_message_id=message.message_id,
                conversation_id=message.conversation_id,
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
                progress=0.1, status_message="Processing travel query..."
            )

            # Process the travel query
            response_text = await self._process_travel_query(query)

            # Update task with response
            task.response = Message(
                content=TextContent(response_text), role=MessageRole.AGENT
            )

            # Update task status to completed
            task.status = TaskStatus.COMPLETED
            task.state = TaskState(
                progress=1.0, status_message="Travel query processed successfully"
            )
        except Exception as e:
            # Update task status to failed
            error_message = f"Error processing travel task: {str(e)}"
            task.status = TaskStatus.FAILED
            task.state = TaskState(progress=0, status_message=error_message)
            task.response = Message(
                content=TextContent(error_message), role=MessageRole.AGENT
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
        if any(
            keyword in query.lower()
            for keyword in ["plan", "trip", "visit", "itinerary"]
        ):
            # Extract days from query (simplified)
            days = 3
            for word in query.split():
                if word.isdigit():
                    days = int(word)
                    break

            return await self._plan_trip(location, days)

        elif any(
            keyword in query.lower()
            for keyword in ["activity", "activities", "do", "recommendation"]
        ):
            # Get weather first
            weather_info = await self._get_weather_for_location(location)
            return await self._suggest_activities(location, weather_info)

        elif any(
            keyword in query.lower()
            for keyword in ["advisory", "alert", "warning", "safe"]
        ):
            return await self._get_travel_advisory(location)

        elif any(
            keyword in query.lower()
            for keyword in ["info", "information", "tell me about", "details"]
        ):
            return await self._get_destination_info(location)

        else:
            try:
                # First, get weather for the location
                weather_info = await self._get_weather_for_location(location)

                # Get destination information from MCP
                destination_info = await self._get_destination_info_summary(location)

                # Then, provide basic travel info with weather
                return (
                    f"Here's some information about traveling to {location}:\n\n"
                    f"Weather: {weather_info}\n\n"
                    f"{destination_info}\n\n"
                    f"For a more specific response, try asking about planning a trip, recommended activities, or travel advisories for {location}."
                )
            except Exception as e:
                logger.error(
                    f"[MCPTravelAgent] Error processing general travel query: {e}"
                )
                return f"Sorry, I couldn't get travel information for {location}. The MCP service might be unavailable."

    def _extract_location(self, query: str) -> str:
        """Extract location from query (simplified implementation)"""
        # List of common cities
        common_cities = ["london", "paris", "new york", "tokyo", "sydney"]

        # Check if any common city is in the query
        for city in common_cities:
            if city in query.lower():
                return city.title()

        # Log when no city is found
        logger.info(
            f"[MCPTravelAgent] No location found in query: '{query}', using default"
        )

        # Default to London if no city found
        return "London"

    async def _get_weather_for_location(self, location: str) -> str:
        """Get weather information for a location from the weather agent"""
        logger.info(f"[MCPTravelAgent] Getting weather for location: '{location}'")
        try:
            # Format the location name properly
            formatted_location = location.strip().title()

            # Call the weather agent
            weather_query = f"What's the weather in {formatted_location}?"
            logger.info(
                f"[MCPTravelAgent] Querying weather agent with: '{weather_query}'"
            )

            weather_response = await self.call_agent("weather", weather_query)

            if weather_response:
                logger.info(
                    f"[MCPTravelAgent] Received weather response for {formatted_location}: {weather_response[:100]}..."
                )
                return weather_response
            else:
                logger.warning(
                    f"[MCPTravelAgent] Empty weather response for {formatted_location}"
                )
                return f"Weather information for {formatted_location} is currently unavailable."

        except Exception as e:
            logger.error(f"[MCPTravelAgent] Error getting weather for {location}: {e}")
            logger.exception("Detailed exception information:")
            return f"Unable to retrieve weather for {location} at this time. The weather service might be unavailable."

    async def _get_destination_info(self, location: str) -> str:
        """
        Get comprehensive destination information from MCP server

        Args:
            location: Destination name

        Returns:
            Formatted destination information
        """
        logger.info(f"[MCPTravelAgent] Getting destination information for {location}")
        try:
            # Call MCP tool to get destination information
            dest_json = await self.call_mcp_tool(
                server_name="travel",
                tool_name="get_destination_info",
                location=location,
            )

            # Debug log the raw response
            logger.debug(
                f"[MCPTravelAgent] Raw MCP destination info response: {dest_json[:200]}..."
            )

            # Parse JSON response
            dest_data = json.loads(dest_json)
            logger.info(
                f"[MCPTravelAgent] Successfully received destination data for {location}"
            )

            # Check if response contains content (MCP servers might wrap responses)
            if isinstance(dest_data, dict) and "content" in dest_data:
                if (
                    isinstance(dest_data["content"], list)
                    and len(dest_data["content"]) > 0
                ):
                    # Extract the first content item's text
                    content_item = dest_data["content"][0]
                    if isinstance(content_item, dict) and "text" in content_item:
                        try:
                            dest_data = json.loads(content_item["text"])
                        except json.JSONDecodeError:
                            # If not valid JSON, use as is
                            return content_item["text"]
                    else:
                        return str(content_item)
                elif isinstance(dest_data["content"], str):
                    # Try to parse content as JSON
                    try:
                        dest_data = json.loads(dest_data["content"])
                    except json.JSONDecodeError:
                        return dest_data["content"]

            # Now check if the expected keys exist
            if "location" not in dest_data:
                logger.error(
                    "[MCPTravelAgent] Missing 'location' key in destination info response"
                )
                dest_data["location"] = location.strip().title()

            # Check for required data sections
            required_sections = [
                "attractions",
                "indoor_activities",
                "outdoor_activities",
                "cuisines",
                "transportation",
                "language",
                "currency",
                "timezone",
            ]

            for section in required_sections:
                if section not in dest_data:
                    logger.error(
                        f"[MCPTravelAgent] Missing '{section}' in destination info"
                    )
                    if section in ["language", "currency", "timezone"]:
                        dest_data[section] = "Information not available"
                    else:
                        dest_data[section] = ["Information not available"]

            if "safety_level" not in dest_data:
                dest_data["safety_level"] = "Information not available"

            # Format destination information
            result = f"📍 Destination Guide: {dest_data['location']} 📍\n\n"

            result += "🏛️ Top Attractions:\n"
            for attraction in dest_data["attractions"]:
                result += f"  • {attraction}\n"

            result += "\n🏠 Indoor Activities:\n"
            for activity in dest_data["indoor_activities"]:
                result += f"  • {activity}\n"

            result += "\n🌳 Outdoor Activities:\n"
            for activity in dest_data["outdoor_activities"]:
                result += f"  • {activity}\n"

            result += "\n🍽️ Local Cuisine: " + ", ".join(dest_data["cuisines"]) + "\n"
            result += (
                "🚌 Getting Around: " + ", ".join(dest_data["transportation"]) + "\n"
            )
            result += f"🗣️ Language: {dest_data['language']}\n"
            result += f"💰 Currency: {dest_data['currency']}\n"
            result += f"🕒 Timezone: {dest_data['timezone']}\n"
            result += f"🛡️ Safety Level: {dest_data['safety_level']}\n"

            return result
        except Exception as e:
            logger.error(
                f"[MCPTravelAgent] Error getting destination info from MCP: {e}"
            )
            logger.exception("Detailed exception information:")
            return f"Error: Unable to retrieve destination information for {location}. The MCP service might be unavailable."

    async def _get_destination_info_summary(self, location: str) -> str:
        """
        Get summary destination information from MCP server (shorter version)

        Args:
            location: Destination name

        Returns:
            Summarized destination information
        """
        try:
            # Call MCP tool to get destination information
            dest_json = await self.call_mcp_tool(
                server_name="travel",
                tool_name="get_destination_info",
                location=location,
            )

            # Parse JSON response
            dest_data = json.loads(dest_json)

            # Check if response contains content (MCP servers might wrap responses)
            if isinstance(dest_data, dict) and "content" in dest_data:
                if (
                    isinstance(dest_data["content"], list)
                    and len(dest_data["content"]) > 0
                ):
                    # Extract the first content item's text
                    content_item = dest_data["content"][0]
                    if isinstance(content_item, dict) and "text" in content_item:
                        try:
                            dest_data = json.loads(content_item["text"])
                        except json.JSONDecodeError:
                            # Cannot parse summary, raise exception
                            raise ValueError("Cannot parse destination data")
                    else:
                        raise ValueError("Invalid content format")
                elif isinstance(dest_data["content"], str):
                    # Try to parse content as JSON
                    try:
                        dest_data = json.loads(dest_data["content"])
                    except json.JSONDecodeError:
                        raise ValueError("Cannot parse destination data content")

            # Validate required fields
            if "location" not in dest_data:
                dest_data["location"] = location.strip().title()

            if "attractions" not in dest_data or not isinstance(
                dest_data["attractions"], list
            ):
                dest_data["attractions"] = ["Information not available"]

            if "language" not in dest_data:
                dest_data["language"] = "Information not available"

            if "currency" not in dest_data:
                dest_data["currency"] = "Information not available"

            # Create a shorter summary
            summary = f"Destination Overview: {dest_data['location']}\n"
            summary += (
                f"Top attractions include {', '.join(dest_data['attractions'][:3])}\n"
            )
            summary += f"Local language: {dest_data['language']}, Currency: {dest_data['currency']}"

            return summary
        except Exception as e:
            logger.error(
                f"[MCPTravelAgent] Error getting destination summary from MCP: {e}"
            )
            logger.exception("Detailed exception information:")
            raise e  # Re-throw the exception to be handled by the caller

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
        logger.info(f"[MCPTravelAgent] Planning {days}-day trip to {location}")

        # Format the city name (capitalize first letter, lowercase the rest)
        formatted_location = location.strip().title()
        logger.info(f"[MCPTravelAgent] Formatted location name: {formatted_location}")

        # Get weather forecast from weather agent
        try:
            weather_query = f"What's the weather forecast for {formatted_location} for the next {days} days?"
            logger.info(
                f"[MCPTravelAgent] Querying weather agent with: '{weather_query}'"
            )
            weather_forecast = await self.call_agent("weather", weather_query)
            logger.info(
                f"[MCPTravelAgent] Successfully received weather forecast for {formatted_location}"
            )
        except Exception as e:
            logger.error(f"[MCPTravelAgent] Error getting weather forecast: {e}")
            logger.error(
                f"[MCPTravelAgent] Exception details: {str(e.__class__.__name__)} - {str(e)}"
            )
            weather_forecast = "Weather forecast unavailable"

        # Get trip itinerary from MCP server with weather consideration
        try:
            # Extract weather condition (simplified)
            weather_condition = None
            if weather_forecast != "Weather forecast unavailable":
                if "rain" in weather_forecast.lower():
                    weather_condition = "Rainy"
                elif (
                    "sun" in weather_forecast.lower()
                    or "clear" in weather_forecast.lower()
                ):
                    weather_condition = "Sunny"

            # Call MCP tool to create trip itinerary
            itinerary_json = await self.call_mcp_tool(
                server_name="travel",
                tool_name="create_trip_itinerary",
                location=formatted_location,
                days=days,
                weather_condition=weather_condition,
            )

            # Debug log the raw response
            logger.debug(
                f"[MCPTravelAgent] Raw MCP response: {itinerary_json[:200]}..."
            )

            # Parse JSON response
            itinerary_data = json.loads(itinerary_json)
            logger.info(
                f"[MCPTravelAgent] Successfully received itinerary for {formatted_location}"
            )

            # Check if response contains content (MCP servers might wrap responses)
            if isinstance(itinerary_data, dict) and "content" in itinerary_data:
                if (
                    isinstance(itinerary_data["content"], list)
                    and len(itinerary_data["content"]) > 0
                ):
                    # Extract the first content item's text
                    content_item = itinerary_data["content"][0]
                    if isinstance(content_item, dict) and "text" in content_item:
                        # If it's a JSON string, parse it
                        try:
                            itinerary_data = json.loads(content_item["text"])
                        except json.JSONDecodeError:
                            # If not valid JSON, use as is
                            return content_item["text"]
                    else:
                        return str(content_item)
                elif isinstance(itinerary_data["content"], str):
                    # If content is a string, try to parse as JSON
                    try:
                        itinerary_data = json.loads(itinerary_data["content"])
                    except json.JSONDecodeError:
                        # If not valid JSON, use as is
                        return itinerary_data["content"]

            # Now check if the expected keys exist
            if "location" not in itinerary_data:
                logger.error(
                    f"[MCPTravelAgent] Missing 'location' key in response: {str(itinerary_data)[:200]}..."
                )
                itinerary_data["location"] = formatted_location

            if "weather_consideration" not in itinerary_data:
                itinerary_data["weather_consideration"] = (
                    weather_condition or "Not specified"
                )

            if "itinerary" not in itinerary_data:
                logger.error("[MCPTravelAgent] Missing 'itinerary' key in response")
                return (
                    f"Error: Invalid response format from MCP service for {location}."
                )

            if "tips" not in itinerary_data:
                itinerary_data["tips"] = [
                    "Check local weather before heading out",
                    "Research local customs and traditions",
                    "Have emergency contacts saved",
                ]

            # Format the itinerary
            trip_plan = (
                f"🧳 {days}-Day Trip Plan for {itinerary_data['location']} 🧳\n\n"
            )
            trip_plan += (
                f"Weather Consideration: {itinerary_data['weather_consideration']}\n\n"
            )

            # Add daily itinerary
            for day in itinerary_data["itinerary"]:
                # Verify day has required fields
                if not all(
                    k in day for k in ["day", "date", "morning", "afternoon", "evening"]
                ):
                    logger.warning(
                        f"[MCPTravelAgent] Day missing required fields: {day}"
                    )
                    continue

                trip_plan += f"Day {day['day']} ({day['date']}):\n"

                # Handle morning activities safely
                if (
                    isinstance(day.get("morning"), dict)
                    and "activity" in day["morning"]
                ):
                    activity_type = day["morning"].get("type", "activity")
                    trip_plan += (
                        f"  - Morning: {day['morning']['activity']} ({activity_type})\n"
                    )
                else:
                    trip_plan += "  - Morning: Free time\n"

                # Handle afternoon activities safely
                if (
                    isinstance(day.get("afternoon"), dict)
                    and "activity" in day["afternoon"]
                ):
                    activity_type = day["afternoon"].get("type", "activity")
                    trip_plan += f"  - Afternoon: {day['afternoon']['activity']} ({activity_type})\n"
                else:
                    trip_plan += "  - Afternoon: Free time\n"

                # Handle evening activities safely
                if (
                    isinstance(day.get("evening"), dict)
                    and "activity" in day["evening"]
                ):
                    trip_plan += f"  - Evening: {day['evening']['activity']}\n"
                elif isinstance(day.get("evening"), str):
                    trip_plan += f"  - Evening: {day['evening']}\n"
                else:
                    trip_plan += "  - Evening: Free time\n"

                # Add transportation tip if available
                if "transportation_tip" in day:
                    trip_plan += f"  - {day['transportation_tip']}\n"

                trip_plan += "\n"

            # Add tips
            trip_plan += "Tips:\n"
            for tip in itinerary_data["tips"]:
                trip_plan += f"  • {tip}\n"

            return trip_plan
        except Exception as e:
            logger.error(
                f"[MCPTravelAgent] Error creating trip itinerary from MCP: {e}"
            )
            logger.exception("Detailed exception information:")
            return f"Error: Unable to plan a trip to {location}. The MCP service might be unavailable."

    async def _suggest_activities(
        self, location: str, weather_condition: Optional[str] = None
    ) -> str:
        """
        Suggest activities based on weather

        Args:
            location: Location
            weather_condition: Current weather condition or None to fetch it

        Returns:
            Activity suggestions
        """
        logger.info(f"[MCPTravelAgent] Suggesting activities for {location}")

        # Get weather if not provided
        if weather_condition is None:
            try:
                weather_query = f"What's the current weather in {location}?"
                weather_condition = await self.call_agent("weather", weather_query)
                logger.info(
                    f"[MCPTravelAgent] Got weather condition for activities: {weather_condition[:100]}..."
                )
            except Exception as e:
                logger.error(
                    f"[MCPTravelAgent] Error getting weather for activities: {e}"
                )
                weather_condition = "Weather information unavailable"

        # Use MCP tool to get activity suggestions based on weather
        try:
            # Format the location name
            formatted_location = location.strip().title()

            # Call MCP tool for activity suggestions
            activities_json = await self.call_mcp_tool(
                server_name="travel",
                tool_name="suggest_activities",
                location=formatted_location,
                weather_condition=weather_condition,
            )

            # Debug log the raw response
            logger.debug(
                f"[MCPTravelAgent] Raw MCP activities response: {activities_json[:200]}..."
            )

            # Parse JSON response
            activities_data = json.loads(activities_json)
            logger.info(
                f"[MCPTravelAgent] Successfully received activity suggestions for {formatted_location}"
            )

            # Check if response contains content (MCP servers might wrap responses)
            if isinstance(activities_data, dict) and "content" in activities_data:
                if (
                    isinstance(activities_data["content"], list)
                    and len(activities_data["content"]) > 0
                ):
                    # Extract the first content item's text
                    content_item = activities_data["content"][0]
                    if isinstance(content_item, dict) and "text" in content_item:
                        try:
                            activities_data = json.loads(content_item["text"])
                        except json.JSONDecodeError:
                            # If not valid JSON, use as is
                            return content_item["text"]
                    else:
                        return str(content_item)
                elif isinstance(activities_data["content"], str):
                    # Try to parse content as JSON
                    try:
                        activities_data = json.loads(activities_data["content"])
                    except json.JSONDecodeError:
                        return activities_data["content"]

            # Now check if the expected keys exist
            if "location" not in activities_data:
                logger.error(
                    "[MCPTravelAgent] Missing 'location' key in activities response"
                )
                activities_data["location"] = formatted_location

            if "weather_condition" not in activities_data:
                activities_data["weather_condition"] = weather_condition

            if "recommended_activity_type" not in activities_data:
                activities_data["recommended_activity_type"] = "Recommended"

            if (
                "top_activities" not in activities_data
                or not activities_data["top_activities"]
            ):
                logger.error("[MCPTravelAgent] Missing 'top_activities' in response")
                return (
                    f"Error: Invalid response format from MCP service for {location}."
                )

            # Format activity suggestions
            suggestions = (
                f"🌈 Activity Suggestions for {activities_data['location']} 🌈\n\n"
            )
            suggestions += f"Current Weather: {activities_data['weather_condition']}\n"
            suggestions += f"Recommended: {activities_data['recommended_activity_type']} Activities\n\n"

            suggestions += "Top Recommendations:\n"
            for activity in activities_data["top_activities"]:
                suggestions += f"  • {activity}\n"

            # Check if all activities exist with correct key
            activity_type_lower = activities_data["recommended_activity_type"].lower()
            all_activities_key = f"all_{activity_type_lower}_options"

            if (
                all_activities_key in activities_data
                and activities_data[all_activities_key]
            ):
                suggestions += f"\nAll {activity_type_lower} options:"
                for i, activity in enumerate(activities_data[all_activities_key]):
                    if i > 0:
                        suggestions += f", {activity}"
                    else:
                        suggestions += f" {activity}"

            return suggestions
        except Exception as e:
            logger.error(
                f"[MCPTravelAgent] Error getting activity suggestions from MCP: {e}"
            )
            logger.exception("Detailed exception information:")
            return f"Error: Unable to suggest activities for {location}. The MCP service might be unavailable."

    async def _get_travel_advisory(self, location: str) -> str:
        """
        Get travel advisories including weather alerts

        Args:
            location: Location

        Returns:
            Travel advisory information
        """
        logger.info(f"[MCPTravelAgent] Getting travel advisory for {location}")

        # Get weather alerts from weather agent
        try:
            weather_query = f"Are there any weather alerts for {location}?"
            weather_alerts = await self.call_agent("weather", weather_query)
            logger.info(f"[MCPTravelAgent] Received weather alerts for {location}")
        except Exception as e:
            logger.error(f"[MCPTravelAgent] Error getting weather alerts: {e}")
            weather_alerts = "Weather alert information unavailable"

        # Get travel advisories from MCP server
        try:
            # Format the location name
            formatted_location = location.strip().title()

            # Call MCP tool for travel advisories
            advisory_json = await self.call_mcp_tool(
                server_name="travel",
                tool_name="get_travel_advisory",
                location=formatted_location,
            )

            # Debug log the raw response
            logger.debug(
                f"[MCPTravelAgent] Raw MCP advisory response: {advisory_json[:200]}..."
            )

            # Parse JSON response
            advisory_data = json.loads(advisory_json)
            logger.info(
                f"[MCPTravelAgent] Successfully received travel advisory for {formatted_location}"
            )

            # Check if response contains content (MCP servers might wrap responses)
            if isinstance(advisory_data, dict) and "content" in advisory_data:
                if (
                    isinstance(advisory_data["content"], list)
                    and len(advisory_data["content"]) > 0
                ):
                    # Extract the first content item's text
                    content_item = advisory_data["content"][0]
                    if isinstance(content_item, dict) and "text" in content_item:
                        try:
                            advisory_data = json.loads(content_item["text"])
                        except json.JSONDecodeError:
                            # If not valid JSON, use as is
                            return content_item["text"]
                    else:
                        return str(content_item)
                elif isinstance(advisory_data["content"], str):
                    # Try to parse content as JSON
                    try:
                        advisory_data = json.loads(advisory_data["content"])
                    except json.JSONDecodeError:
                        return advisory_data["content"]

            # Now check if the expected keys exist
            if "location" not in advisory_data:
                logger.error(
                    "[MCPTravelAgent] Missing 'location' key in advisory response"
                )
                advisory_data["location"] = formatted_location

            # Ensure all required fields exist
            required_fields = [
                "safety_info",
                "health_info",
                "entry_requirements",
                "local_laws",
            ]
            for field in required_fields:
                if field not in advisory_data:
                    advisory_data[field] = "Information not available"

            if "updated_at" not in advisory_data:
                advisory_data["updated_at"] = datetime.now().isoformat()

            # Format travel advisory
            advisory = f"🚨 Travel Advisory for {advisory_data['location']} 🚨\n\n"
            advisory += f"Weather Alerts: {weather_alerts}\n\n"

            advisory += "🛡️ Safety Information:\n"
            advisory += f"  {advisory_data['safety_info']}\n\n"

            advisory += "🏥 Health Information:\n"
            advisory += f"  {advisory_data['health_info']}\n\n"

            advisory += "🛂 Entry Requirements:\n"
            advisory += f"  {advisory_data['entry_requirements']}\n\n"

            advisory += "📜 Local Laws:\n"
            advisory += f"  {advisory_data['local_laws']}\n\n"

            advisory += f"Last Updated: {advisory_data['updated_at']}"

            return advisory
        except Exception as e:
            logger.error(
                f"[MCPTravelAgent] Error getting travel advisory from MCP: {e}"
            )
            logger.exception("Detailed exception information:")
            return f"Error: Unable to retrieve travel advisories for {location}. The MCP service might be unavailable."
