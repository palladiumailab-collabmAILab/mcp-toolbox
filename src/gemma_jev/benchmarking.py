from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from typing import Any, Sequence

from .models import DecisionRequest, DecisionResult

REPORT_SCHEMA_VERSION = 1


def canonical_request_payload(request: DecisionRequest) -> dict[str, Any]:
    return {
        "context": request.context,
        "criteria": list(request.criteria),
        "options": [{"id": option.id, "text": option.text} for option in request.options],
        "image_urls": list(request.image_urls),
    }


def request_fingerprint(request: DecisionRequest) -> str:
    encoded = json.dumps(
        canonical_request_payload(request),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def serialize_trial(result: DecisionResult) -> dict[str, Any]:
    return {
        "selected_option_id": result.selected_option_id,
        "weights": dict(result.weights),
        "latency_ms": result.latency_ms,
    }


def summarize_results(
    results: Sequence[DecisionResult],
    option_ids: tuple[str, ...],
) -> dict[str, Any]:
    if not results:
        raise ValueError("at least one benchmark result is required")

    latencies = [result.latency_ms for result in results]
    selections = Counter(result.selected_option_id for result in results)
    modal_selection = max(
        option_ids,
        key=lambda option_id: (selections[option_id], -option_ids.index(option_id)),
    )
    modal_count = selections[modal_selection]

    weight_stats: dict[str, dict[str, float]] = {}
    for option_id in option_ids:
        weights = [result.weights[option_id] for result in results]
        weight_stats[option_id] = {
            "mean": statistics.fmean(weights),
            "stdev": statistics.pstdev(weights),
            "min": min(weights),
            "max": max(weights),
        }

    return {
        "latency_ms": {
            "mean": statistics.fmean(latencies),
            "median": statistics.median(latencies),
            "min": min(latencies),
            "max": max(latencies),
        },
        "selection_agreement": modal_count / len(results),
        "modal_selection": modal_selection,
        "selection_counts": {option_id: selections[option_id] for option_id in option_ids},
        "weight_stats": weight_stats,
    }


def validate_server_status(
    status: dict[str, Any],
    *,
    configured_model: str,
    skip_model_check: bool,
) -> None:
    if skip_model_check:
        return
    if not status.get("reachable"):
        raise RuntimeError("vLLM endpoint is not reachable")
    served_models = status.get("served_models")
    if not isinstance(served_models, list) or configured_model not in served_models:
        raise RuntimeError(
            f"configured model {configured_model!r} is not reported by the vLLM /v1/models endpoint"
        )
