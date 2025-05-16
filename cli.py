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
from agents import WeatherAgent, KnowledgeAgent
from agents.mcp_weather_agent import MCPWeatherAgent
from server import AgentServer
from conversation import ConversationOrchestrator
from utils import find_free_port
from client import A2ANetworkClient
from python_a2a.models import Message, MessageRole, TextContent

# MCPサーバーの設定
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
    }
]

# MCPエージェントの設定
MCP_AGENT_CONFIGS = [
    {
        "name": "weather",
        "class_module": "agents.mcp_weather_agent",
        "class_name": "MCPWeatherAgent",
        "mcp_servers": {
            "weather": "http://localhost:5001",
            "maps": "http://localhost:5002"
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
            agent_type = "MCP対応" if info.get('is_mcp', False) else "標準"
            print(f"- {agent_name}: {endpoint} ({agent_type})")
            
            # MCPエージェントの場合は追加情報を表示
            if info.get('is_mcp', False):
                if 'mcp_servers' in info:
                    print(f"  - 接続先MCPサーバー: {', '.join(info['mcp_servers'])}")
                if 'mcp_tools' in info:
                    print(f"  - 利用可能なツール: {len(info['mcp_tools'])}")


async def start_all_agents():
    """Start all available agent types."""
    # 標準エージェントの起動
    agent, port = AgentServer.start_agent(WeatherAgent, "weather")
    print(f"Started Weather Agent on port {port}")
    
    agent, port = AgentServer.start_agent(KnowledgeAgent, "knowledge")
    print(f"Started Knowledge Agent on port {port}")
    
    # MCP対応エージェントの起動
    mcp_servers = {
        "weather": "http://localhost:5001",
        "maps": "http://localhost:5002"
    }
    
    try:
        agent, port = await AgentServer.start_mcp_agent(
            MCPWeatherAgent, 
            "mcp_weather",
            mcp_servers=mcp_servers
        )
        print(f"Started MCP Weather Agent on port {port}")
    except Exception as e:
        print(f"Failed to start MCP Weather Agent: {e}")
    
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
    # MCP環境用のロガーを取得
    mcp_logger = logging.getLogger("mcp")
    
    mcp_servers = []
    mcp_agents = {}
    
    try:
        # MCPサーバーの起動
        if not args.agents_only:
            mcp_logger.info("MCPサーバーを起動しています...")
            mcp_servers = await AgentServer.start_mcp_servers(MCP_SERVER_CONFIGS)
            mcp_logger.info(f"{len(mcp_servers)}個のMCPサーバーが起動しました")
            
            for server in mcp_servers:
                mcp_logger.info(f"  - {server['name']} (http://localhost:{server['port']})")
        
        # MCPエージェントの起動
        if not args.servers_only:
            mcp_logger.info("MCPエージェントを起動しています...")
            
            for config in MCP_AGENT_CONFIGS:
                # モジュールとクラスをインポート
                module_name = config["class_module"]
                class_name = config["class_name"]
                module = __import__(module_name, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                
                # エージェントの起動
                agent_name = config["name"]
                mcp_servers_config = config.get("mcp_servers")
                
                agent, port = await AgentServer.start_mcp_agent(
                    agent_class=agent_class,
                    name=agent_name,
                    mcp_servers=mcp_servers_config
                )
                
                mcp_agents[agent_name] = {
                    "agent": agent,
                    "port": port
                }
                
                mcp_logger.info(f"  - {agent_name} MCPエージェントが起動しました (http://localhost:{port})")
                
                # エージェント情報を表示
                agent_info = AgentServer.get_agent_info(agent_name)
                if agent_info:
                    mcp_logger.info(f"    - MCPサーバー: {', '.join(agent_info.get('mcp_servers', []))}")
                    mcp_logger.info(f"    - 利用可能なツール: {len(agent_info.get('mcp_tools', []))}")
        
        # すべてのMCPエージェントが起動したことを確認
        print("MCP環境が起動しました。Ctrl+Cで停止します。")
        
        # 無限ループでプログラムを維持
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print("\nMCP環境が停止しました。終了処理を実行します...")
    finally:
        # MCPエージェントの停止
        for name in list(mcp_agents.keys()):
            print(f"{name} MCPエージェントが停止しました...")
            AgentServer.stop_agent(name)
        
        # MCPサーバーの停止
        if mcp_servers:
            print("MCPサーバーが停止しました...")
            AgentServer.stop_mcp_servers(mcp_servers)
        
        print("すべてのMCPエージェントとサーバーが停止しました")


def run_mcp_command(args):
    """Run the MCP command by executing the async function."""
    # 新しいイベントループを作成して使用
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # start_mcp_environment関数を実行
        loop.run_until_complete(start_mcp_environment(args))
    except KeyboardInterrupt:
        print("\nMCP環境が停止しました。")
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
    query_parser.add_argument("--agent", help="Specific agent to query (weather, knowledge, mcp_weather)")
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
    
    args = parser.parse_args()
    
    if args.command == "start":
        # 新しいイベントループを作成して使用
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 