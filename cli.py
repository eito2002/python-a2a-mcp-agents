"""
Command Line Interface (CLI) for the agent network.
"""

import sys
import asyncio
import argparse
import time
import logging
from typing import List, Dict, Optional

from config import logger
from agents import AsyncMCPWeatherAgent
from agents import AsyncMCPTravelAgent
from server import AgentServer
from utils import find_free_port
from client import A2ANetworkClient
from python_a2a.models import Message, MessageRole, TextContent

# MCP server configurations
MCP_SERVER_CONFIGS = [
    {
        "module": "mcp_servers.weather_mcp_server",
        "server_var": "weather_mcp",
        "port": 5001
    },
    {
        "module": "mcp_servers.maps_mcp_server",
        "server_var": "maps_mcp",
        "port": 5002
    },
    {
        "module": "mcp_servers.travel_mcp_server",
        "server_var": "travel_mcp",
        "port": 5003
    }
]

# FastAPI MCP agent configurations
MCP_AGENT_CONFIGS = [
    {
        "name": "mcp_weather",
        "class_module": "agents.mcp.mcp_weather_agent",
        "class_name": "AsyncMCPWeatherAgent",
        "mcp_servers": {
            "weather": "http://localhost:5001",
            "maps": "http://localhost:5002"
        }
    },
    {
        "name": "mcp_travel",
        "class_module": "agents.mcp.mcp_travel_agent",
        "class_name": "AsyncMCPTravelAgent",
        "mcp_servers": {
            "travel": "http://localhost:5003",
            "maps": "http://localhost:5002"
        },
        "agent_connections": {
            "weather": "http://localhost:5000"  # Will be updated dynamically
        }
    }
]

async def start_single_agent(args):
    """Start a single agent with specified configuration and connections."""
    logger.info(f"Starting single agent: {args.agent}")
    
    # Process agent ports
    agent_port = args.port if args.port else find_free_port()
    
    # Process external agent connections
    agent_connections = {}
    if args.connect_to:
        for conn_spec in args.connect_to:
            if ':' not in conn_spec:
                logger.error(f"Invalid connection specification: {conn_spec}. Format should be agent_name:port")
                return
            agent_name, agent_port_str = conn_spec.split(':', 1)
            try:
                agent_connections[agent_name] = f"http://localhost:{int(agent_port_str)}"
                logger.info(f"Adding connection to {agent_name} at port {agent_port_str}")
            except ValueError:
                logger.error(f"Port must be a number: {agent_port_str}")
                return
    
    try:
        # Find agent configuration
        agent_config = None
        for config in MCP_AGENT_CONFIGS:
            if config["name"] == args.agent:
                agent_config = config
                break
        
        if not agent_config:
            logger.error(f"Unknown agent: {args.agent}")
            return
        
        # Import agent class
        module_name = agent_config["class_module"]
        class_name = agent_config["class_name"]
        module = __import__(module_name, fromlist=[class_name])
        agent_class = getattr(module, class_name)
        
        # Get MCP server configurations
        mcp_servers_config = agent_config.get("mcp_servers", {})
        
        # Merge default and specified agent connections
        config_connections = agent_config.get("agent_connections", {})
        merged_connections = {**config_connections, **agent_connections}
        logger.info(f"Using agent connections: {merged_connections}")
        
        # Create agent instance
        if merged_connections:
            agent = agent_class(mcp_servers=mcp_servers_config, agent_connections=merged_connections)
        else:
            agent = agent_class(mcp_servers=mcp_servers_config)
        
        # Initialize if needed
        if hasattr(agent, "initialize") and callable(agent.initialize):
            await agent.initialize()
        
        # Start server thread
        import threading
        server_thread = threading.Thread(
            target=agent.run,
            kwargs={"host": "0.0.0.0", "port": agent_port, "debug": False},
            daemon=True
        )
        server_thread.start()
        
        # Wait for server to start
        await asyncio.sleep(0.5)
        
        # Register agent info
        extra_info = {
            "is_mcp": True,
            "mcp_servers": list(mcp_servers_config.keys())
        }
        
        # Add agent connections if available
        if merged_connections:
            extra_info["agent_connections"] = list(merged_connections.keys())
        
        AgentServer.register_agent(
            name=args.agent,
            agent=agent,
            port=agent_port,
            **extra_info
        )
        
        print(f"{args.agent} agent is running on port {agent_port}. Press Ctrl+C to stop.")
        print(f"Use 'python -m cli query --agent {args.agent} --agent-ports {args.agent}:{agent_port} \"Your query here\"' to query this agent.")
        
        # Keep the program running
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print(f"\nStopping {args.agent} agent...")
    finally:
        # Stop agent
        AgentServer.stop_agent(args.agent)


