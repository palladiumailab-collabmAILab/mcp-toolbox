from __future__ import annotations

import json
import math
import typing

if typing.TYPE_CHECKING:
    from .models import DecisionRequest


SYSTEM_PROMPT = """You are a compact decision model. Evaluate all candidate options jointly.
Return exactly one JSON object and no prose outside it:
{
  "selected_option_id": "<one supplied id>",
  "weights": {"<id>": <non-negative number>, "...": <number>},
  "rationale": "<concise reason>"
}
The weights are relative decision weights, not calibrated probabilities.
Include every supplied option id.
"""


def _canvas_payload(request: DecisionRequest) -> str:
    data = {
        "context": request.context,
        "criteria": list(request.criteria),
        "options": [{"id": o.id, "text": o.text} for o in request.options],
    }
    return "Evaluate this decision canvas jointly:\n" + json.dumps(
        data, ensure_ascii=False, separators=(",", ":")
    )


def build_messages(request: DecisionRequest) -> list[dict[str, typing.Any]]:
    text = _canvas_payload(request)
    if request.image_urls:
        content: list[dict[str, typing.Any]] = [{"type": "text", "text": text}]
        content.extend(
            {"type": "image_url", "image_url": {"url": url}} for url in request.image_urls
        )
        user_content: str | list[dict[str, typing.Any]] = content
    else:
        user_content = text

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _extract_json_object(text: str) -> dict[str, typing.Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("model output did not contain a JSON object")


def normalize_weights(raw: typing.Any, option_ids: tuple[str, ...]) -> dict[str, float]:
    if isinstance(raw, list):
        converted: dict[str, typing.Any] = {}
        for item in raw:
            if isinstance(item, dict) and "id" in item:
                converted[str(item["id"])] = item.get("weight", item.get("probability"))
        raw = converted

    if not isinstance(raw, dict):
        raise ValueError("weights must be an object or a list of id/weight objects")

    values: dict[str, float] = {}
    for option_id in option_ids:
        value = raw.get(option_id, 0.0)
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid weight for option {option_id!r}") from exc
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"weight for option {option_id!r} must be finite and non-negative")
        values[option_id] = number

    total = sum(values.values())
    if total <= 0:
        raise ValueError("at least one option weight must be positive")
    return {option_id: value / total for option_id, value in values.items()}


def parse_decision(text: str, option_ids: tuple[str, ...]) -> tuple[str, dict[str, float], str]:
    payload = _extract_json_object(text)
    raw_weights = payload.get("weights", payload.get("probabilities"))
    weights = normalize_weights(raw_weights, option_ids)

    selected = str(payload.get("selected_option_id", ""))
    if selected not in weights:
        selected = max(option_ids, key=lambda option_id: weights[option_id])

    rationale = payload.get("rationale", "")
    if not isinstance(rationale, str):
        rationale = str(rationale)
    return selected, weights, rationale.strip()
