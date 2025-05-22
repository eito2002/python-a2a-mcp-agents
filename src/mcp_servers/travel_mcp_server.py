"""
Travel MCP server implementation.

This server provides travel-related tools and resources via the MCP protocol.
"""

import json
import random
from datetime import datetime, timedelta

from python_a2a.mcp.fastmcp import (
    FastMCP,
    error_response,
    text_response,
)

# Create the MCP server
travel_mcp = FastMCP(
    name="Travel MCP Server",
    version="1.0.0",
    description="Provides travel data and recommendations via MCP",
    dependencies=["python-a2a>=0.1.0"],
)

# Simulated travel data
TRAVEL_DATA = {
    "london": {
        "attractions": [
            "Big Ben",
            "British Museum",
            "Tower of London",
            "Buckingham Palace",
            "London Eye",
        ],
        "indoor_activities": [
            "British Museum",
            "National Gallery",
            "Madame Tussauds",
            "Shopping at Harrods",
            "West End Theatre",
        ],
        "outdoor_activities": [
            "Hyde Park",
            "Thames River Cruise",
            "Tower Bridge",
            "Camden Market",
            "Kew Gardens",
        ],
        "cuisines": ["British", "Indian", "French", "Italian", "Chinese"],
        "transportation": [
            "Underground (Tube)",
            "Bus",
            "Taxi",
            "Rental Bikes",
            "Walking",
        ],
        "safety": "High",
        "language": "English",
        "currency": "British Pound (£)",
        "timezone": "GMT+0",
    },
    "paris": {
        "attractions": [
            "Eiffel Tower",
            "Louvre Museum",
            "Notre-Dame Cathedral",
            "Arc de Triomphe",
            "Montmartre",
        ],
        "indoor_activities": [
            "Louvre Museum",
            "Musée d'Orsay",
            "Centre Pompidou",
            "Galeries Lafayette",
            "Parisian Cafés",
        ],
        "outdoor_activities": [
            "Seine River Cruise",
            "Luxembourg Gardens",
            "Champs-Élysées",
            "Montmartre Walk",
            "Tuileries Garden",
        ],
        "cuisines": ["French", "Italian", "Japanese", "Moroccan", "Lebanese"],
        "transportation": ["Metro", "Bus", "Taxi", "Rental Bikes", "Walking"],
        "safety": "Moderate",
        "language": "French",
        "currency": "Euro (€)",
        "timezone": "GMT+1",
    },
    "new york": {
        "attractions": [
            "Statue of Liberty",
            "Times Square",
            "Central Park",
            "Empire State Building",
            "Brooklyn Bridge",
        ],
        "indoor_activities": [
            "Metropolitan Museum of Art",
            "MoMA",
            "American Museum of Natural History",
            "Broadway Shows",
            "Shopping in SoHo",
        ],
        "outdoor_activities": [
            "Central Park",
            "High Line",
            "Brooklyn Bridge Walk",
            "Staten Island Ferry",
            "Coney Island",
        ],
        "cuisines": ["American", "Italian", "Chinese", "Mexican", "Japanese"],
        "transportation": ["Subway", "Bus", "Taxi", "Uber/Lyft", "Walking"],
        "safety": "Moderate",
        "language": "English",
        "currency": "US Dollar ($)",
        "timezone": "GMT-5",
    },
    "tokyo": {
        "attractions": [
            "Tokyo Tower",
            "Senso-ji Temple",
            "Meiji Shrine",
            "Shibuya Crossing",
            "Tokyo Skytree",
        ],
        "indoor_activities": [
            "Tokyo National Museum",
            "TeamLab Borderless",
            "Shopping in Ginza",
            "Robot Restaurant",
            "Japanese Food Markets",
        ],
        "outdoor_activities": [
            "Yoyogi Park",
            "Shinjuku Gyoen",
            "Tsukiji Fish Market",
            "Sumida River Cruise",
            "Ueno Park",
        ],
        "cuisines": ["Japanese", "Korean", "French", "Italian", "American"],
        "transportation": ["JR Rail", "Subway", "Bus", "Taxi", "Walking"],
        "safety": "Very High",
        "language": "Japanese",
        "currency": "Japanese Yen (¥)",
        "timezone": "GMT+9",
    },
    "sydney": {
        "attractions": [
            "Sydney Opera House",
            "Sydney Harbour Bridge",
            "Bondi Beach",
            "Taronga Zoo",
            "Darling Harbour",
        ],
        "indoor_activities": [
            "Art Gallery of NSW",
            "Australian Museum",
            "Queen Victoria Building",
            "Sydney Tower Eye",
            "Sea Life Sydney Aquarium",
        ],
        "outdoor_activities": [
            "Bondi to Coogee Coastal Walk",
            "Sydney Harbour Cruise",
            "Royal Botanic Garden",
            "Blue Mountains Day Trip",
            "Manly Beach",
        ],
        "cuisines": [
            "Australian",
            "Asian Fusion",
            "Mediterranean",
            "Seafood",
            "Italian",
        ],
        "transportation": ["Train", "Bus", "Ferry", "Taxi", "Walking"],
        "safety": "High",
        "language": "English",
        "currency": "Australian Dollar (A$)",
        "timezone": "GMT+10",
    },
}

