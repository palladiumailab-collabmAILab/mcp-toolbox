from __future__ import annotations

import json
from typing import Any, Protocol

from .config import Settings
from .llama_client import LlamaClient
from .repo_tools import RepoContext, RepoToolError

_ALLOWED_TOOLS = ["list_files", "search_text", "read_file", "git_status", "git_diff"]

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["tool", "final"]},
        "tool": {"type": ["string", "null"], "enum": [*_ALLOWED_TOOLS, None]},
        "arguments": {"type": "object"},
        "answer": {"type": "string"},
    },
    "required": ["kind", "tool", "arguments", "answer"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = """You are a read-only coding subagent working under a parent Codex agent.
You may investigate the supplied repository only through the allowed tools.
Never claim to edit files, run arbitrary commands, install packages, commit, push, or deploy.
Use tools when repository evidence is needed. Prefer targeted searches and bounded reads.
When finished, return a concise answer with concrete file paths and relevant line evidence.
The parent agent will decide and apply any changes.

Return exactly one JSON object in one of these two forms.
Tool request example:
{"kind":"tool","tool":"read_file","arguments":{"path":"README.md","start_line":1,"end_line":80},"answer":""}
Final answer example:
{"kind":"final","tool":null,"arguments":{},"answer":"README.md:1 contains the project title."}
Do not use a function-call envelope such as {"name":"read_file","arguments":{...}}.

Allowed tools and arguments:
- list_files: {path?: string, max_entries?: integer}
- search_text: {query: string, path?: string, max_matches?: integer}
- read_file: {path: string, start_line?: integer, end_line?: integer}
- git_status: {}
- git_diff: {staged?: boolean, path?: string}
"""


class CompletionClient(Protocol):
    async def complete_json(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> dict[str, Any]: ...


def _normalize_action(action: dict[str, Any]) -> dict[str, Any]:
    kind = action.get("kind")
    if kind in {"tool", "final"}:
        return action

    arguments = action.get("arguments")
    legacy_tool = action.get("name") or action.get("tool")
    if legacy_tool in _ALLOWED_TOOLS and isinstance(arguments, dict):
        return {
            "kind": "tool",
            "tool": legacy_tool,
            "arguments": arguments,
            "answer": "",
        }

    answer = action.get("answer")
    if isinstance(answer, str) and answer.strip():
        return {
            "kind": "final",
            "tool": None,
            "arguments": {},
            "answer": answer,
        }

    return action


async def run_agent(
    task: str,
    workspace: str,
    *,
    settings: Settings | None = None,
    client: CompletionClient | None = None,
    max_rounds: int | None = None,
) -> dict[str, Any]:
    effective_settings = settings or Settings.from_env()
    repo = RepoContext.create(workspace, effective_settings.max_tool_output_chars)
    rounds = max_rounds if max_rounds is not None else effective_settings.max_rounds
    if rounds < 1 or rounds > 32:
        raise ValueError("max_rounds must be between 1 and 32")

    owned_model = None if client is not None else LlamaClient(effective_settings)
    model = client or owned_model
    assert model is not None
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Workspace: {repo.root}\nTask: {task}",
        },
    ]
    trace: list[dict[str, Any]] = []

    try:
        for _ in range(rounds):
            action = _normalize_action(await model.complete_json(messages, _RESPONSE_SCHEMA))
            kind = action.get("kind")
            if kind == "final":
                answer = action.get("answer")
                if not isinstance(answer, str) or not answer.strip():
                    raise RuntimeError("Qwen returned an invalid final answer")
                return {"answer": answer.strip(), "rounds": len(trace) + 1, "trace": trace}

            if kind != "tool":
                raise RuntimeError(f"invalid Qwen action kind: {kind!r}")
            tool = action.get("tool")
            arguments = action.get("arguments")
            if tool not in _ALLOWED_TOOLS or not isinstance(arguments, dict):
                raise RuntimeError("Qwen requested an invalid tool action")

            try:
                result = repo.execute(str(tool), arguments)
            except (RepoToolError, KeyError, TypeError, ValueError) as exc:
                result = f"ERROR: {exc}"

            trace.append({"tool": tool, "arguments": arguments})
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(action, ensure_ascii=False),
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool result for {tool}:\n{result}",
                }
            )

        return {
            "answer": "Qwen reached the tool-round limit before producing a final answer.",
            "rounds": rounds,
            "trace": trace,
        }
    finally:
        if owned_model is not None:
            await owned_model.aclose()
