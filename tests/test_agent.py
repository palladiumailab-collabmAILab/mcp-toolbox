from pathlib import Path
from typing import Any

import pytest

from qwen_mcp.agent import run_agent
from qwen_mcp.config import Settings


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        del messages, response_schema
        self.calls += 1
        if self.calls == 1:
            return {
                "kind": "tool",
                "tool": "read_file",
                "arguments": {"path": "example.py", "start_line": 1, "end_line": 5},
                "answer": "",
            }
        return {
            "kind": "final",
            "tool": None,
            "arguments": {},
            "answer": "example.py:1 contains the implementation.",
        }


@pytest.mark.asyncio
async def test_agent_executes_read_only_tool_loop(tmp_path: Path) -> None:
    (tmp_path / "example.py").write_text("print('ok')\n", encoding="utf-8")
    result = await run_agent(
        "Locate the implementation",
        str(tmp_path),
        settings=Settings(max_rounds=4),
        client=FakeClient(),
    )

    assert result["answer"] == "example.py:1 contains the implementation."
    assert result["trace"] == [
        {
            "tool": "read_file",
            "arguments": {"path": "example.py", "start_line": 1, "end_line": 5},
        }
    ]
