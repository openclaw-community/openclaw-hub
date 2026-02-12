"""
MCP Server management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()
router = APIRouter()


class AddServerRequest(BaseModel):
    """Request to add an MCP server"""
    name: str
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None


def get_mcp_manager():
    """Get MCP manager from app state"""
    from ..main import mcp_manager
    if mcp_manager is None:
        raise HTTPException(status_code=503, detail="MCP manager not initialized")
    return mcp_manager


@router.post("/v1/mcp/servers")
async def add_server(
    request: AddServerRequest,
    manager = Depends(get_mcp_manager)
):
    """Add and connect to an MCP server"""
    try:
        await manager.add_server(
            name=request.name,
            command=request.command,
            args=request.args,
            env=request.env
        )
        return {"status": "connected", "server": request.name}
    
    except Exception as e:
        logger.error("add_server_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/mcp/servers")
async def list_servers(manager = Depends(get_mcp_manager)):
    """List all connected MCP servers"""
    servers = manager.list_servers()
    return {"servers": servers}


@router.get("/v1/mcp/servers/{server_name}/tools")
async def list_tools(
    server_name: str,
    manager = Depends(get_mcp_manager)
):
    """List available tools from a specific server"""
    try:
        tools = await manager.list_tools(server_name)
        return {"server": server_name, "tools": tools}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error("list_tools_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