# Travel advisories (simplified)
TRAVEL_ADVISORIES = {
    "london": {
        "safety": "Generally safe for travelers. Take normal precautions.",
        "health": "No major health concerns. Standard travel insurance recommended.",
        "entry": "Passport required. Visa-free for many countries for short stays.",
        "local_laws": "Follow local regulations regarding smoking, drinking in public areas.",
    },
    "paris": {
        "safety": "Exercise caution, especially in tourist areas. Beware of pickpocketing.",
        "health": "No major health concerns. Standard travel insurance recommended.",
        "entry": "Passport required. Schengen visa for non-EU citizens for stays longer than 90 days.",
        "local_laws": "Taking photos of security facilities may be restricted.",
    },
    "new york": {
        "safety": "Exercise caution in certain neighborhoods, especially at night.",
        "health": "Healthcare is excellent but expensive. Travel insurance strongly advised.",
        "entry": "Passport and either ESTA or visa required.",
        "local_laws": "21 years minimum age for alcohol consumption.",
    },
    "tokyo": {
        "safety": "Extremely safe for travelers. Low crime rate.",
        "health": "High standard of healthcare. Travel insurance recommended.",
        "entry": "Passport and visa required for most visitors.",
        "local_laws": "Zero tolerance for drug offenses. Always carry ID.",
    },
    "sydney": {
        "safety": "Generally safe for travelers. Take precautions for sun exposure.",
        "health": "High standard of healthcare. Travel insurance recommended.",
        "entry": "Passport and visa required for most visitors.",
        "local_laws": "Strict quarantine laws for food, plants, and animal products.",
    },
}


@travel_mcp.tool(
    name="get_destination_info",
    description="Get comprehensive information about a travel destination",
)
def get_destination_info(location: str):
    """
    Get comprehensive information about a travel destination.

    Args:
        location: Name of the location to get information for

    Returns:
        Comprehensive travel information for the location
    """
    location = location.lower()

    if location not in TRAVEL_DATA:
        return error_response(f"Travel data not available for {location}")

    data = TRAVEL_DATA[location]

    result = {
        "location": location.title(),
        "attractions": data["attractions"],
        "indoor_activities": data["indoor_activities"],
        "outdoor_activities": data["outdoor_activities"],
        "cuisines": data["cuisines"],
        "transportation": data["transportation"],
        "safety_level": data["safety"],
        "language": data["language"],
        "currency": data["currency"],
        "timezone": data["timezone"],
        "timestamp": datetime.now().isoformat(),
    }

    return text_response(json.dumps(result, indent=2))


