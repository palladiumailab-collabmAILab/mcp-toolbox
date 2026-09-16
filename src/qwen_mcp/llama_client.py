from __future__ import annotations

import json
from typing import Any

import httpx

from .config import Settings


class LlamaClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.get(f"{self.settings.base_url}/models")
            response.raise_for_status()
            payload = response.json()
        return {"ok": True, "configured_model": self.settings.model, "server": payload}

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": self.settings.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "schema": response_schema,
            },
        }
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise RuntimeError("llama.cpp returned non-text message content")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise RuntimeError("llama.cpp returned non-object JSON")
        return parsed
