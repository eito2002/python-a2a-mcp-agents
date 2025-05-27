"""
Weather MCP server implementation.

This server provides weather-related tools and resources via the MCP protocol.
"""

import json
import random
import logging
from datetime import datetime, timedelta

from python_a2a.mcp.fastmcp import (
    FastMCP,
    error_response,
    text_response,
)

# Configure logger
logger = logging.getLogger(__name__)

# Create the MCP server
weather_mcp = FastMCP(
    name="Weather MCP Server",
    version="1.0.0",
    description="Provides weather data and forecasts via MCP",
    dependencies=["python-a2a>=0.1.0"],
)

# Simulated weather data
WEATHER_DATA = {
    "london": {
        "condition": "Rainy",
        "temperature": 15,
        "humidity": 85,
        "wind": 18,
        "precipitation": 0.8,
    },
    "paris": {
        "condition": "Sunny",
        "temperature": 22,
        "humidity": 60,
        "wind": 10,
        "precipitation": 0.0,
    },
    "new york": {
        "condition": "Partly Cloudy",
        "temperature": 18,
        "humidity": 65,
        "wind": 15,
        "precipitation": 0.2,
    },
    "tokyo": {
        "condition": "Clear",
        "temperature": 24,
        "humidity": 70,
        "wind": 8,
        "precipitation": 0.0,
    },
    "sydney": {
        "condition": "Mild",
        "temperature": 20,
        "humidity": 75,
        "wind": 12,
        "precipitation": 0.1,
    },
}