def run_single_agent_command(args):
    """Run the start-agent command by executing the async function."""
    # Create and use a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the start_single_agent function
        loop.run_until_complete(start_single_agent(args))
    except KeyboardInterrupt:
        print(f"\n{args.agent} agent stopped.")
    finally:
        loop.close()


def query_agent(args):
    """Query a specific agent or let the network route the query."""
    if not args.query:
        print("Error: No query provided.")
        return
    
    # Create agent endpoints dictionary from agent_ports argument
    agent_ports = {}
    if args.agent_ports:
        for port_spec in args.agent_ports:
            if ':' not in port_spec:
                print(f"Error: Invalid port specification: {port_spec}. Format should be agent_name:port")
                return
            agent_name, port = port_spec.split(':', 1)
            try:
                agent_ports[agent_name] = int(port)
            except ValueError:
                print(f"Error: Port must be a number: {port}")
                return
    
    # Create the agent network client with specified ports
    client = A2ANetworkClient()
    client.discover_agents(known_ports=agent_ports if agent_ports else None)
    
    # Check if we have any agents to query
    if not client.agents:
        print("Error: No agents available. Use 'start-agent' command first, or specify agent ports.")
        return
    
    # List the discovered agents
    agents_info = client.list_agents()
    print("Available agents:")
    for agent in agents_info:
        status = "Available" if agent["available"] else "Not available"
        print(f"- {agent['name']}: {agent['endpoint']} ({status})")
    
    # Create the message with proper TextContent
    message = Message(
        content=TextContent(text=args.query),
        role=MessageRole.USER
    )
    
    # Process the query
    if args.agent:
        print(f"Querying {args.agent} agent...")
        response = client.send_message(message, agent_name=args.agent)
    else:
        print("Routing query to the most appropriate agent...")
        response = client.send_message(message)
    
    print("\nResult:")
    if hasattr(response.content, 'text'):
        print(response.content.text)
    else:
        print(response.content)


async def start_mcp_environment(args):
    """Start the MCP environment with servers only."""
    # Get logger for MCP environment
    mcp_logger = logging.getLogger("mcp")
    mcp_servers = []
    
    try:
        # Start MCP servers
        mcp_logger.info("Starting MCP servers...")
        mcp_servers = await AgentServer.start_mcp_servers(MCP_SERVER_CONFIGS)
        mcp_logger.info(f"Started {len(mcp_servers)} MCP servers")
        
        for server in mcp_servers:
            mcp_logger.info(f"  - {server['name']} (http://localhost:{server['port']})")
        
        # Confirm all MCP servers are started
        print("MCP servers are running. Press Ctrl+C to stop.")
        
        # Keep program running with infinite loop
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print("\nMCP servers stopping...")
    finally:
        # Stop MCP servers
        if mcp_servers:
            print("MCP servers stopped...")
            AgentServer.stop_mcp_servers(mcp_servers)


def run_mcp_command(args):
    """Run the MCP command by executing the async function."""
    # Create and use a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the start_mcp_environment function
        loop.run_until_complete(start_mcp_environment(args))
    except KeyboardInterrupt:
        print("\nMCP servers stopped.")
    finally:
        loop.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Agent Network CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # MCP command (servers only)
    mcp_parser = subparsers.add_parser("mcp", help="Start MCP servers")
    
    # Start-agent command
    start_agent_parser = subparsers.add_parser("start-agent", help="Start a single agent with configurable connections")
    start_agent_parser.add_argument("--agent", required=True, 
                                   help="Agent to start (mcp_weather, mcp_travel)")
    start_agent_parser.add_argument("--port", type=int, 
                                  help="Port to use for this agent (if not specified, a free port will be found)")
    start_agent_parser.add_argument("--connect-to", nargs="+", 
                                   help="Agents to connect to in format 'agent_name:port' (e.g., 'weather:53537')")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query the agent network")
    query_parser.add_argument("--agent", help="Specific agent to query (mcp_weather, mcp_travel)")
    query_parser.add_argument("--router-type", default="keyword", choices=["keyword", "ai"], 
                              help="Type of routing to use (default: keyword)")
    query_parser.add_argument("--agent-ports", nargs="+", 
                              help="Custom agent ports in format 'agent_name:port' (e.g., 'weather:59983')")
    query_parser.add_argument("query", nargs="?", help="The query text")
    
    args = parser.parse_args()
    
    if args.command == "mcp":
        run_mcp_command(args)
    elif args.command == "start-agent":
        run_single_agent_command(args)
    elif args.command == "query":
        query_agent(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 