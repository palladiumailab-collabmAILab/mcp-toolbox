import subprocess
from pathlib import Path
from typing import Any

import pytest

from qwen_mcp.agent import run_agent
from qwen_mcp.config import Settings


def _git_workspace(path: Path) -> Path:
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True, text=True)
    return path


def _settings(workspace: Path, max_rounds: int) -> Settings:
    return Settings(max_rounds=max_rounds, allowed_workspace_roots=(str(workspace),))


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


class LegacyToolClient:
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
                "name": "read_file",
                "arguments": {"path": "example.py", "start_line": 1, "end_line": 5},
            }
        return {"answer": "example.py:1 contains the implementation."}


class InvalidLegacyToolClient:
    async def complete_json(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        del messages, response_schema
        return {"name": "run_shell", "arguments": {"command": "echo unsafe"}}


class StaticClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        del messages, response_schema
        return self.payload


@pytest.mark.asyncio
async def test_agent_executes_read_only_tool_loop(tmp_path: Path) -> None:
    workspace = _git_workspace(tmp_path)
    (workspace / "example.py").write_text("print('ok')\n", encoding="utf-8")
    result = await run_agent(
        "Locate the implementation",
        str(workspace),
        settings=_settings(workspace, 4),
        client=FakeClient(),
    )

    assert result["answer"] == "example.py:1 contains the implementation."
    assert result["trace"] == [
        {
            "tool": "read_file",
            "arguments": {"path": "example.py", "start_line": 1, "end_line": 5},
        }
    ]


@pytest.mark.asyncio
async def test_agent_normalizes_legacy_tool_and_answer_envelopes(tmp_path: Path) -> None:
    workspace = _git_workspace(tmp_path)
    (workspace / "example.py").write_text("print('ok')\n", encoding="utf-8")
    result = await run_agent(
        "Locate the implementation",
        str(workspace),
        settings=_settings(workspace, 4),
        client=LegacyToolClient(),
    )

    assert result["answer"] == "example.py:1 contains the implementation."
    assert result["trace"] == [
        {
            "tool": "read_file",
            "arguments": {"path": "example.py", "start_line": 1, "end_line": 5},
        }
    ]


@pytest.mark.asyncio
async def test_agent_rejects_unknown_legacy_tool(tmp_path: Path) -> None:
    workspace = _git_workspace(tmp_path)
    with pytest.raises(RuntimeError, match="invalid Qwen action kind"):
        await run_agent(
            "Run an unsafe command",
            str(workspace),
            settings=_settings(workspace, 1),
            client=InvalidLegacyToolClient(),
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "final"},
        {"kind": "final", "answer": None},
        {"kind": "final", "answer": 123},
        {"kind": "final", "answer": "   "},
    ],
)
@pytest.mark.asyncio
async def test_agent_rejects_malformed_final_answer(
    tmp_path: Path,
    payload: dict[str, Any],
) -> None:
    workspace = _git_workspace(tmp_path)
    with pytest.raises(RuntimeError, match="invalid final answer"):
        await run_agent(
            "Return a final answer",
            str(workspace),
            settings=_settings(workspace, 1),
            client=StaticClient(payload),
        )
