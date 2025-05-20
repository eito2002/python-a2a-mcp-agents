"""
Command Line Interface (CLI) for the agent network.
"""

import sys
import asyncio
import argparse
import time
import logging
import signal
from typing import List, Dict, Optional

from config import logger
from network import AgentNetwork
from agents import KnowledgeAgent, MathAgent
from agents.mcp.mcp_weather_agent import AsyncMCPWeatherAgent
from agents.mcp.mcp_travel_agent import AsyncMCPTravelAgent
from server import AgentServer
from conversation import ConversationOrchestrator
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

def list_agents():
    """List all available agents in the network."""
    running_agents = AgentServer.list_running_agents()
    
    if not running_agents:
        print("No agents running.")
        return
    
    print("Running agents:")
    for agent_name in running_agents:
        info = AgentServer.get_agent_info(agent_name)
        if info:
            endpoint = info['endpoint']
            agent_type = "MCP-enabled" if info.get('is_mcp', False) else "Standard"
            print(f"- {agent_name}: {endpoint} ({agent_type})")
            
            # Display additional information for MCP agents
            if info.get('is_mcp', False):
                if 'mcp_servers' in info:
                    print(f"  - Connected MCP servers: {', '.join(info['mcp_servers'])}")
                if 'mcp_tools' in info:
                    print(f"  - Available tools: {len(info['mcp_tools'])}")
                if 'agent_connections' in info:
                    print(f"  - Connected agents: {', '.join(info['agent_connections'])}")


async def start_all_agents():
    """Start all available agent types."""
    # Start standard agents
    
    agent, port = AgentServer.start_agent(KnowledgeAgent, "knowledge")
    print(f"Started Knowledge Agent on port {port}")

    agent, port = AgentServer.start_agent(MathAgent, "math")
    print(f"Started Math Agent on port {port}")
    
    # Wait a moment for agents to initialize
    time.sleep(1)
    
    # Keep the program running so the agents remain active
    print("Agents are running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping agents...")
        # You could add cleanup logic here if needed


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
        # Handle standard agents
        if args.agent in ["knowledge", "math"]:
            if args.agent == "knowledge":
                agent, port = AgentServer.start_agent(KnowledgeAgent, "knowledge", port=agent_port)
                logger.info(f"Started Knowledge Agent on port {port}")
            else:  # math
                agent, port = AgentServer.start_agent(MathAgent, "math", port=agent_port)
                logger.info(f"Started Math Agent on port {port}")
            
            agent_type = "Standard"
        
        # Handle MCP agents
        else:
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
            
            port = agent_port
            agent_type = "MCP-enabled"
        
        print(f"{args.agent} agent ({agent_type}) is running on port {port}. Press Ctrl+C to stop.")
        print(f"Use 'python -m cli query --agent {args.agent} --agent-ports {args.agent}:{port} \"Your query here\"' to query this agent.")
        
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
        print("Error: No agents available. Use 'start' command first, or specify agent ports.")
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


def run_conversation(args):
    """Run a multi-agent conversation with a specified workflow."""
    if not args.query:
        print("Error: No query provided.")
        return
    
    if not args.workflow:
        print("Error: No workflow specified.")
        return
    
    # Parse the workflow
    workflow = args.workflow.split(",")
    
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
    
    # List the discovered agents
    agents_info = client.list_agents()
    print("Available agents:")
    for agent in agents_info:
        status = "Available" if agent["available"] else "Not available"
        print(f"- {agent['name']}: {agent['endpoint']} ({status})")
    
    # Check if all workflow agents are available
    available_agents = set(client.agents.keys())
    for agent_name in workflow:
        if agent_name not in available_agents:
            print(f"Error: Agent '{agent_name}' not found in the network.")
            return
    
    # Create the initial message with proper TextContent
    initial_message = Message(
        content=TextContent(text=args.query),
        role=MessageRole.USER
    )
    
    try:
        print("Starting multi-agent conversation...")
        # Run the workflow
        conversation = client.run_workflow(initial_message, workflow)
        
        # Print the conversation history
        print("\nConversation History:")
        for i, message in enumerate(conversation.messages):
            print(f"[{message.role}]: ", end="")
            if hasattr(message.content, 'text'):
                print(message.content.text)
            else:
                print(message.content)
            print()
        
        # Get the final message
        if conversation.messages:
            final_message = conversation.messages[-1]
            print("\nFinal Result:")
            if hasattr(final_message.content, 'text'):
                print(final_message.content.text)
            else:
                print(final_message.content)
        else:
            print("\nNo result produced.")
    
    except Exception as e:
        print(f"Error in conversation: {e}")