@weather_mcp.tool(
    name="get_current_weather",
    description="Get current weather conditions for a location",
)
def get_current_weather(location: str):
    """
    Get current weather conditions for a location.

    Args:
        location: The name of the location to get weather for

    Returns:
        Current weather data for the location
    """
    # Add debug log
    logger.info(f"[Weather MCP] get_current_weather called with location: '{location}'")

    # Convert to lowercase for case-insensitive processing
    location = location.lower().strip()

    if location not in WEATHER_DATA:
        # Display list of available cities
        available_cities = ", ".join(WEATHER_DATA.keys())
        logger.warning(
            f"[Weather MCP] Weather data not available for {location}. Available cities: {available_cities}"
        )
        return error_response(
            f"Weather data not available for {location}. Available cities: {available_cities}"
        )

    data = WEATHER_DATA[location]

    # Add some randomness to make it more realistic
    temp_variation = random.uniform(-1.0, 1.0)
    humidity_variation = random.uniform(-5.0, 5.0)

    result = {
        "location": location.title(),
        "condition": data["condition"],
        "temperature": round(data["temperature"] + temp_variation, 1),
        "temperature_unit": "celsius",
        "humidity": min(100, max(0, round(data["humidity"] + humidity_variation))),
        "wind_speed": data["wind"],
        "wind_unit": "km/h",
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(f"[Weather MCP] Successfully returning weather data for {location}")
    return text_response(json.dumps(result, indent=2))


@weather_mcp.tool(
    name="get_weather_forecast", description="Get weather forecast for a location"
)
def get_weather_forecast(location: str, days: int = 3):
    """
    Get weather forecast for a location.

    Args:
        location: The name of the location to get forecast for
        days: Number of days to forecast (default: 3, max: 7)

    Returns:
        Weather forecast data for the location
    """
    # Add debug log
    logger.info(
        f"[Weather MCP] get_weather_forecast called with location: '{location}', days: {days}"
    )

    # Parameter validation
    if location is None:
        logger.error("[Weather MCP] Error: location parameter is None")
        return error_response("Location parameter is required")

    # Convert to lowercase for case-insensitive processing
    location = str(location).lower().strip()
    logger.debug(f"[Weather MCP] Normalized location: '{location}'")

    if location not in WEATHER_DATA:
        # Display list of available cities
        available_cities = ", ".join(WEATHER_DATA.keys())
        logger.warning(
            f"[Weather MCP] Weather data not available for {location}. Available cities: {available_cities}"
        )
        return error_response(
            f"Weather data not available for {location}. Available cities: {available_cities}"
        )

    # Limit forecast days
    days = min(max(1, days), 7)

    data = WEATHER_DATA[location]
    base_temp = data["temperature"]
    base_condition = data["condition"]

    forecast = []
    for i in range(days):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")

        # Generate some variation for the forecast
        temp_variation = random.uniform(-3.0, 3.0)
        humidity_variation = random.uniform(-10.0, 10.0)

        # Occasionally change the condition
        if random.random() > 0.7:
            conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Clear"]
            condition = random.choice(conditions)
        else:
            condition = base_condition

        forecast.append(
            {
                "date": date,
                "condition": condition,
                "temperature_high": round(base_temp + temp_variation + 2, 1),
                "temperature_low": round(base_temp + temp_variation - 4, 1),
                "temperature_unit": "celsius",
                "humidity": min(
                    100, max(0, round(data["humidity"] + humidity_variation))
                ),
                "precipitation_chance": (
                    round(random.random() * 100)
                    if "Rainy" in condition
                    else round(random.random() * 30)
                ),
            }
        )

    result = {
        "location": location.title(),
        "forecast": forecast,
        "generated_at": datetime.now().isoformat(),
    }

    logger.info(f"[Weather MCP] Successfully returning forecast data for {location}")
    return text_response(json.dumps(result, indent=2))


@weather_mcp.tool(
    name="get_weather_alert", description="Get weather alerts for a location"
)
def get_weather_alert(location: str):
    """
    Get active weather alerts for a location.

    Args:
        location: The name of the location to get alerts for

    Returns:
        Active weather alerts for the location
    """
    logger.info(f"[Weather MCP] get_weather_alert called with location: '{location}'")

    location = location.lower()

    if location not in WEATHER_DATA:
        logger.warning(f"[Weather MCP] Weather data not available for {location}")
        return error_response(f"Weather data not available for {location}")

    data = WEATHER_DATA[location]

    # Randomly determine if there's an alert
    has_alert = random.random() < 0.3

    if not has_alert:
        logger.info(f"[Weather MCP] No alerts found for {location}")
        return text_response(
            json.dumps(
                {
                    "location": location.title(),
                    "alerts": [],
                    "timestamp": datetime.now().isoformat(),
                },
                indent=2,
            )
        )

    # Generate a random alert
    alert_types = ["Flood", "High Wind", "Thunderstorm", "Extreme Heat", "Heavy Rain"]
    alert_type = random.choice(alert_types)

    alert = {
        "type": alert_type,
        "severity": random.choice(["Minor", "Moderate", "Severe"]),
        "description": f"{alert_type} warning for {location.title()} area",
        "issued_at": (
            datetime.now() - timedelta(hours=random.randint(1, 6))
        ).isoformat(),
        "expires_at": (
            datetime.now() + timedelta(hours=random.randint(6, 24))
        ).isoformat(),
    }

    result = {
        "location": location.title(),
        "alerts": [alert],
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(f"[Weather MCP] Returning alert of type {alert_type} for {location}")
    return text_response(json.dumps(result, indent=2))


@weather_mcp.resource(
    uri="/weather/current/{location}",
    name="current_weather_resource",
    description="Resource for current weather data",
)
def current_weather_resource(location: str):
    """Get current weather as a resource."""
    logger.info(
        f"[Weather MCP] current_weather_resource called with location: '{location}'"
    )
    return get_current_weather(location)


@weather_mcp.resource(
    uri="/weather/forecast/{location}/{days}",
    name="forecast_resource",
    description="Resource for weather forecast data",
)
def forecast_resource(location: str, days: str):
    """Get weather forecast as a resource."""
    logger.info(
        f"[Weather MCP] forecast_resource called with location: '{location}', days: {days}"
    )
    try:
        days_int = int(days)
    except ValueError:
        logger.error(f"[Weather MCP] Invalid days parameter: {days}")
        return error_response("Days must be a number")

    return get_weather_forecast(location, days_int)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Run the MCP server
    logger.info("[Weather MCP] Starting Weather MCP server")
    weather_mcp.run(host="0.0.0.0", port=5001)
