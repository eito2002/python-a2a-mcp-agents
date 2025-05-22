"""
Maps MCP server implementation.

This server provides map generation and visualization tools via the MCP protocol.
"""

import json
import random
from datetime import datetime

from python_a2a.mcp import FastMCP, error_response, text_response

# Create the MCP server
maps_mcp = FastMCP(
    name="Maps MCP Server",
    version="1.0.0",
    description="Provides map generation and visualization via MCP",
    dependencies=["python-a2a>=0.1.0"],
)

# Simulated map data for locations
MAP_LOCATIONS = {
    "london": {"lat": 51.5074, "lon": -0.1278, "country": "UK"},
    "paris": {"lat": 48.8566, "lon": 2.3522, "country": "France"},
    "new york": {"lat": 40.7128, "lon": -74.0060, "country": "USA"},
    "tokyo": {"lat": 35.6762, "lon": 139.6503, "country": "Japan"},
    "sydney": {"lat": -33.8688, "lon": 151.2093, "country": "Australia"},
    "berlin": {"lat": 52.5200, "lon": 13.4050, "country": "Germany"},
    "rome": {"lat": 41.9028, "lon": 12.4964, "country": "Italy"},
    "madrid": {"lat": 40.4168, "lon": -3.7038, "country": "Spain"},
    "cairo": {"lat": 30.0444, "lon": 31.2357, "country": "Egypt"},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "country": "India"},
}


def generate_ascii_map(location: str, map_type: str = "weather") -> str:
    """
    Generate a simple ASCII art map for demonstration purposes.

    Args:
        location: Location name
        map_type: Type of map to generate

    Returns:
        ASCII art map
    """
    location = location.lower()
    loc_data = MAP_LOCATIONS.get(location, {"lat": 0, "lon": 0, "country": "Unknown"})

    # Generate a simple ASCII art map
    width, height = 40, 20
    map_grid = [[" " for _ in range(width)] for _ in range(height)]

    # Add borders
    for i in range(width):
        map_grid[0][i] = "-"
        map_grid[height - 1][i] = "-"
    for i in range(height):
        map_grid[i][0] = "|"
        map_grid[i][width - 1] = "|"

    # Add location marker
    center_x, center_y = width // 2, height // 2
    map_grid[center_y][center_x] = "X"

    # Add location name
    name_start = max(center_x - len(location) // 2, 1)
    for i, char in enumerate(location.upper()):
        if name_start + i < width - 1:
            map_grid[center_y + 2][name_start + i] = char

    # Add some random features based on map type
    if map_type == "weather":
        # Add some cloud or sun symbols
        symbols = (
            ["☁", "☀", "☂", "☔"] if map_type == "weather" else ["⛰", "🌊", "🌲", "🏙"]
        )
        for _ in range(10):
            x = random.randint(1, width - 2)
            y = random.randint(1, height - 2)
            if map_grid[y][x] == " ":
                map_grid[y][x] = random.choice(symbols)

    # Convert grid to string
    map_str = f"--- {location.title()} {map_type.title()} Map ---\n"
    for row in map_grid:
        map_str += "".join(row) + "\n"
    map_str += f"--- Coordinates: {loc_data['lat']}, {loc_data['lon']} ---"

    return map_str


@maps_mcp.tool(
    name="generate_weather_map", description="Generate a weather map for a location"
)
def generate_weather_map(location: str):
    """
    Generate a weather map for a location.

    Args:
        location: The name of the location to generate a map for

    Returns:
        A weather map for the specified location
    """
    location = location.lower()

    if location not in MAP_LOCATIONS:
        return error_response(f"Map data not available for {location}")

    # Generate ASCII art map for demonstration
    map_text = generate_ascii_map(location, "weather")

    result = {
        "location": location.title(),
        "map_type": "weather",
        "coordinates": MAP_LOCATIONS[location],
        "generated_at": datetime.now().isoformat(),
    }

    # Return the map as text
    return text_response(
        f"{map_text}\n\n"
        + f"Weather Map for {location.title()}\n"
        + f"Generated at: {result['generated_at']}\n"
        + f"Coordinates: {result['coordinates']['lat']}, {result['coordinates']['lon']}"
    )


@maps_mcp.tool(
    name="generate_terrain_map", description="Generate a terrain map for a location"
)
def generate_terrain_map(location: str):
    """
    Generate a terrain map for a location.

    Args:
        location: The name of the location to generate a map for

    Returns:
        A terrain map for the specified location
    """
    location = location.lower()

    if location not in MAP_LOCATIONS:
        return error_response(f"Map data not available for {location}")

    # Generate ASCII art map for demonstration
    map_text = generate_ascii_map(location, "terrain")

    result = {
        "location": location.title(),
        "map_type": "terrain",
        "coordinates": MAP_LOCATIONS[location],
        "generated_at": datetime.now().isoformat(),
    }

    # Return the map as text
    return text_response(
        f"{map_text}\n\n"
        + f"Terrain Map for {location.title()}\n"
        + f"Generated at: {result['generated_at']}\n"
        + f"Coordinates: {result['coordinates']['lat']}, {result['coordinates']['lon']}"
    )


@maps_mcp.tool(name="get_location_info", description="Get information about a location")
def get_location_info(location: str):
    """
    Get information about a location.

    Args:
        location: The name of the location to get information for

    Returns:
        Location information
    """
    location = location.lower()

    if location not in MAP_LOCATIONS:
        return error_response(f"Location data not available for {location}")

    loc_data = MAP_LOCATIONS[location]

    result = {
        "name": location.title(),
        "coordinates": {"latitude": loc_data["lat"], "longitude": loc_data["lon"]},
        "country": loc_data["country"],
        "timezone": "UTC",  # Simplified for example
        "timestamp": datetime.now().isoformat(),
    }

    return text_response(json.dumps(result, indent=2))


@maps_mcp.resource(
    uri="/maps/weather/{location}",
    name="weather_map_resource",
    description="Resource for weather maps",
)
def weather_map_resource(location: str):
    """Get weather map as a resource."""
    return generate_weather_map(location)


@maps_mcp.resource(
    uri="/maps/terrain/{location}",
    name="terrain_map_resource",
    description="Resource for terrain maps",
)
def terrain_map_resource(location: str):
    """Get terrain map as a resource."""
    return generate_terrain_map(location)


if __name__ == "__main__":
    # Run the MCP server
    maps_mcp.run(host="0.0.0.0", port=5002)