async def start_mcp_environment(args):
    """Start the MCP environment with servers and agents."""
    # Get logger for MCP environment
    mcp_logger = logging.getLogger("mcp")
    
    mcp_servers = []
    mcp_agents = {}
    agent_ports = {}
    
    # Process agent-ports argument if provided
    if args.agent_ports:
        for port_spec in args.agent_ports:
            if ':' not in port_spec:
                mcp_logger.error(f"Invalid port specification: {port_spec}. Format should be agent_name:port")
                continue
            agent_name, port = port_spec.split(':', 1)
            try:
                agent_ports[agent_name] = int(port)
                mcp_logger.info(f"Using specified port for {agent_name}: {port}")
            except ValueError:
                mcp_logger.error(f"Port must be a number: {port}")
    
    try:
        # Start MCP servers
        if not args.agents_only:
            mcp_logger.info("Starting MCP servers...")
            mcp_servers = await AgentServer.start_mcp_servers(MCP_SERVER_CONFIGS)
            mcp_logger.info(f"Started {len(mcp_servers)} MCP servers")
            
            for server in mcp_servers:
                mcp_logger.info(f"  - {server['name']} (http://localhost:{server['port']})")
        
        # Start standard agents first if specified
        if args.with_standard_agents:
            mcp_logger.info("Starting standard agents...")
            
            agent, port = AgentServer.start_agent(KnowledgeAgent, "knowledge")
            agent_ports["knowledge"] = port
            mcp_logger.info(f"Started Knowledge Agent on port {port}")
            
            agent, port = AgentServer.start_agent(MathAgent, "math")
            agent_ports["math"] = port
            mcp_logger.info(f"Started Math Agent on port {port}")
            
            # Wait a moment for agents to initialize
            await asyncio.sleep(1)
        
        # Start FastAPI MCP agents
        if not args.servers_only:
            mcp_logger.info("Starting FastAPI MCP agents...")
            
            for config in MCP_AGENT_CONFIGS:
                # Import module and class
                module_name = config["class_module"]
                class_name = config["class_name"]
                module = __import__(module_name, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                
                # Get agent name and MCP server configuration
                agent_name = config["name"]
                mcp_servers_config = config.get("mcp_servers", {})
                
                # Get agent connections and update any ports if we started standard agents or they were specified
                agent_connections = config.get("agent_connections", {})
                if agent_connections and agent_ports:
                    for conn_name, conn_url in list(agent_connections.items()):
                        if conn_name in agent_ports:
                            new_url = f"http://localhost:{agent_ports[conn_name]}"
                            agent_connections[conn_name] = new_url
                            mcp_logger.info(f"Updated {agent_name}'s connection to {conn_name}: {new_url}")
                
                # Create FastAPI agent instance
                port = agent_ports.get(agent_name) if agent_name in agent_ports else find_free_port()
                
                mcp_logger.info(f"Creating {agent_name} agent with connections: {agent_connections}")
                if agent_connections:
                    agent = agent_class(mcp_servers=mcp_servers_config, agent_connections=agent_connections)
                else:
                    agent = agent_class(mcp_servers=mcp_servers_config)
                
                # Perform initialization if available
                if hasattr(agent, "initialize") and callable(agent.initialize):
                    await agent.initialize()
                
                # Start server in background thread
                import threading
                server_thread = threading.Thread(
                    target=agent.run,
                    kwargs={"host": "0.0.0.0", "port": port, "debug": False},
                    daemon=True
                )
                server_thread.start()
                
                # Wait a moment for the server to start
                await asyncio.sleep(0.5)
                
                # Register agent information
                extra_info = {
                    "is_mcp": True,
                    "mcp_servers": list(mcp_servers_config.keys())
                }
                
                # Add agent connections if available
                if agent_connections:
                    extra_info["agent_connections"] = list(agent_connections.keys())
                
                AgentServer.register_agent(
                    name=agent_name,
                    agent=agent,
                    port=port,
                    **extra_info
                )
                
                agent_ports[agent_name] = port
                mcp_agents[agent_name] = {
                    "agent": agent,
                    "port": port,
                    "thread": server_thread
                }
                
                mcp_logger.info(f"  - {agent_name} FastAPI MCP agent started (http://localhost:{port})")
                
                # Display agent information
                agent_info = AgentServer.get_agent_info(agent_name)
                if agent_info:
                    mcp_logger.info(f"    - MCP servers: {', '.join(agent_info.get('mcp_servers', []))}")
                    if "agent_connections" in agent_info:
                        mcp_logger.info(f"    - Connected agents: {', '.join(agent_info.get('agent_connections', []))}")
        
        # Confirm all MCP agents are started
        print("MCP environment is running. Press Ctrl+C to stop.")
        
        # Keep program running with infinite loop
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print("\nMCP environment stopping. Executing shutdown procedures...")
    finally:
        # Stop MCP agents
        for name in list(mcp_agents.keys()):
            print(f"{name} MCP agent stopped...")
            AgentServer.stop_agent(name)
        
        # Stop standard agents if we started them
        if args.with_standard_agents:
            print("Stopping standard agents...")
            AgentServer.stop_agent("knowledge")
            AgentServer.stop_agent("math")
        
        # Stop MCP servers
        if mcp_servers:
            print("MCP servers stopped...")
            AgentServer.stop_mcp_servers(mcp_servers)
        
        print("All MCP agents and servers have been stopped")


def run_mcp_command(args):
    """Run the MCP command by executing the async function."""
    # Create and use a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the start_mcp_environment function
        loop.run_until_complete(start_mcp_environment(args))
    except KeyboardInterrupt:
        print("\nMCP environment stopped.")
    finally:
        loop.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Agent Network CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start agent servers")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available agents")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query the agent network")
    query_parser.add_argument("--agent", help="Specific agent to query (knowledge, math, mcp_weather, mcp_travel)")
    query_parser.add_argument("--router-type", default="keyword", choices=["keyword", "ai"], 
                              help="Type of routing to use (default: keyword)")
    query_parser.add_argument("--agent-ports", nargs="+", 
                              help="Custom agent ports in format 'agent_name:port' (e.g., 'weather:59983')")
    query_parser.add_argument("query", nargs="?", help="The query text")
    
    # Conversation command
    conv_parser = subparsers.add_parser("conversation", help="Run a multi-agent conversation")
    conv_parser.add_argument("--workflow", help="Comma-separated list of agent names in workflow order")
    conv_parser.add_argument("--agent-ports", nargs="+", 
                             help="Custom agent ports in format 'agent_name:port' (e.g., 'weather:59983')")
    conv_parser.add_argument("query", nargs="?", help="The initial query text")
    
    # MCP command
    mcp_parser = subparsers.add_parser("mcp", help="Start MCP environment")
    mcp_parser.add_argument("--servers-only", action="store_true", help="Start only MCP servers")
    mcp_parser.add_argument("--agents-only", action="store_true", help="Start only MCP agents")
    mcp_parser.add_argument("--with-standard-agents", action="store_true", help="Also start standard agents (knowledge, math)")
    mcp_parser.add_argument("--agent-ports", nargs="+", 
                           help="Custom agent ports in format 'agent_name:port' (e.g., 'mcp_weather:53537 mcp_travel:53543')")
    
    # New command: start-agent (starts a single agent with configurable connections)
    start_agent_parser = subparsers.add_parser("start-agent", help="Start a single agent with configurable connections")
    start_agent_parser.add_argument("--agent", required=True, 
                                   help="Agent to start (knowledge, math, mcp_weather, mcp_travel)")
    start_agent_parser.add_argument("--port", type=int, 
                                  help="Port to use for this agent (if not specified, a free port will be found)")
    start_agent_parser.add_argument("--connect-to", nargs="+", 
                                   help="Agents to connect to in format 'agent_name:port' (e.g., 'weather:53537')")
    
    args = parser.parse_args()
    
    if args.command == "start":
        # Create and use a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(start_all_agents())
        finally:
            loop.close()
    elif args.command == "list":
        list_agents()
    elif args.command == "query":
        query_agent(args)
    elif args.command == "conversation":
        run_conversation(args)
    elif args.command == "mcp":
        run_mcp_command(args)
    elif args.command == "start-agent":
        run_single_agent_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 