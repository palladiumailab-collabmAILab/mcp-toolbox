import asyncio

from mcp import Client

from gemma_jev.engine import DecisionEngine
from gemma_jev.mcp_server import create_server


class FakeClient:
    def complete(self, messages):
        assert messages
        return (
            '{"selected_option_id":"B","weights":{"A":1,"B":4},'
            '"rationale":"lower expected latency"}'
        )


def test_mcp_decide_returns_structured_result() -> None:
    async def scenario() -> None:
        server = create_server(DecisionEngine(FakeClient()))
        async with Client(server, raise_exceptions=True) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools.tools] == ["decide"]

            result = await client.call_tool(
                "decide",
                {
                    "context": "choose an implementation",
                    "criteria": ["latency"],
                    "options": [
                        {"id": "A", "text": "sequential path"},
                        {"id": "B", "text": "parallel path"},
                    ],
                },
            )

            assert result.is_error is False
            assert result.structured_content is not None
            assert result.structured_content["selected_option_id"] == "B"
            assert result.structured_content["weights"] == {"A": 0.2, "B": 0.8}
            assert result.structured_content["confidence"] == 0.8
            assert result.structured_content["rationale"] == "lower expected latency"

    asyncio.run(scenario())
