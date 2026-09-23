"""End-to-end tests for the acrux_context MCP tool (regression: Stores Protocol bug)."""

import pytest

from acrux.config import AcruxConfig
from acrux.mcp_server import AcruxMCPServer


@pytest.mark.asyncio
async def test_context_tool_returns_stored_fact(tmp_path) -> None:
    server = AcruxMCPServer(AcruxConfig(data_dir=tmp_path))

    stored = await server._handle_tool(
        "acrux_remember_fact",
        {
            "project": "demo",
            "content": "The deploy script lives in scripts/deploy.sh",
            "source": "test",
            "tags": ["deploy"],
        },
    )
    assert "Fact stored" in stored[0].text

    result = await server._handle_tool(
        "acrux_context", {"project": "demo", "query": "deploy script"}
    )
    assert "deploy.sh" in result[0].text


@pytest.mark.asyncio
async def test_context_tool_empty_query_returns_message(tmp_path) -> None:
    server = AcruxMCPServer(AcruxConfig(data_dir=tmp_path))
    result = await server._handle_tool("acrux_context", {"project": "demo", "query": ""})
    assert result[0].text == "No relevant memories."


@pytest.mark.asyncio
async def test_unknown_tool_is_reported(tmp_path) -> None:
    server = AcruxMCPServer(AcruxConfig(data_dir=tmp_path))
    result = await server._handle_tool("acrux_nonexistent", {})
    assert "Unknown tool" in result[0].text
