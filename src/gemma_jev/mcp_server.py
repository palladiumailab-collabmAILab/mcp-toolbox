from __future__ import annotations

from functools import cache
from typing import Any

from mcp.server import MCPServer

from .engine import DecisionEngine
from .models import DecisionRequest
from .runtime import build_engine_from_env


@cache
def _default_engine() -> DecisionEngine:
    return build_engine_from_env()


def create_server(engine: DecisionEngine | None = None) -> MCPServer:
    server = MCPServer("Gemma-Jev")

    @server.tool()
    def decide(
        context: str,
        options: list[dict[str, str]],
        criteria: list[str] | None = None,
        image_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate candidate options jointly and return a structured decision."""
        request = DecisionRequest.from_dict(
            {
                "context": context,
                "options": options,
                "criteria": criteria or [],
                "image_urls": image_urls or [],
            }
        )
        decision_engine = engine if engine is not None else _default_engine()
        return decision_engine.decide(request).to_dict()

    return server


mcp = create_server()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
