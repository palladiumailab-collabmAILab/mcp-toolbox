import pytest
from mcp import Client

from qwen_mcp.server import mcp


@pytest.mark.asyncio
async def test_mcp_exposes_expected_tools() -> None:
    async with Client(mcp) as client:
        result = await client.list_tools()
    names = {tool.name for tool in result.tools}
    assert {"qwen_health", "qwen_delegate"} <= names