@travel_mcp.tool(
    name="suggest_activities",
    description="Get activity suggestions based on weather conditions",
)
def suggest_activities(location: str, weather_condition: str):
    """
    Get activity suggestions based on weather conditions.

    Args:
        location: Name of the location to get suggestions for
        weather_condition: Current weather condition (e.g., "Sunny", "Rainy")

    Returns:
        Weather-appropriate activity suggestions
    """
    location = location.lower()

    if location not in TRAVEL_DATA:
        return error_response(f"Travel data not available for {location}")

    data = TRAVEL_DATA[location]

    # Determine if weather is good or bad
    bad_weather_keywords = [
        "rain",
        "snow",
        "storm",
        "thunder",
        "cold",
        "windy",
        "hurricane",
        "tornado",
        "typhoon",
    ]
    is_bad_weather = any(
        keyword in weather_condition.lower() for keyword in bad_weather_keywords
    )

    if is_bad_weather:
        # Recommend indoor activities
        activities = data["indoor_activities"]
        activity_type = "Indoor"
    else:
        # Recommend outdoor activities
        activities = data["outdoor_activities"]
        activity_type = "Outdoor"

    # Randomize order and pick top activities
    random.shuffle(activities)
    top_activities = activities[:3]

    result = {
        "location": location.title(),
        "weather_condition": weather_condition,
        "recommended_activity_type": activity_type,
        "top_activities": top_activities,
        "all_" + activity_type.lower() + "_options": activities,
        "timestamp": datetime.now().isoformat(),
    }

    return text_response(json.dumps(result, indent=2))


@travel_mcp.tool(
    name="get_travel_advisory",
    description="Get travel advisory information for a location",
)
def get_travel_advisory(location: str):
    """
    Get travel advisory information for a location.

    Args:
        location: Name of the location to get advisory for

    Returns:
        Travel advisory information
    """
    location = location.lower()

    if location not in TRAVEL_ADVISORIES:
        return error_response(f"Travel advisory not available for {location}")

    advisory = TRAVEL_ADVISORIES[location]

    result = {
        "location": location.title(),
        "safety_info": advisory["safety"],
        "health_info": advisory["health"],
        "entry_requirements": advisory["entry"],
        "local_laws": advisory["local_laws"],
        "updated_at": datetime.now().isoformat(),
    }

    return text_response(json.dumps(result, indent=2))


