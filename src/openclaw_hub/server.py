"""Main MCP server implementation for OpenClaw Hub."""

import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openclaw-hub")

# Initialize MCP server
app = Server("openclaw-hub")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return list of available MCP tools.
    
    This is the capability discovery mechanism - OpenClaw calls this
    to learn what the hub can do without needing to remember.
    """
    return [
        Tool(
            name="hub.health",
            description="Check OpenClaw Hub health status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="hub.capabilities",
            description="List all available domains and their capabilities",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution requests.
    
    Routes tool calls to appropriate handlers based on tool name.
    """
    if name == "hub.health":
        return await health_check()
    elif name == "hub.capabilities":
        return await list_capabilities()
    else:
        raise ValueError(f"Unknown tool: {name}")


async def health_check() -> list[TextContent]:
    """Check server health status."""
    logger.info("Health check requested")
    
    return [
        TextContent(
            type="text",
            text="✅ OpenClaw Hub is healthy\n\nStatus: Operational\nVersion: 0.1.0\nDomains loaded: 0 (core only)"
        )
    ]


async def list_capabilities() -> list[TextContent]:
    """List all available capabilities across all domains."""
    logger.info("Capabilities list requested")
    
    capabilities = {
        "core": {
            "health": "Check server health status",
            "capabilities": "List all available capabilities",
        },
        "domains": {
            "media": "Not yet loaded (coming in Issue #4-6)",
            "git": "Not yet loaded (coming in Issue #7)",
        }
    }
    
    output = "# OpenClaw Hub Capabilities\n\n"
    output += "## Core Tools\n"
    for tool, desc in capabilities["core"].items():
        output += f"- `hub.{tool}`: {desc}\n"
    
    output += "\n## Domains\n"
    for domain, status in capabilities["domains"].items():
        output += f"- **{domain}**: {status}\n"
    
    return [TextContent(type="text", text=output)]


async def main() -> None:
    """Run the MCP server."""
    logger.info("Starting OpenClaw Hub MCP server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
