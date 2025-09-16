#!/usr/bin/env python3
"""Run the FastMCP Data2CSV server."""

import sys
import os
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    parser = argparse.ArgumentParser(description="Data2CSV FastMCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind to")
    args = parser.parse_args()

    print(f"Starting Data2CSV FastMCP Server on {args.host}:{args.port}")

    try:
        from src.fastmcp_server import mcp
        mcp.run(transport="sse", host=args.host, port=args.port)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()