"""Simplified Remote MCP Server with working endpoints."""

import json
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .models.data_models import ConvertRequest
from .tools.csv_converter import CSVConverter
from .tools.excel_converter import ExcelConverter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data2CSV Remote MCP Server",
    description="Remote MCP server for converting 2D data to CSV and Excel formats",
    version="0.1.0"
)

# Connection Manager for SSE
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, asyncio.Queue] = {}

    async def connect(self, connection_id: str) -> asyncio.Queue:
        """Create a new connection and return its message queue."""
        queue = asyncio.Queue()
        self.connections[connection_id] = queue
        logger.info(f"New SSE connection established: {connection_id}")
        return queue

    async def disconnect(self, connection_id: str):
        """Remove a connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            logger.info(f"SSE connection closed: {connection_id}")

    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """Send a message to a specific connection."""
        if connection_id in self.connections:
            await self.connections[connection_id].put(message)
        else:
            logger.warning(f"Attempt to send message to non-existent connection: {connection_id}")

# Initialize connection manager
connection_manager = ConnectionManager()

# MCP Protocol Models
from typing import Union

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int, float]] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int, float]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

# Session storage
sessions = {}

@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "Data2CSV Remote MCP Server",
        "version": "0.1.0",
        "description": "Remote MCP server with SSE transport",
        "endpoints": {
            "sse": "/sse (GET for Server-Sent Events connection)",
            "messages": "/messages/{connection_id} (POST for JSON-RPC requests)",
            "health": "/health"
        },
        "transport": "SSE",
        "protocol_version": "2025-06-18",
        "status": "running"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sessions": len(sessions)
    }

@app.get("/sse")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint for MCP communication."""
    connection_id = str(uuid.uuid4())
    queue = await connection_manager.connect(connection_id)

    async def event_generator():
        try:
            # Send initial endpoint information for SSE transport
            endpoint_info = {
                "type": "endpoint",
                "endpoint": f"http://{request.url.hostname}:{request.url.port}/messages/{connection_id}",
                "transport": "sse",
                "connection_id": connection_id
            }
            yield f"data: {json.dumps(endpoint_info)}\n\n"

            # Listen for messages in the queue
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    logger.debug(f"Sending message to {connection_id}: {message}")
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send keep-alive ping
                    ping_message = {'type': 'ping', 'timestamp': datetime.now().isoformat()}
                    logger.debug(f"Sending keep-alive ping to {connection_id}")
                    yield f"data: {json.dumps(ping_message)}\n\n"
                except asyncio.CancelledError:
                    logger.info(f"SSE connection {connection_id} cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in SSE stream for {connection_id}: {e}")
                    break
        except asyncio.CancelledError:
            logger.info(f"SSE event generator for {connection_id} cancelled")
        except Exception as e:
            logger.error(f"SSE connection error for {connection_id}: {e}")
        finally:
            logger.info(f"Cleaning up SSE connection: {connection_id}")
            await connection_manager.disconnect(connection_id)

    return EventSourceResponse(event_generator())

@app.post("/messages/{connection_id}")
async def handle_messages(connection_id: str, request: Request):
    """Handle MCP JSON-RPC messages from clients."""
    try:
        # Check if connection exists
        if connection_id not in connection_manager.connections:
            logger.warning(f"Received message for non-existent connection: {connection_id}")
            raise HTTPException(status_code=404, detail="Connection not found")

        body = await request.json()
        mcp_request = MCPRequest(**body)

        logger.info(f"Processing {mcp_request.method} request for connection {connection_id}")

        if mcp_request.method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "serverInfo": {
                    "name": "data2csv",
                    "version": "0.1.0"
                },
                "capabilities": {
                    "tools": {"listChanged": False}
                }
            }
            response = MCPResponse(id=mcp_request.id, result=result).model_dump(exclude_none=True)
            await connection_manager.send_message(connection_id, response)

        elif mcp_request.method == "tools/list":
            tools = [
                {
                    "name": "convert_to_csv",
                    "description": "Convert 2D array data to CSV format",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "array", "description": "2D array data"},
                            "headers": {"type": "array", "description": "Optional headers"},
                            "filename": {"type": "string", "default": "data"}
                        },
                        "required": ["data"]
                    }
                },
                {
                    "name": "convert_to_excel",
                    "description": "Convert 2D array data to Excel format",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "array", "description": "2D array data"},
                            "headers": {"type": "array", "description": "Optional headers"},
                            "filename": {"type": "string", "default": "data"},
                            "styled": {"type": "boolean", "default": False}
                        },
                        "required": ["data"]
                    }
                }
            ]
            response = MCPResponse(id=mcp_request.id, result={"tools": tools}).model_dump(exclude_none=True)
            await connection_manager.send_message(connection_id, response)

        elif mcp_request.method == "tools/call":
            params = mcp_request.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            try:
                if tool_name == "convert_to_csv":
                    data = arguments.get("data", [])
                    headers = arguments.get("headers")
                    filename = arguments.get("filename", "data")

                    # Validate and convert
                    is_valid, error_msg = CSVConverter.validate_data(data)
                    if not is_valid:
                        result = {
                            "content": [{"type": "text", "text": f"Error: {error_msg}"}],
                            "isError": True
                        }
                    else:
                        request_obj = ConvertRequest(data=data, headers=headers, filename=filename)
                        response_obj = CSVConverter.convert_to_csv(request_obj)
                        result = {
                            "content": [{"type": "text", "text": response_obj.content if response_obj.success else f"Error: {response_obj.message}"}],
                            "isError": not response_obj.success
                        }

                elif tool_name == "convert_to_excel":
                    data = arguments.get("data", [])
                    headers = arguments.get("headers")
                    filename = arguments.get("filename", "data")
                    styled = arguments.get("styled", False)

                    # Validate and convert
                    is_valid, error_msg = CSVConverter.validate_data(data)
                    if not is_valid:
                        result = {
                            "content": [{"type": "text", "text": f"Error: {error_msg}"}],
                            "isError": True
                        }
                    else:
                        request_obj = ConvertRequest(data=data, headers=headers, filename=filename)
                        if styled:
                            response_obj = ExcelConverter.convert_to_excel_with_styling(request_obj)
                        else:
                            response_obj = ExcelConverter.convert_to_excel(request_obj)
                        result = {
                            "content": [{"type": "text", "text": response_obj.content if response_obj.success else f"Error: {response_obj.message}"}],
                            "isError": not response_obj.success
                        }
                else:
                    result = {
                        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                        "isError": True
                    }

                response = MCPResponse(id=mcp_request.id, result=result).model_dump(exclude_none=True)
                await connection_manager.send_message(connection_id, response)

            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                result = {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
                response = MCPResponse(id=mcp_request.id, result=result).model_dump(exclude_none=True)
                await connection_manager.send_message(connection_id, response)

        else:
            response = MCPResponse(
                id=mcp_request.id,
                error={"code": -32601, "message": f"Method not found: {mcp_request.method}"}
            ).model_dump(exclude_none=True)
            await connection_manager.send_message(connection_id, response)

        return {"status": "message_queued"}

    except Exception as e:
        logger.error(f"Request processing error: {e}")
        error_response = MCPResponse(
            error={"code": -32603, "message": "Internal error", "data": str(e)}
        ).model_dump(exclude_none=True)
        await connection_manager.send_message(connection_id, error_response)
        return {"status": "error", "message": str(e)}

