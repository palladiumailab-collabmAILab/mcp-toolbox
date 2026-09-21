from __future__ import annotations

from functools import cache
from typing import Any

from mcp.server import MCPServer

from .engine import QwenImageEngine


@cache
def _default_engine() -> QwenImageEngine:
    return QwenImageEngine.from_env()


def create_server(engine: QwenImageEngine | None = None) -> MCPServer:
    server = MCPServer("Qwen-Image-2.1")
    image_engine = engine if engine is not None else _default_engine()

    @server.tool()
    def qwen_image_generate(
        prompt: str,
        aspect_ratio: str = "1:1",
        num_inference_steps: int = 40,
        seed: int = 42,
        transparent: bool = False,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        """Generate a PNG with Qwen-Image-2.1 and return the local output path."""
        return image_engine.generate(
            prompt,
            aspect_ratio=aspect_ratio,
            num_inference_steps=num_inference_steps,
            seed=seed,
            transparent=transparent,
            output_name=output_name,
        )

    @server.tool()
    def qwen_image_edit(
        prompt: str,
        image_paths: list[str],
        aspect_ratio: str = "source",
        num_inference_steps: int = 40,
        seed: int = 42,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        """Edit 1-10 local images; source aspect ratio is preserved by default."""
        return image_engine.edit(
            prompt,
            image_paths,
            aspect_ratio=aspect_ratio,
            num_inference_steps=num_inference_steps,
            seed=seed,
            output_name=output_name,
        )

    @server.tool()
    def qwen_image_status() -> dict[str, Any]:
        """Report configuration and whether local model dependencies are installed."""
        return image_engine.status()

    return server


mcp = create_server()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
