"""
MCP Server Manager
Connects to and manages Model Context Protocol servers
"""

import asyncio
from typing import Dict, List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import structlog

logger = structlog.get_logger()


class MCPManager:
    """Manages connections to MCP servers"""
    
    def __init__(self):
        self.servers: Dict[str, ClientSession] = {}
        self.server_configs: Dict[str, dict] = {}
        
    async def add_server(
        self,
        name: str,
        command: str,
        args: List[str] = None,
        env: Dict[str, str] = None
    ):
        """Add and connect to an MCP server"""
        logger.info("adding_mcp_server", name=name, command=command)
        
        try:
            # Store configuration
            self.server_configs[name] = {
                "command": command,
                "args": args or [],
                "env": env or {}
            }
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=command,
                args=args or [],
                env=env
            )
            
            # Connect to server
            stdio_transport = await stdio_client(server_params)
            read, write = stdio_transport
            
            # Create session
            session = ClientSession(read, write)
            await session.initialize()
            
            self.servers[name] = session
            
            logger.info("mcp_server_connected", name=name)
            
        except Exception as e:
            logger.error("mcp_server_failed", name=name, error=str(e))
            raise
    
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """List available tools from a server"""
        if server_name not in self.servers:
            raise ValueError(f"Server '{server_name}' not connected")
        
        session = self.servers[server_name]
        
        try:
            response = await session.list_tools()
            tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in response.tools
            ]
            
            logger.info("tools_listed", server=server_name, count=len(tools))
            return tools
            
        except Exception as e:
            logger.error("list_tools_failed", server=server_name, error=str(e))
            raise
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Execute a tool on an MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"Server '{server_name}' not connected")
        
        session = self.servers[server_name]
        
        logger.info(
            "calling_tool",
            server=server_name,
            tool=tool_name,
            args=arguments
        )
        
        try:
            response = await session.call_tool(tool_name, arguments)
            
            # Extract content from response
            result = None
            if response.content:
                # Handle different content types
                if len(response.content) > 0:
                    first_content = response.content[0]
                    if hasattr(first_content, 'text'):
                        result = first_content.text
                    else:
                        result = str(first_content)
            
            logger.info("tool_executed", server=server_name, tool=tool_name)
            return result
            
        except Exception as e:
            logger.error(
                "tool_execution_failed",
                server=server_name,
                tool=tool_name,
                error=str(e)
            )
            raise
    
    async def close_all(self):
        """Close all MCP server connections"""
        for name, session in self.servers.items():
            try:
                await session.__aexit__(None, None, None)
                logger.info("mcp_server_closed", name=name)
            except Exception as e:
                logger.error("close_failed", name=name, error=str(e))
        
        self.servers.clear()
    
    def list_servers(self) -> List[str]:
        """List all connected server names"""
        return list(self.servers.keys())
