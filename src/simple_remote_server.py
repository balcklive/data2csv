"""Simplified Remote MCP Server with working endpoints."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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
        "description": "Remote MCP server with HTTP transport",
        "endpoints": {
            "mcp": "/mcp (POST for JSON-RPC requests)",
            "health": "/health"
        },
        "transport": "HTTP",
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

@app.post("/mcp")
async def handle_mcp_request(request: Request):
    """Handle MCP JSON-RPC requests."""
    try:
        body = await request.json()
        mcp_request = MCPRequest(**body)

        logger.info(f"Processing {mcp_request.method} request")

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
            return MCPResponse(id=mcp_request.id, result=result).model_dump(exclude_none=True)

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
            return MCPResponse(id=mcp_request.id, result={"tools": tools}).model_dump(exclude_none=True)

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
                        response = CSVConverter.convert_to_csv(request_obj)
                        result = {
                            "content": [{"type": "text", "text": response.content if response.success else f"Error: {response.message}"}],
                            "isError": not response.success
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
                            response = ExcelConverter.convert_to_excel_with_styling(request_obj)
                        else:
                            response = ExcelConverter.convert_to_excel(request_obj)
                        result = {
                            "content": [{"type": "text", "text": response.content if response.success else f"Error: {response.message}"}],
                            "isError": not response.success
                        }
                else:
                    result = {
                        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                        "isError": True
                    }

                return MCPResponse(id=mcp_request.id, result=result).model_dump(exclude_none=True)

            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                result = {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
                return MCPResponse(id=mcp_request.id, result=result).model_dump(exclude_none=True)

        else:
            return MCPResponse(
                id=mcp_request.id,
                error={"code": -32601, "message": f"Method not found: {mcp_request.method}"}
            ).model_dump(exclude_none=True)

    except Exception as e:
        logger.error(f"Request processing error: {e}")
        return MCPResponse(
            error={"code": -32603, "message": "Internal error", "data": str(e)}
        ).model_dump(exclude_none=True)