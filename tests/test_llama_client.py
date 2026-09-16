from typing import Any

import pytest

from qwen_mcp.config import Settings
from qwen_mcp.llama_client import LlamaClient


class FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeAsyncClient:
    instances = 0

    def __init__(self, timeout: float):
        self.timeout = timeout
        self.closed = False
        self.calls: list[str] = []
        type(self).instances += 1

    async def get(self, url: str) -> FakeResponse:
        self.calls.append(url)
        return FakeResponse({"data": []})

    async def post(self, url: str, json: dict[str, Any]) -> FakeResponse:
        del json
        self.calls.append(url)
        return FakeResponse({"choices": [{"message": {"content": '{"kind":"final"}'}}]})

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_client_reuses_one_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.instances = 0
    monkeypatch.setattr("qwen_mcp.llama_client.httpx.AsyncClient", FakeAsyncClient)
    client = LlamaClient(Settings())

    await client.health()
    await client.complete_json([{"role": "user", "content": "hi"}], {})
    await client.aclose()

    assert FakeAsyncClient.instances == 1
    assert client._client.closed is True
    assert len(client._client.calls) == 2
