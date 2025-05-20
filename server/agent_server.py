"""
Agent server management.
"""

import asyncio
import importlib
import multiprocessing
import os
import signal
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from config import logger
from utils.network_utils import find_free_port

# Dictionary to store running agents and their process information
_running_agents = {}

# Dictionary to store running MCP servers and their process information
_running_mcp_servers = {}


def run_agent_process(agent, host, port, name):
    """
    Run an agent in a separate process.

    Args:
        agent: Agent instance
        host: Host to bind to
        port: Port to listen on
        name: Agent name for logging
    """
    try:
        agent.run(host=host, port=port)
    except Exception as e:
        logger.error(f"Error running agent {name}: {e}")


def run_mcp_server_process(server, host, port, server_var):
    """
    Run an MCP server in a separate process.

    Args:
        server: MCP server instance
        host: Host to bind to
        port: Port to listen on
        server_var: Server variable name for logging
    """
    try:
        server.run(host=host, port=port)
    except Exception as e:
        logger.error(f"Error running MCP server {server_var}: {e}")


class AgentServer:
    """Agent server management class."""

    @staticmethod
    def start_agent(
        agent_class, name: str, port: Optional[int] = None, **kwargs
    ) -> Tuple[Any, int]:
        """
        Start an agent server in a separate process.

        Args:
            agent_class: The agent class to instantiate
            name: Name identifier for the agent
            port: Optional port to use (if not provided, a free port will be found)
            **kwargs: Additional arguments to pass to the agent constructor

        Returns:
            Tuple of (agent instance, port)
        """
        # Stop the agent if it's already running with the same name
        if name in _running_agents:
            AgentServer.stop_agent(name)

        # Find a free port if none is provided
        if port is None:
            port = find_free_port()

        # Create the agent instance
        agent = agent_class(**kwargs)

        # Start the agent in a separate process
        process = multiprocessing.Process(
            target=run_agent_process, args=(agent, "0.0.0.0", port, name), daemon=True
        )
        process.start()

        # Record agent information
        _running_agents[name] = {
            "agent": agent,
            "process": process,
            "port": port,
            "endpoint": f"http://localhost:{port}",
            "is_mcp": False,
        }

        logger.info(f"Started agent {name} on port {port}")

        # Wait a moment for the agent to start
        time.sleep(0.5)

        return agent, port

    @staticmethod
    def register_agent(
        name: str,
        agent: Any,
        port: int,
        is_mcp: bool = False,
        mcp_servers: Optional[List[str]] = None,
        agent_connections: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        """
        Register an agent (for externally launched agents)

        Args:
            name: Agent name
            agent: Agent instance
            port: Port being used
            is_mcp: Whether this is an MCP-enabled agent
            mcp_servers: List of connected MCP server names
            agent_connections: List of connected agent names
            **kwargs: Additional arguments to store with the agent info
        """
        # Overwrite if an agent with the same name is already registered
        if name in _running_agents:
            logger.warning(f"Agent {name} already registered. Overwriting.")

        # Record agent information
        agent_info = {
            "agent": agent,
            "process": None,  # None for externally managed processes
            "port": port,
            "endpoint": f"http://localhost:{port}",
            "is_mcp": is_mcp,
        }

        # Add additional information for MCP agents
        if is_mcp and mcp_servers:
            agent_info["mcp_servers"] = mcp_servers

        # Add information about connected agents
        if agent_connections:
            agent_info["agent_connections"] = agent_connections

        # Add any other provided information
        agent_info.update(kwargs)

        _running_agents[name] = agent_info
        logger.info(f"Registered agent {name} on port {port}")

    @staticmethod
    async def start_mcp_agent(
        agent_class,
        name: str,
        mcp_servers: Optional[Dict[str, str]] = None,
        port: Optional[int] = None,
        **kwargs,
    ) -> Tuple[Any, int]:
        """
        Start an MCP-enabled agent server.

        Args:
            agent_class: The MCP agent class to instantiate
            name: Name identifier for the agent
            mcp_servers: Dictionary of MCP server connections
            port: Optional port to use (if not provided, a free port will be found)
            **kwargs: Additional arguments to pass to the agent constructor

        Returns:
            Tuple of (agent instance, port)
        """
        # Stop the agent if it's already running with the same name
        if name in _running_agents:
            AgentServer.stop_agent(name)

        # Find a free port if none is provided
        if port is None:
            port = find_free_port()

        # Create the agent instance
        if mcp_servers:
            kwargs["mcp_servers"] = mcp_servers

        agent = agent_class(**kwargs)

        # Initialize asynchronously if needed
        if hasattr(agent, "initialize") and callable(agent.initialize):
            try:
                await agent.initialize()
            except Exception as e:
                logger.error(f"Error initializing MCP agent {name}: {e}")
                raise

        # Start the agent in a separate process
        process = multiprocessing.Process(
            target=run_agent_process, args=(agent, "0.0.0.0", port, name), daemon=True
        )
        process.start()

        # Record agent information
        _running_agents[name] = {
            "agent": agent,
            "process": process,
            "port": port,
            "endpoint": f"http://localhost:{port}",
            "is_mcp": True,
        }

        # Add MCP server information
        if mcp_servers:
            _running_agents[name]["mcp_servers"] = list(mcp_servers.keys())

        # Add MCP tool information if available
        if hasattr(agent, "mcp_tools") and agent.mcp_tools:
            _running_agents[name]["mcp_tools"] = agent.mcp_tools

        # Add agent connections information if available
        if hasattr(agent, "agent_connections") and agent.agent_connections:
            _running_agents[name]["agent_connections"] = list(
                agent.agent_connections.keys()
            )

        logger.info(f"Started MCP agent {name} on port {port}")

        # Wait a moment for the agent to start
        time.sleep(0.5)

        return agent, port

    @staticmethod
    def stop_agent(name: str) -> bool:
        """
        Stop a running agent.

        Args:
            name: Name identifier for the agent

        Returns:
            True if successfully stopped, False otherwise
        """
        if name not in _running_agents:
            logger.warning(f"Agent {name} not running")
            return False

        agent_info = _running_agents[name]
        process = agent_info.get("process")

        if process:
            try:
                # Terminate the process if it's running
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)  # Wait for 2 seconds

                    # Force kill if it's still alive
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=1)
            except Exception as e:
                logger.error(f"Error stopping agent {name}: {e}")

        # Remove agent information
        del _running_agents[name]
        logger.info(f"Stopped agent {name}")
        return True

    @staticmethod
    def get_agent_info(name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a running agent.

        Args:
            name: Name identifier for the agent

        Returns:
            Dictionary of agent information or None if not found
        """
        return _running_agents.get(name)

    @staticmethod
    def list_running_agents() -> List[str]:
        """
        Get a list of all running agents.

        Returns:
            List of agent names
        """
        return list(_running_agents.keys())

    @staticmethod
    async def start_mcp_servers(
        server_configs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Start MCP servers from configurations.

        Args:
            server_configs: List of server configurations

        Returns:
            List of started MCP server info
        """
        started_servers = []

        for config in server_configs:
            module_name = config["module"]
            server_var = config["server_var"]
            port = config.get("port")

            # Import the module
            try:
                module = importlib.import_module(module_name)
                server = getattr(module, server_var)
            except (ImportError, AttributeError) as e:
                logger.error(
                    f"Failed to import MCP server {server_var} from {module_name}: {e}"
                )
                continue

            # Start the server
            if port is None:
                port = find_free_port()

            # Start the server in a separate process
            process = multiprocessing.Process(
                target=run_mcp_server_process,
                args=(server, "0.0.0.0", port, server_var),
                daemon=True,
            )
            process.start()

            # Record server information
            server_info = {
                "name": server_var,
                "module": module_name,
                "port": port,
                "process": process,
                "url": f"http://localhost:{port}",
            }

            _running_mcp_servers[server_var] = server_info
            started_servers.append(server_info)

            logger.info(f"Started MCP server {server_var} on port {port}")

            # Wait a moment for the server to start
            time.sleep(0.5)

        return started_servers

    @staticmethod
    def stop_mcp_servers(server_infos: List[Dict[str, Any]]) -> None:
        """
        Stop running MCP servers.

        Args:
            server_infos: List of server info dictionaries
        """
        for server_info in server_infos:
            name = server_info["name"]
            process = server_info["process"]

            if process and process.is_alive():
                try:
                    process.terminate()
                    process.join(timeout=2)

                    # Force kill if it's still alive
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=1)
                except Exception as e:
                    logger.error(f"Error stopping MCP server {name}: {e}")

            # Remove server information
            if name in _running_mcp_servers:
                del _running_mcp_servers[name]

            logger.info(f"Stopped MCP server {name}")

    @staticmethod
    def is_agent_running(name: str) -> bool:
        """
        Check if an agent is running.

        Args:
            name: Name identifier for the agent

        Returns:
            True if agent is running, False otherwise
        """
        if name not in _running_agents:
            return False

        agent_info = _running_agents[name]
        process = agent_info.get("process")

        # Consider as running if process is None (externally managed)
        if process is None:
            return True

        return process.is_alive()
