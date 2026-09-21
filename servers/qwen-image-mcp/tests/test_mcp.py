import asyncio

from mcp import Client

from qwen_image_mcp.mcp_server import create_server


class FakeEngine:
    def generate(self, prompt, **kwargs):
        return {"path": "/tmp/generated.png", "prompt": prompt, **kwargs}

    def edit(self, prompt, image_paths, **kwargs):
        return {
            "path": "/tmp/edited.png",
            "prompt": prompt,
            "reference_image_count": len(image_paths),
            **kwargs,
        }

    def status(self):
        return {"model_loaded": False, "model_id": "Qwen/Qwen-Image-2.1"}


def test_mcp_exposes_generation_edit_and_status_tools() -> None:
    async def scenario() -> None:
        server = create_server(FakeEngine())
        async with Client(server, raise_exceptions=True) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools.tools] == [
                "qwen_image_generate",
                "qwen_image_edit",
                "qwen_image_status",
            ]

            generated = await client.call_tool(
                "qwen_image_generate",
                {
                    "prompt": "a mountain",
                    "aspect_ratio": "3:2",
                    "seed": 9,
                    "transparent": False,
                },
            )
            assert generated.is_error is False
            assert generated.structured_content["path"] == "/tmp/generated.png"

            edited = await client.call_tool(
                "qwen_image_edit",
                {
                    "prompt": "combine them",
                    "image_paths": ["a.png", "b.png"],
                },
            )
            assert edited.is_error is False
            assert edited.structured_content["reference_image_count"] == 2

            status = await client.call_tool("qwen_image_status", {})
            assert status.is_error is False
            assert status.structured_content["model_id"] == "Qwen/Qwen-Image-2.1"

    asyncio.run(scenario())
