from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol

from .models import DecisionRequest, DecisionResult
from .protocol import build_messages, parse_decision


class CompletionClient(Protocol):
    def complete(self, messages: list[dict[str, Any]]) -> str: ...


class DecisionEngine:
    def __init__(self, client: CompletionClient) -> None:
        self.client = client

    def decide(self, request: DecisionRequest) -> DecisionResult:
        messages = build_messages(request)
        started = perf_counter()
        raw = self.client.complete(messages)
        latency_ms = (perf_counter() - started) * 1000.0
        option_ids = tuple(option.id for option in request.options)
        selected, weights, rationale = parse_decision(raw, option_ids)
        return DecisionResult(
            selected_option_id=selected,
            weights=weights,
            rationale=rationale,
            latency_ms=latency_ms,
            raw_text=raw,
        )
