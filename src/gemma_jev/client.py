from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ResponseLike(Protocol):
    def __enter__(self) -> "ResponseLike": ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> object: ...

    def read(self) -> bytes: ...


UrlOpener = Callable[..., ResponseLike]


@dataclass(slots=True)
class VLLMClient:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_s: float = 60.0
    max_tokens: int = 256
    extra_body: dict[str, Any] = field(default_factory=dict)
    opener: UrlOpener = field(default=urlopen, repr=False)

    def _v1_url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/v1/chat/completions"):
            base = base[: -len("/chat/completions")]
        elif not base.endswith("/v1"):
            base += "/v1"
        return base + "/" + path.lstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def complete(self, messages: list[dict[str, Any]]) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        payload.update(self.extra_body)

        request = Request(
            self._v1_url("chat/completions"),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.timeout_s) as response:
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

    def status(self) -> dict[str, Any]:
        request = Request(
            self._v1_url("models"),
            headers=self._headers(),
            method="GET",
        )
        try:
            with self.opener(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return {
                "reachable": True,
                "configured_model": self.model,
                "served_models": [],
                "model_available": False,
                "error": f"http_{exc.code}",
            }
        except URLError:
            return {
                "reachable": False,
                "configured_model": self.model,
                "served_models": [],
                "model_available": False,
                "error": "connection_error",
            }

        data = body.get("data", []) if isinstance(body, dict) else []
        served_models = [
            str(item["id"])
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
        return {
            "reachable": True,
            "configured_model": self.model,
            "served_models": served_models,
            "model_available": self.model in served_models,
            "error": None,
        }
