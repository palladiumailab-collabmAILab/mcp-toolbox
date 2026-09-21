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


def test_mcp_decide_and_status_return_structured_results() -> None:
    async def scenario() -> None:
        server = create_server(
            DecisionEngine(FakeClient()),
            status_provider=lambda: {
                "reachable": True,
                "configured_model": "model",
                "served_models": ["model"],
                "model_available": True,
                "error": None,
            },
        )
        async with Client(server, raise_exceptions=True) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools.tools] == ["decide", "status"]

            decision = await client.call_tool(
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

            assert decision.is_error is False
            assert decision.structured_content is not None
            assert decision.structured_content["selected_option_id"] == "B"
            assert decision.structured_content["weights"] == {"A": 0.2, "B": 0.8}
            assert decision.structured_content["confidence"] == 0.8
            assert decision.structured_content["rationale"] == "lower expected latency"

            status = await client.call_tool("status", {})
            assert status.is_error is False
            assert status.structured_content is not None
            assert status.structured_content["reachable"] is True
            assert status.structured_content["model_available"] is True

    asyncio.run(scenario())
