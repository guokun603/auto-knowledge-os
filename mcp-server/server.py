"""Entry point for the central_auto_kb MCP server.

Prefers the standard MCP stdio server so Codex talks a compliant protocol.
Falls back to the line-based JSON-RPC loop only when the mcp SDK is missing.
"""
from auto_kb.mcp_server import MCP_SDK_AVAILABLE, main, stdio_main

if __name__ == "__main__":
    raise SystemExit(stdio_main() if MCP_SDK_AVAILABLE else main())
