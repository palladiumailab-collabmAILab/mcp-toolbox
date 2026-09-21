from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DecisionOption:
    id: str
    text: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("option id must be non-empty")
        if not self.text.strip():
            raise ValueError("option text must be non-empty")


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    context: str
    options: tuple[DecisionOption, ...]
    criteria: tuple[str, ...] = field(default_factory=tuple)
    image_urls: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if len(self.options) < 2:
            raise ValueError("at least two options are required")
        ids = [option.id for option in self.options]
        if len(ids) != len(set(ids)):
            raise ValueError("option ids must be unique")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DecisionRequest":
        options = tuple(
            DecisionOption(id=str(item["id"]), text=str(item["text"]))
            for item in payload["options"]
        )
        return cls(
            context=str(payload.get("context", "")),
            options=options,
            criteria=tuple(str(x) for x in payload.get("criteria", [])),
            image_urls=tuple(str(x) for x in payload.get("image_urls", [])),
        )


@dataclass(frozen=True, slots=True)
class DecisionResult:
    selected_option_id: str
    weights: dict[str, float]
    rationale: str
    latency_ms: float
    raw_text: str

    @property
    def confidence(self) -> float:
        return self.weights[self.selected_option_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_option_id": self.selected_option_id,
            "weights": self.weights,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "latency_ms": self.latency_ms,
        }
