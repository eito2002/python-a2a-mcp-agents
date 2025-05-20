"""
FastAPI based asynchronous agent implementation.
"""

import asyncio
import json
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from python_a2a.models.agent import AgentCard, AgentSkill
from python_a2a.models.content import ErrorContent, TextContent
from python_a2a.models.message import Message, MessageRole
from python_a2a.models.task import Task, TaskState, TaskStatus
from starlette.middleware.cors import CORSMiddleware


class FastAPIAgent:
    """FastAPI based asynchronous agent implementation"""

    def __init__(self, agent_card: AgentCard, **kwargs):
        """
        Initialize the asynchronous agent

        Args:
            agent_card: Card containing agent metadata
            **kwargs: Additional keyword arguments
        """
        self.agent_card = agent_card
        self.tasks = {}  # Task storage
        self.streaming_subscriptions = {}  # Streaming subscriptions
        self.server = None  # Uvicorn server instance

        # Google A2A compatibility settings
        self.use_google_a2a = kwargs.get("google_a2a_compatible", True)

        # Update capabilities
        if not hasattr(self.agent_card, "capabilities"):
            self.agent_card.capabilities = {}
        if isinstance(self.agent_card.capabilities, dict):
            self.agent_card.capabilities["google_a2a_compatible"] = self.use_google_a2a
            self.agent_card.capabilities["parts_array_format"] = self.use_google_a2a
            self.agent_card.capabilities["streaming"] = True

        # Create FastAPI app
        self.app = FastAPI(
            title=self.agent_card.name,
            description=self.agent_card.description,
            version=self.agent_card.version,
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Setup routes
        self._setup_routes()

    def _extract_query_from_task(self, task: Task) -> str:
        """
        Extract query text from a task

        Args:
            task: Task object

        Returns:
            Extracted query text
        """
        if task.message:
            if isinstance(task.message, dict):
                content = task.message.get("content", {})
                if isinstance(content, dict):
                    return content.get("text", "")
        return ""

    def _setup_routes(self):
        """Setup FastAPI endpoints"""

        # Root endpoint
        @self.app.get("/")
        async def root():
            """A2A root endpoint"""
            return {
                "name": self.agent_card.name,
                "description": self.agent_card.description,
                "agent_card_url": "/agent.json",
                "protocol": "a2a",
                "capabilities": self.agent_card.capabilities,
            }

        # Health check endpoint
        @self.app.get("/health")
        async def health():
            """Health check endpoint"""
            return {"status": "ok", "agent": self.agent_card.name}

        @self.app.post("/")
        async def root_post(request: Request):
            """Process POST requests"""
            try:
                data = await request.json()

                # Detect if this is Google A2A format
                is_google_format = False
                if "parts" in data and "role" in data and "content" not in data:
                    is_google_format = True

                # Check if this is a task
                if "id" in data and ("message" in data or "status" in data):
                    return await self._handle_task_request(data, is_google_format)

                # Check if this is a conversation
                if "messages" in data:
                    # Check format of first message
                    if (
                        data["messages"]
                        and "parts" in data["messages"][0]
                        and "role" in data["messages"][0]
                    ):
                        is_google_format = True
                    return await self._handle_conversation_request(
                        data, is_google_format
                    )

                # Process as a single message
                return await self._handle_message_request(data, is_google_format)

            except Exception as e:
                # Return error response
                error_msg = f"Request processing error: {str(e)}"
                if self.use_google_a2a:
                    # Return error in Google A2A format
                    return JSONResponse(
                        status_code=500,
                        content={
                            "role": "agent",
                            "parts": [{"type": "data", "data": {"error": error_msg}}],
                        },
                    )
                else:
                    # Return error in python_a2a format
                    return JSONResponse(
                        status_code=500,
                        content={
                            "content": {"type": "error", "message": error_msg},
                            "role": "system",
                        },
                    )

        # A2A endpoints
        @self.app.get("/a2a")
        async def a2a_index():
            """A2A index endpoint"""
            return {
                "name": self.agent_card.name,
                "description": self.agent_card.description,
                "agent_card_url": "/a2a/agent.json",
                "protocol": "a2a",
                "capabilities": self.agent_card.capabilities,
            }

        @self.app.post("/a2a")
        async def a2a_post(request: Request):
            """A2A POST endpoint"""
            return await root_post(request)

        # Agent card endpoints
        @self.app.get("/a2a/agent.json")
        async def a2a_agent_card():
            """Return the agent card"""
            return self.agent_card.to_dict()

        @self.app.get("/agent.json")
        async def agent_card():
            """Return the agent card (standard location)"""
            return self.agent_card.to_dict()

        # Task endpoints
        @self.app.post("/a2a/tasks/send")
        async def a2a_tasks_send(request: Request):
            """Task send endpoint"""
            try:
                request_data = await request.json()

                # Process as JSON-RPC
                if "jsonrpc" in request_data:
                    rpc_id = request_data.get("id", 1)
                    params = request_data.get("params", {})

                    # Detect format from parameters
                    is_google_format = False
                    if isinstance(params, dict) and "message" in params:
                        message_data = params.get("message", {})
                        if (
                            isinstance(message_data, dict)
                            and "parts" in message_data
                            and "role" in message_data
                        ):
                            is_google_format = True

                    # Process the task
                    result = await self._handle_task_request(params, is_google_format)

                    # Get result data
                    result_data = (
                        result.body.decode() if hasattr(result, "body") else result
                    )
                    if isinstance(result_data, str):
                        result_data = json.loads(result_data)

                    # Return JSON-RPC response
                    return {"jsonrpc": "2.0", "id": rpc_id, "result": result_data}
                else:
                    # Process as direct task send
                    is_google_format = False
                    if "message" in request_data:
                        message_data = request_data.get("message", {})
                        if (
                            isinstance(message_data, dict)
                            and "parts" in message_data
                            and "role" in message_data
                        ):
                            is_google_format = True

                    # Process task request
                    return await self._handle_task_request(
                        request_data, is_google_format
                    )

            except Exception as e:
                # Process error
                if "jsonrpc" in request_data:
                    return JSONResponse(
                        content={
                            "jsonrpc": "2.0",
                            "id": request_data.get("id", 1),
                            "error": {
                                "code": -32603,
                                "message": f"Internal error: {str(e)}",
                            },
                        },
                        status_code=500,
                    )
                else:
                    if self.use_google_a2a:
                        return JSONResponse(
                            content={
                                "role": "agent",
                                "parts": [
                                    {
                                        "type": "data",
                                        "data": {"error": f"Error: {str(e)}"},
                                    }
                                ],
                            },
                            status_code=500,
                        )
                    else:
                        return JSONResponse(
                            content={
                                "content": {
                                    "type": "error",
                                    "message": f"Error: {str(e)}",
                                },
                                "role": "system",
                            },
                            status_code=500,
                        )

        @self.app.post("/tasks/send")
        async def tasks_send(request: Request):
            """Task send endpoint (standard location)"""
            return await a2a_tasks_send(request)

        @self.app.post("/a2a/tasks/get")
        async def a2a_tasks_get(request: Request):
            """Task get endpoint"""
            try:
                request_data = await request.json()

                # Process as JSON-RPC
                if "jsonrpc" in request_data:
                    rpc_id = request_data.get("id", 1)
                    params = request_data.get("params", {})

                    # Get task ID
                    task_id = None
                    if isinstance(params, dict):
                        task_id = params.get("id")

                    # Check if task exists
                    if task_id and task_id in self.tasks:
                        task = self.tasks[task_id]

                        # Format response based on task status
                        if task.status.state == TaskState.COMPLETED:
                            return {
                                "jsonrpc": "2.0",
                                "id": rpc_id,
                                "result": task.to_dict(),
                            }
                        else:
                            # Task still in progress
                            return {
                                "jsonrpc": "2.0",
                                "id": rpc_id,
                                "result": {
                                    "id": task_id,
                                    "status": task.status.to_dict(),
                                },
                            }
                    else:
                        # Task not found
                        return {
                            "jsonrpc": "2.0",
                            "id": rpc_id,
                            "error": {
                                "code": -32600,
                                "message": f"Task with ID {task_id} not found",
                            },
                        }
                else:
                    # Process as direct task get
                    task_id = request_data.get("id")

                    # Check if task exists
                    if task_id and task_id in self.tasks:
                        task = self.tasks[task_id]
                        return task.to_dict()
                    else:
                        # Task not found
                        return JSONResponse(
                            status_code=404,
                            content={"error": f"Task with ID {task_id} not found"},
                        )

            except Exception as e:
                # Process error
                if "jsonrpc" in request_data:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_data.get("id", 1),
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}",
                        },
                    }
                else:
                    return JSONResponse(
                        status_code=500, content={"error": f"Error: {str(e)}"}
                    )

        @self.app.post("/tasks/get")
        async def tasks_get(request: Request):
            """Task get endpoint (standard location)"""
            return await a2a_tasks_get(request)

    async def _handle_message_request(self, data, is_google_format=False):
        """
        Handle message request

        Args:
            data: Request data
            is_google_format: Whether the data is in Google A2A format

        Returns:
            Response data
        """
        try:
            # Convert data to Message object
            message = None

            if is_google_format:
                # Convert from Google A2A format
                message = Message.from_google_a2a(data)
            else:
                # Convert from standard format
                message = Message.from_dict(data)

            # Process the message
            response = await self.handle_message_async(message)

            # Format response
            if is_google_format:
                # Convert to Google A2A format
                return response.to_google_a2a()
            else:
                # Convert to standard format
                return response.to_dict()

        except Exception as e:
            # Handle error
            error_msg = f"Error processing message: {str(e)}"

            if is_google_format:
                return {
                    "role": "agent",
                    "parts": [{"type": "data", "data": {"error": error_msg}}],
                }
            else:
                return {
                    "content": {"type": "error", "message": error_msg},
                    "role": "system",
                }

    async def _handle_task_request(self, data, is_google_format=False):
        """
        Handle task request

        Args:
            data: Request data
            is_google_format: Whether the data is in Google A2A format

        Returns:
            Response data
        """
        try:
            # Convert data to Task object
            task = None

            if "id" in data:
                # Use existing task ID
                task_id = data["id"]
            else:
                # Generate new task ID
                task_id = str(uuid.uuid4())

            # Create or update task
            if task_id in self.tasks:
                task = self.tasks[task_id]

                # Update task with new data
                if "message" in data:
                    task.message = data["message"]
                if "status" in data:
                    task.status = TaskStatus.from_dict(data["status"])
            else:
                # Create new task
                task = Task(
                    id=task_id,
                    message=data.get("message"),
                    status=TaskStatus(state=TaskState.PENDING),
                )
                self.tasks[task_id] = task

            # Process the task
            processed_task = await self.handle_task_async(task)

            # Return task data
            return processed_task.to_dict()

        except Exception as e:
            # Handle error
            error_msg = f"Error processing task: {str(e)}"

            return {
                "id": data.get("id", str(uuid.uuid4())),
                "status": {"state": "failed", "error": error_msg},
            }

    async def _handle_conversation_request(self, data, is_google_format=False):
        """
        Handle conversation request

        Args:
            data: Request data
            is_google_format: Whether the data is in Google A2A format

        Returns:
            Response data
        """
        try:
            # Extract messages
            message_data_list = data.get("messages", [])
            messages = []

            for message_data in message_data_list:
                # Convert message data to Message object
                if is_google_format:
                    # Convert from Google A2A format
                    message = Message.from_google_a2a(message_data)
                else:
                    # Convert from standard format
                    message = Message.from_dict(message_data)

                messages.append(message)

            # Create conversation object
            conversation = {
                "messages": messages,
                "add_message": lambda msg: messages.append(msg),
            }

            # Process the conversation
            processed_conversation = await self.handle_conversation_async(conversation)

            # Format response
            response_messages = []
            for message in processed_conversation["messages"]:
                if is_google_format:
                    response_messages.append(message.to_google_a2a())
                else:
                    response_messages.append(message.to_dict())

            return {"messages": response_messages}

        except Exception as e:
            # Handle error
            error_msg = f"Error processing conversation: {str(e)}"

            if is_google_format:
                return {
                    "messages": [
                        {
                            "role": "agent",
                            "parts": [{"type": "data", "data": {"error": error_msg}}],
                        }
                    ]
                }
            else:
                return {
                    "messages": [
                        {
                            "content": {"type": "error", "message": error_msg},
                            "role": "system",
                        }
                    ]
                }

    async def handle_message_async(self, message: Message) -> Message:
        """
        Asynchronous message handler

        Hook for subclasses to override.

        Args:
            message: Received A2A message

        Returns:
            Response message
        """
        # Default implementation: echo
        if message.content.type == "text":
            return Message(
                content=TextContent(text=message.content.text),  # Simply echo the text
                role=MessageRole.AGENT,
                parent_message_id=message.message_id,
                conversation_id=message.conversation_id,
            )
        else:
            # Basic handling for non-text content
            return Message(
                content=TextContent(text="Received non-text message"),
                role=MessageRole.AGENT,
                parent_message_id=message.message_id,
                conversation_id=message.conversation_id,
            )

    async def handle_task_async(self, task: Task) -> Task:
        """
        Asynchronous task handler

        Hook for subclasses to override.

        Args:
            task: Received A2A task

        Returns:
            Processed task
        """
        # Extract message from task
        message_data = task.message or {}

        try:
            # Convert to Message object
            message = None

            if isinstance(message_data, dict):
                # Check for Google A2A format
                if (
                    "parts" in message_data
                    and "role" in message_data
                    and "content" not in message_data
                ):
                    try:
                        message = Message.from_google_a2a(message_data)
                    except Exception:
                        # If conversion fails, try standard format
                        pass

                # Try standard format
                if message is None:
                    try:
                        message = Message.from_dict(message_data)
                    except Exception:
                        # If standard format also fails, create basic message
                        text = ""
                        if "content" in message_data and isinstance(
                            message_data["content"], dict
                        ):
                            # python_a2a format
                            content = message_data["content"]
                            if "text" in content:
                                text = content["text"]
                            elif "message" in content:
                                text = content["message"]
                        elif "parts" in message_data:
                            # Google A2A format
                            for part in message_data["parts"]:
                                if (
                                    isinstance(part, dict)
                                    and part.get("type") == "text"
                                    and "text" in part
                                ):
                                    text = part["text"]
                                    break

                        message = Message(
                            content=TextContent(text=text), role=MessageRole.USER
                        )
            else:
                # If already a Message object, use directly
                message = message_data

            # Call message handler
            response = await self.handle_message_async(message)

            # Create artifacts based on response content type
            if hasattr(response, "content"):
                content_type = getattr(response.content, "type", None)

                if content_type == "text":
                    # Process TextContent
                    task.artifacts = [
                        {"parts": [{"type": "text", "text": response.content.text}]}
                    ]
                elif content_type == "error":
                    # Process ErrorContent
                    task.artifacts = [
                        {
                            "parts": [
                                {"type": "error", "message": response.content.message}
                            ]
                        }
                    ]
                else:
                    # Process other content types
                    task.artifacts = [
                        {"parts": [{"type": "text", "text": str(response.content)}]}
                    ]
            else:
                # Process response without content
                task.artifacts = [{"parts": [{"type": "text", "text": str(response)}]}]
        except Exception as e:
            # Handle message handler errors
            task.artifacts = [
                {
                    "parts": [
                        {"type": "error", "message": f"Message handler error: {str(e)}"}
                    ]
                }
            ]

        # Mark as completed
        task.status = TaskStatus(state=TaskState.COMPLETED)
        return task

    async def handle_conversation_async(self, conversation):
        """
        Asynchronous conversation handler

        Hook for subclasses to override.

        Args:
            conversation: Received A2A conversation

        Returns:
            Processed conversation
        """
        # Extract last message
        if conversation.messages:
            last_message = conversation.messages[-1]
            # Process message
            response = await self.handle_message_async(last_message)
            # Add response to conversation
            conversation.add_message(response)

        return conversation

    def _create_uvicorn_config(self, host, port, log_level):
        """
        Create Uvicorn server configuration

        Args:
            host: Host to bind to
            port: Port to listen on
            log_level: Log level for Uvicorn

        Returns:
            Uvicorn configuration object
        """
        import logging

        # Create Uvicorn config
        config = uvicorn.Config(app=self.app, host=host, port=port, log_level=log_level)

        return config

    def run(self, host="0.0.0.0", port=5000, debug=False):
        """
        Start the server

        This method can be called in a thread without blocking.
        It uses a separate thread for Uvicorn if needed.

        Args:
            host: Host to bind to (default: "0.0.0.0")
            port: Port to listen on (default: 5000)
            debug: Enable debug mode (default: False)
        """
        # Update agent card URL with actual port
        if hasattr(self.agent_card, "url"):
            self.agent_card.url = f"http://{host}:{port}"

        log_level = "info" if debug else "warning"

        # Create uvicorn config
        config = self._create_uvicorn_config(host, port, log_level)
        server = uvicorn.Server(config)
        self.server = server

        # Run the server
        server.run()
