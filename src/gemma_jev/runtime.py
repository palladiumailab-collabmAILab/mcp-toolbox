from __future__ import annotations

import os

from .client import VLLMClient
from .engine import DecisionEngine
from .media_policy import MediaPolicy
from .model_assets import load_model_spec

_MODEL_SPEC = load_model_spec()

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_MODEL = _MODEL_SPEC.repo_id
DEFAULT_MODEL_REVISION = _MODEL_SPEC.revision
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_TOKENS = 256


def build_client(
    *,
    base_url: str,
    model: str,
    api_key: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> VLLMClient:
    return VLLMClient(
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout_s=timeout_s,
        max_tokens=max_tokens,
    )


def build_engine(
    *,
    base_url: str,
    model: str,
    api_key: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    media_policy: MediaPolicy | None = None,
) -> DecisionEngine:
    return DecisionEngine(
        build_client(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_s=timeout_s,
            max_tokens=max_tokens,
        ),
        media_policy=media_policy or MediaPolicy.from_env(),
    )


def build_client_from_env() -> VLLMClient:
    return build_client(
        base_url=os.getenv("VLLM_BASE_URL", DEFAULT_BASE_URL),
        model=os.getenv("VLLM_MODEL", DEFAULT_MODEL),
        api_key=os.getenv("VLLM_API_KEY"),
        timeout_s=float(os.getenv("VLLM_TIMEOUT_S", str(DEFAULT_TIMEOUT_S))),
        max_tokens=int(os.getenv("VLLM_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
    )


def build_engine_from_env() -> DecisionEngine:
    return DecisionEngine(
        build_client_from_env(),
        media_policy=MediaPolicy.from_env(),
    )
