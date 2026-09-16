from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from .agent import run_agent
from .config import Settings
from .llama_client import LlamaClient

mcp = MCPServer(
    "qwen-coder-subagent",
    instructions=(
        "Read-only local coding worker backed by Qwen3-Coder. "
        "Use qwen_delegate for bounded repository investigation; apply changes in the parent agent."
    ),
)


@mcp.tool()
async def qwen_health() -> dict[str, Any]:
    """Check whether the configured local llama.cpp OpenAI-compatible endpoint is reachable."""
    settings = Settings.from_env()
    return await LlamaClient(settings).health()


@mcp.tool()
async def qwen_delegate(task: str, workspace: str, max_rounds: int | None = None) -> dict[str, Any]:
    """Delegate a bounded, read-only coding or repository research task to local Qwen."""
    return await run_agent(task, workspace, max_rounds=max_rounds)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
