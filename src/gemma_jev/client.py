from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(slots=True)
class VLLMClient:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_s: float = 60.0
    max_tokens: int = 256
    extra_body: dict[str, Any] = field(default_factory=dict)

    def _url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            return base + "/chat/completions"
        if base.endswith("/v1/chat/completions"):
            return base
        return base + "/v1/chat/completions"

    def complete(self, messages: list[dict[str, Any]]) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        payload.update(self.extra_body)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = Request(
            self._url(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"vLLM returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"failed to reach vLLM: {exc.reason}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("unexpected vLLM response shape") from exc
        if not isinstance(content, str):
            raise RuntimeError("vLLM response content was not text")
        return content
