# chapter-04/first_mcp_server.py
# A complete, runnable MCP server for weather and time tools
# Run with: python first_mcp_server.py
# Then connect from Claude Code (instructions in section 4.4)

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

# MCP SDK imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Set up logging so we can see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-mcp-server")

# ------------------------------------------------------------------
# CREATE THE MCP SERVER
# ------------------------------------------------------------------

# Create the server with a name
server = Server("weather-server")

# ------------------------------------------------------------------
# DEFINE THE TOOLS
# ------------------------------------------------------------------
# This is where we tell MCP what tools this server provides.
# The agent will see this list and know what it can call.
# ------------------------------------------------------------------

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List all available tools.
    This function is called when the agent asks "what tools do you have?"
    """
    return [
        types.Tool(
            name="get_weather",
            description="Get the current weather for a city. Use this when someone asks about temperature, conditions, or forecast.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city (e.g., 'Chicago', 'London', 'Tokyo')"
                    }
                },
                "required": ["city"]
            }
        ),
        types.Tool(
            name="get_time",
            description="Get the current time in a specific timezone. Use this when someone asks about what time it is.",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "The timezone (e.g., 'America/Chicago', 'Europe/London', 'Asia/Tokyo')"
                    }
                },
                "required": ["timezone"]
            }
        ),
        types.Tool(
            name="get_weather_and_time",
            description="Get both weather and time for a city in one call. More efficient than calling separately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "The timezone (optional, defaults to city's timezone)"
                    }
                },
                "required": ["city"]
            }
        )
    ]


# ------------------------------------------------------------------
# IMPLEMENT THE TOOLS
# ------------------------------------------------------------------
# This is where the actual work happens.
# When the agent calls a tool, the corresponding function runs.
# ------------------------------------------------------------------

# Simulated weather database
WEATHER_DATA = {
    "chicago": "72°F and sunny",
    "london": "58°F and cloudy",
    "new york": "68°F and partly cloudy",
    "tokyo": "75°F and humid",
    "sydney": "82°F and clear",
    "paris": "64°F and light rain",
    "berlin": "60°F and overcast",
    "mumbai": "88°F and humid",
    "beijing": "70°F and hazy",
    "cairo": "95°F and dry",
}

# Timezone mapping for common cities
CITY_TIMEZONES = {
    "chicago": "America/Chicago",
    "london": "Europe/London",
    "new york": "America/New_York",
    "tokyo": "Asia/Tokyo",
    "sydney": "Australia/Sydney",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "mumbai": "Asia/Kolkata",
    "beijing": "Asia/Shanghai",
    "cairo": "Africa/Cairo",
}


def get_weather_impl(city: str) -> str:
    """Internal implementation of the weather tool."""
    city_lower = city.lower()
    if city_lower in WEATHER_DATA:
        return f"The weather in {city} is {WEATHER_DATA[city_lower]}."
    else:
        closest = find_closest_city(city_lower)
        if closest:
            return f"I don't have exact data for {city}. However, {closest} has {WEATHER_DATA[closest]}."
        return f"I don't have weather data for {city}. Try: Chicago, London, New York, Tokyo, Sydney, Paris, Berlin, Mumbai, Beijing, or Cairo."


def find_closest_city(query: str) -> str | None:
    """Find the closest matching city in our database."""
    query_lower = query.lower()
    for city in WEATHER_DATA.keys():
        if query_lower in city or city in query_lower:
            return city
    return None


def get_time_impl(timezone: str) -> str:
    """Internal implementation of the time tool."""
    import pytz
    
    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        return f"The current time in {timezone} is {current_time.strftime('%I:%M %p')}."
    except Exception as e:
        # Try to map common timezone names
        timezone_map = {
            "eastern": "America/New_York",
            "central": "America/Chicago",
            "mountain": "America/Denver",
            "pacific": "America/Los_Angeles",
            "london": "Europe/London",
            "uk": "Europe/London",
            "paris": "Europe/Paris",
            "berlin": "Europe/Berlin",
            "tokyo": "Asia/Tokyo",
            "japan": "Asia/Tokyo",
            "sydney": "Australia/Sydney",
            "mumbai": "Asia/Kolkata",
            "beijing": "Asia/Shanghai",
        }
        mapped = timezone_map.get(timezone.lower(), timezone)
        try:
            tz = pytz.timezone(mapped)
            current_time = datetime.now(tz)
            return f"The current time in {timezone} is {current_time.strftime('%I:%M %p')}."
        except:
            return f"Error: Could not find timezone '{timezone}'. Try 'America/Chicago' or 'Europe/London'."


@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: dict[str, Any]
) -> list[types.TextContent]:
    """
    Execute a tool when the agent calls it.
    This is the main entry point for all tool calls.
    """
    logger.info(f"Tool called: {name} with arguments {arguments}")
    
    try:
        if name == "get_weather":
            city = arguments.get("city", "")
            if not city:
                result = "Error: Missing required argument 'city'"
            else:
                result = get_weather_impl(city)
        
        elif name == "get_time":
            timezone = arguments.get("timezone", "")
            if not timezone:
                result = "Error: Missing required argument 'timezone'"
            else:
                result = get_time_impl(timezone)
        
        elif name == "get_weather_and_time":
            city = arguments.get("city", "")
            timezone = arguments.get("timezone", CITY_TIMEZONES.get(city.lower(), "America/Chicago"))
            
            if not city:
                result = "Error: Missing required argument 'city'"
            else:
                weather = get_weather_impl(city)
                time = get_time_impl(timezone)
                result = f"{weather}\n{time}"
        
        else:
            result = f"Error: Unknown tool '{name}'"
        
        return [types.TextContent(type="text", text=result)]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text", 
            text=f"Error executing {name}: {str(e)}"
        )]


# ------------------------------------------------------------------
# RUN THE SERVER
# ------------------------------------------------------------------
# This starts the MCP server and listens for connections.
# The server runs forever until you press Ctrl+C.
# ------------------------------------------------------------------

async def main():
    """Start the MCP server."""
    logger.info("Starting Weather MCP Server...")
    
    # Run the server using stdio (standard input/output)
    # This allows Claude Code and other agents to communicate with it
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="weather-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
