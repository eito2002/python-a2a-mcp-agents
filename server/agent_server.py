"""
Agent server management module.
"""

import asyncio
import threading
import time
import multiprocessing
from typing import Dict, List, Optional, Any, Tuple, Union

from config import logger, running_agents
from utils import find_free_port

def run_agent_server(agent, host, port, name):
    """
    Run an agent server process.
    
    Args:
        agent: The agent instance to run
        host: Host address to bind to
        port: Port to bind to
        name: Agent name for logging
    """
    try:
        logger.info(f"Starting {name} agent server on port {port}")
        agent.run(host=host, port=port)
    except Exception as e:
        logger.error(f"Error in {name} agent server: {e}")

def run_mcp_agent_server(agent, host, port, name):
    """
    Run an MCP agent server process with proper async handling.
    
    Args:
        agent: The MCP agent instance to run
        host: Host address to bind to
        port: Port to bind to
        name: Agent name for logging
    """
    try:
        # 新しいイベントループを作成してセット
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info(f"Starting {name} MCP agent server on port {port}")
        agent.run(host=host, port=port)
    except Exception as e:
        logger.error(f"Error in {name} MCP agent server: {e}")

def run_mcp_server(server, host, port):
    """
    Run an MCP server process.
    
    Args:
        server: The MCP server instance to run
        host: Host address to bind to
        port: Port to bind to
    """
    try:
        logger.info(f"Starting MCP server {server.name} on port {port}")
        server.run(host=host, port=port)
    except Exception as e:
        logger.error(f"Error in MCP server: {e}")

