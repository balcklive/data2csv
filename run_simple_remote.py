#!/usr/bin/env python3
"""Run the simplified remote MCP server."""

import sys
import os
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()

    print(f"Starting Simplified Remote MCP Server on {args.host}:{args.port}")

    try:
        import uvicorn
        from src.simple_remote_server import app
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()