from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    base_url: str = "http://127.0.0.1:8080/v1"
    model: str = "qwen3-coder-30b-a3b"
    timeout_seconds: float = 180.0
    max_rounds: int = 8
    max_output_tokens: int = 2048
    max_tool_output_chars: int = 24_000
    allowed_workspace_roots: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> Settings:
        allowed_roots = tuple(
            item.strip()
            for item in os.getenv("QWEN_ALLOWED_WORKSPACE_ROOTS", "").split(os.pathsep)
            if item.strip()
        )
        return cls(
            base_url=os.getenv("QWEN_BASE_URL", cls.base_url).rstrip("/"),
            model=os.getenv("QWEN_MODEL", cls.model),
            timeout_seconds=float(os.getenv("QWEN_TIMEOUT_SECONDS", str(cls.timeout_seconds))),
            max_rounds=int(os.getenv("QWEN_MAX_ROUNDS", str(cls.max_rounds))),
            max_output_tokens=int(os.getenv("QWEN_MAX_OUTPUT_TOKENS", str(cls.max_output_tokens))),
            max_tool_output_chars=int(
                os.getenv("QWEN_MAX_TOOL_OUTPUT_CHARS", str(cls.max_tool_output_chars))
            ),
            allowed_workspace_roots=allowed_roots,
        )