class AgentServer:
    """
    Manages the lifecycle of agent server processes.
    """
    
    @staticmethod
    def start_agent(agent_class, name: str) -> Tuple[Any, int]:
        """
        Start an agent server process.
        
        Args:
            agent_class: The agent class to instantiate
            name: The name for the agent
            
        Returns:
            Tuple of (agent instance, server port)
        """
        # Find an available port
        port = find_free_port()
        
        # Create the agent instance
        agent = agent_class()
        
        # Update the agent card URL with the actual port
        if hasattr(agent, "agent_card") and hasattr(agent.agent_card, "url"):
            agent.agent_card.url = f"http://localhost:{port}"
        
        # Start the server in a separate thread
        server_thread = threading.Thread(
            target=run_agent_server, 
            args=(agent, "0.0.0.0", port, name), 
            daemon=True
        )
        server_thread.start()
        
        # Wait for a moment to let the server start
        time.sleep(1)
        
        # Store the agent in the running agents registry
        running_agents[name] = {
            "instance": agent,
            "thread": server_thread,
            "port": port
        }
        
        return agent, port
    
    @staticmethod
    async def start_mcp_agent(agent_class, name: str, mcp_servers: Optional[Dict[str, str]] = None) -> Tuple[Any, int]:
        """
        Start an MCP-enabled agent server process.
        
        Args:
            agent_class: The MCP-enabled agent class to instantiate
            name: The name for the agent
            mcp_servers: Dictionary mapping server names to URLs
            
        Returns:
            Tuple of (agent instance, server port)
        """
        # Find an available port
        port = find_free_port()
        
        # Create the agent instance with MCP servers
        agent = agent_class(mcp_servers=mcp_servers)
        
        # Update the agent card URL with the actual port
        if hasattr(agent, "agent_card") and hasattr(agent.agent_card, "url"):
            agent.agent_card.url = f"http://localhost:{port}"
        
        # Initialize MCP connections
        logger.info(f"Initializing MCP connections for {name} agent")
        await agent.initialize()
        
        # Start the server in a separate thread
        server_thread = threading.Thread(
            target=run_mcp_agent_server, 
            args=(agent, "0.0.0.0", port, name), 
            daemon=True
        )
        server_thread.start()
        
        # Wait for a moment to let the server start
        time.sleep(1)
        
        # Store the agent in the running agents registry with MCP flag
        running_agents[name] = {
            "instance": agent,
            "thread": server_thread,
            "port": port,
            "is_mcp": True
        }
        
        return agent, port
    
    @staticmethod
    def stop_agent(name: str) -> bool:
        """
        Stop a running agent server.
        
        Args:
            name: The name of the agent to stop
            
        Returns:
            True if the agent was stopped, False otherwise
        """
        if name not in running_agents:
            logger.warning(f"Agent {name} not found in running agents")
            return False
        
        try:
            # Get the agent
            agent_info = running_agents[name]
            agent = agent_info["instance"]
            
            # Check if it's an MCP agent
            is_mcp = agent_info.get("is_mcp", False)
            
            # For MCP agents, close connections asynchronously
            if is_mcp:
                # Create an event loop for closing MCP connections
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Close MCP connections
                    loop.run_until_complete(agent.close())
                finally:
                    loop.close()
            
            # Stop the server
            if hasattr(agent, "server") and agent.server:
                logger.info(f"Stopping {name} agent server")
                agent.server.shutdown()
                agent.server.server_close()
            
            # Remove from running agents
            del running_agents[name]
            
            return True
        except Exception as e:
            logger.error(f"Error stopping agent {name}: {e}")
            return False
    
    @staticmethod
    def list_running_agents() -> List[str]:
        """
        List all running agent names.
        
        Returns:
            List of running agent names
        """
        return list(running_agents.keys())
    
    @staticmethod
    def get_agent_info(name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a running agent.
        
        Args:
            name: The name of the agent
            
        Returns:
            Dictionary with agent information or None if not found
        """
        if name not in running_agents:
            return None
        
        agent_info = running_agents[name]
        info = {
            "name": name,
            "port": agent_info["port"],
            "endpoint": f"http://localhost:{agent_info['port']}",
            "is_mcp": agent_info.get("is_mcp", False)
        }
        
        # Add MCP-specific information if available
        if info["is_mcp"]:
            agent = agent_info["instance"]
            if hasattr(agent, "mcp_servers"):
                info["mcp_servers"] = list(agent.mcp_servers.keys())
            if hasattr(agent, "_tool_capabilities"):
                info["mcp_tools"] = list(agent._tool_capabilities.keys())
        
        return info
    
    @staticmethod
    async def start_mcp_servers(server_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Start MCP server processes.
        
        Args:
            server_configs: List of server configuration dictionaries
                Each config should have 'module', 'server_var', and 'port' keys
                
        Returns:
            List of dictionaries with server information
        """
        started_servers = []
        
        for config in server_configs:
            try:
                module_name = config["module"]
                server_var = config["server_var"]
                port = config["port"]
                
                # Import the module
                module = __import__(module_name, fromlist=[server_var])
                
                # Get the server instance
                server = getattr(module, server_var)
                
                # Start the server in a separate process
                process = multiprocessing.Process(
                    target=run_mcp_server,
                    args=(server, "0.0.0.0", port),
                    daemon=True
                )
                process.start()
                
                # Wait for a moment to let the server start
                time.sleep(1)
                
                # Store server information
                server_info = {
                    "name": server.name,
                    "port": port,
                    "process": process,
                    "endpoint": f"http://localhost:{port}"
                }
                
                started_servers.append(server_info)
                logger.info(f"Started MCP server {server.name} on port {port}")
                
            except Exception as e:
                logger.error(f"Failed to start MCP server from {config['module']}: {e}")
        
        return started_servers
    
    @staticmethod
    def stop_mcp_servers(server_infos: List[Dict[str, Any]]) -> None:
        """
        Stop MCP server processes.
        
        Args:
            server_infos: List of server information dictionaries
        """
        for info in server_infos:
            try:
                process = info["process"]
                if process.is_alive():
                    logger.info(f"Stopping MCP server {info['name']}")
                    process.terminate()
                    process.join(timeout=5)
                    
                    if process.is_alive():
                        logger.warning(f"MCP server {info['name']} did not terminate, killing")
                        process.kill()
            except Exception as e:
                logger.error(f"Error stopping MCP server {info['name']}: {e}") 