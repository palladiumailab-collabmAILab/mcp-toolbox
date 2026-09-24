from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mcp import Client

import qwen_mcp.server as server_module


class FakeLlamaClient:
    def __init__(self, settings: object) -> None:
        self.settings = settings

    async def __aenter__(self) -> FakeLlamaClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "configured_model": "qwen3-coder-30b-a3b",
            "server": {"data": [{"id": "qwen3-coder-30b-a3b"}]},
        }


def test_every_tool_is_callable_through_mcp(monkeypatch, tmp_path: Path) -> None:
    async def fake_run_agent(
        task: str,
        workspace: str,
        max_rounds: int | None = None,
    ) -> dict[str, Any]:
        return {
            "answer": f"reviewed: {task}",
            "workspace": workspace,
            "rounds": max_rounds,
        }

    monkeypatch.setattr(server_module, "LlamaClient", FakeLlamaClient)
    monkeypatch.setattr(server_module, "run_agent", fake_run_agent)

    async def scenario() -> None:
        async with Client(server_module.mcp, raise_exceptions=True) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools.tools] == ["qwen_health", "qwen_delegate"]

            health = await client.call_tool("qwen_health", {})
            assert health.is_error is False
            assert health.structured_content is not None
            assert health.structured_content["ok"] is True

            delegated = await client.call_tool(
                "qwen_delegate",
                {
                    "task": "find protocol regressions",
                    "workspace": str(tmp_path),
                    "max_rounds": 2,
                },
            )
            assert delegated.is_error is False
            assert delegated.structured_content is not None
            assert delegated.structured_content["answer"] == "reviewed: find protocol regressions"
            assert delegated.structured_content["rounds"] == 2

    asyncio.run(scenario())