@travel_mcp.tool(
    name="create_trip_itinerary",
    description="Create a trip itinerary based on destination and duration",
)
def create_trip_itinerary(location: str, days: int = 3, weather_condition: str = None):
    """
    Create a trip itinerary based on destination and duration.

    Args:
        location: Name of the destination
        days: Number of days for the trip (1-7)
        weather_condition: Optional weather condition to consider

    Returns:
        Daily itinerary for the specified trip
    """
    location = location.lower()

    if location not in TRAVEL_DATA:
        return error_response(f"Travel data not available for {location}")

    # Limit days
    days = min(max(1, days), 7)

    data = TRAVEL_DATA[location]

    # Create itinerary
    itinerary = []
    attractions = data["attractions"].copy()
    random.shuffle(attractions)

    indoor = data["indoor_activities"].copy()
    random.shuffle(indoor)

    outdoor = data["outdoor_activities"].copy()
    random.shuffle(outdoor)

    # Determine if weather is favorable for outdoor activities
    is_bad_weather = False
    if weather_condition:
        bad_weather_keywords = [
            "rain",
            "snow",
            "storm",
            "thunder",
            "cold",
            "windy",
            "hurricane",
            "tornado",
            "typhoon",
        ]
        is_bad_weather = any(
            keyword in weather_condition.lower() for keyword in bad_weather_keywords
        )

    for day in range(1, days + 1):
        daily_plan = {
            "day": day,
            "date": (datetime.now() + timedelta(days=day - 1)).strftime("%Y-%m-%d"),
            "morning": None,
            "afternoon": None,
            "evening": None,
            "meals": [],
        }

        # Morning activity
        if is_bad_weather or (day % 2 == 0):  # Alternate or weather-based
            if indoor:
                daily_plan["morning"] = {"activity": indoor.pop(0), "type": "indoor"}
            elif attractions:
                daily_plan["morning"] = {
                    "activity": attractions.pop(0),
                    "type": "attraction",
                }
        else:
            if outdoor:
                daily_plan["morning"] = {"activity": outdoor.pop(0), "type": "outdoor"}
            elif attractions:
                daily_plan["morning"] = {
                    "activity": attractions.pop(0),
                    "type": "attraction",
                }

        # Afternoon activity
        if is_bad_weather:
            if indoor:
                daily_plan["afternoon"] = {"activity": indoor.pop(0), "type": "indoor"}
            elif attractions:
                daily_plan["afternoon"] = {
                    "activity": attractions.pop(0),
                    "type": "attraction",
                }
        else:
            if day % 2 == 0 and outdoor:
                daily_plan["afternoon"] = {
                    "activity": outdoor.pop(0),
                    "type": "outdoor",
                }
            elif indoor:
                daily_plan["afternoon"] = {"activity": indoor.pop(0), "type": "indoor"}
            elif attractions:
                daily_plan["afternoon"] = {
                    "activity": attractions.pop(0),
                    "type": "attraction",
                }

        # Evening activity - typically indoor or dining
        daily_plan["evening"] = {
            "activity": f"Dinner - {random.choice(data['cuisines'])} cuisine",
            "type": "dining",
        }

        # Meals
        daily_plan["meals"] = [
            {"meal": "Breakfast", "suggestion": "Hotel or local café"},
            {
                "meal": "Lunch",
                "suggestion": f"Try {random.choice(data['cuisines'])} food",
            },
            {
                "meal": "Dinner",
                "suggestion": f"{random.choice(data['cuisines'])} restaurant",
            },
        ]

        # Add transportation tip
        daily_plan["transportation_tip"] = (
            f"Best way to get around: {random.choice(data['transportation'])}"
        )

        itinerary.append(daily_plan)

    result = {
        "location": location.title(),
        "trip_duration": days,
        "weather_consideration": (
            weather_condition if weather_condition else "Not specified"
        ),
        "itinerary": itinerary,
        "tips": [
            f"Language: {data['language']}",
            f"Currency: {data['currency']}",
            f"Timezone: {data['timezone']}",
            "Carry a map or use map apps for navigation",
            "Check opening hours of attractions before visiting",
        ],
        "generated_at": datetime.now().isoformat(),
    }

    return text_response(json.dumps(result, indent=2))


@travel_mcp.resource(
    uri="/travel/destination/{location}",
    name="destination_resource",
    description="Resource for destination information",
)
def destination_resource(location: str):
    """Resource endpoint for destination information"""
    location = location.lower()

    if location not in TRAVEL_DATA:
        return error_response(f"Travel data not available for {location}")

    data = TRAVEL_DATA[location]

    result = {
        "location": location.title(),
        "attractions": data["attractions"],
        "indoor_activities": data["indoor_activities"],
        "outdoor_activities": data["outdoor_activities"],
        "cuisines": data["cuisines"],
        "transportation": data["transportation"],
        "safety_level": data["safety"],
        "language": data["language"],
        "currency": data["currency"],
        "timezone": data["timezone"],
    }

    return text_response(json.dumps(result, indent=2))


@travel_mcp.resource(
    uri="/travel/advisory/{location}",
    name="advisory_resource",
    description="Resource for travel advisories",
)
def advisory_resource(location: str):
    """Resource endpoint for travel advisories"""
    location = location.lower()

    if location not in TRAVEL_ADVISORIES:
        return error_response(f"Travel advisory not available for {location}")

    advisory = TRAVEL_ADVISORIES[location]

    result = {
        "location": location.title(),
        "safety_info": advisory["safety"],
        "health_info": advisory["health"],
        "entry_requirements": advisory["entry"],
        "local_laws": advisory["local_laws"],
    }

    return text_response(json.dumps(result, indent=2))
