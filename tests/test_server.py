"""Tests for core MCP server functionality."""

import pytest
from openclaw_hub.server import health_check, list_capabilities


@pytest.mark.asyncio
async def test_health_check():
    """Test that health check returns expected status."""
    result = await health_check()
    
    assert len(result) == 1
    assert result[0].type == "text"
    assert "OpenClaw Hub is healthy" in result[0].text
    assert "Version: 0.1.0" in result[0].text


@pytest.mark.asyncio
async def test_list_capabilities():
    """Test that capabilities list is returned correctly."""
    result = await list_capabilities()
    
    assert len(result) == 1
    assert result[0].type == "text"
    assert "OpenClaw Hub Capabilities" in result[0].text
    assert "hub.health" in result[0].text
    assert "hub.capabilities" in result[0].text
