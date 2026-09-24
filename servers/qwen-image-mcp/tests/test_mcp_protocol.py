from __future__ import annotations

import asyncio
from typing import Any

from mcp import Client

from qwen_image_mcp.mcp_server import create_server


class FakeImageEngine:
    def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        return {"operation": "generate", "prompt": prompt, **kwargs}

    def edit(self, prompt: str, image_paths: list[str], **kwargs: Any) -> dict[str, Any]:
        return {
            "operation": "edit",
            "prompt": prompt,
            "image_paths": image_paths,
            **kwargs,
        }

    def status(self) -> dict[str, Any]:
        return {
            "model_id": "Qwen/Qwen-Image-2.1",
            "model_loaded": False,
            "quantization_type": "nf4",
        }


def test_every_tool_is_callable_through_mcp() -> None:
    async def scenario() -> None:
        async with Client(create_server(FakeImageEngine()), raise_exceptions=True) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools.tools] == [
                "qwen_image_generate",
                "qwen_image_edit",
                "qwen_image_status",
            ]

            generated = await client.call_tool(
                "qwen_image_generate",
                {"prompt": "a transparent blue cube", "transparent": True},
            )
            assert generated.is_error is False
            assert generated.structured_content is not None
            assert generated.structured_content["operation"] == "generate"
            assert generated.structured_content["transparent"] is True

            edited = await client.call_tool(
                "qwen_image_edit",
                {"prompt": "add a shadow", "image_paths": ["reference.png"]},
            )
            assert edited.is_error is False
            assert edited.structured_content is not None
            assert edited.structured_content["operation"] == "edit"
            assert edited.structured_content["image_paths"] == ["reference.png"]

            status = await client.call_tool("qwen_image_status", {})
            assert status.is_error is False
            assert status.structured_content is not None
            assert status.structured_content["quantization_type"] == "nf4"

    asyncio.run(scenario())
