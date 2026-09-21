from gemma_jev.benchmarking import (
    request_fingerprint,
    serialize_trial,
    summarize_results,
    validate_server_status,
)
from gemma_jev.models import DecisionOption, DecisionRequest, DecisionResult


def make_request(
    *,
    options: tuple[DecisionOption, ...] | None = None,
) -> DecisionRequest:
    return DecisionRequest(
        context="choose",
        criteria=("latency", "stability"),
        options=options
        or (
            DecisionOption("A", "alpha"),
            DecisionOption("B", "beta"),
        ),
    )


def result(
    selected: str,
    a: float,
    b: float,
    latency_ms: float,
) -> DecisionResult:
    return DecisionResult(
        selected_option_id=selected,
        weights={"A": a, "B": b},
        rationale="unused",
        latency_ms=latency_ms,
        raw_text="unused",
    )


def test_request_fingerprint_is_deterministic() -> None:
    request = make_request()

    assert request_fingerprint(request) == request_fingerprint(request)
    assert len(request_fingerprint(request)) == 64


def test_request_fingerprint_changes_when_option_order_changes() -> None:
    first = make_request()
    second = make_request(
        options=(
            DecisionOption("B", "beta"),
            DecisionOption("A", "alpha"),
        )
    )

    assert request_fingerprint(first) != request_fingerprint(second)


def test_trial_serialization_excludes_raw_model_text_and_rationale() -> None:
    trial = serialize_trial(result("A", 0.75, 0.25, 10.0))

    assert trial == {
        "selected_option_id": "A",
        "weights": {"A": 0.75, "B": 0.25},
        "latency_ms": 10.0,
    }


def test_summary_preserves_latency_selection_and_weight_stability() -> None:
    summary = summarize_results(
        [
            result("A", 0.8, 0.2, 10.0),
            result("A", 0.6, 0.4, 20.0),
            result("B", 0.4, 0.6, 30.0),
        ],
        ("A", "B"),
    )

    assert summary["latency_ms"] == {
        "mean": 20.0,
        "median": 20.0,
        "min": 10.0,
        "max": 30.0,
    }
    assert summary["selection_agreement"] == 2 / 3
    assert summary["modal_selection"] == "A"
    assert summary["selection_counts"] == {"A": 2, "B": 1}
    assert summary["weight_stats"]["A"]["mean"] == 0.6
    assert summary["weight_stats"]["A"]["min"] == 0.4
    assert summary["weight_stats"]["A"]["max"] == 0.8
    assert summary["weight_stats"]["A"]["stdev"] > 0


def test_single_trial_weight_stdev_is_zero() -> None:
    summary = summarize_results(
        [result("A", 0.8, 0.2, 10.0)],
        ("A", "B"),
    )

    assert summary["weight_stats"]["A"]["stdev"] == 0.0
    assert summary["weight_stats"]["B"]["stdev"] == 0.0


def test_server_status_requires_reachable_matching_model() -> None:
    validate_server_status(
        {
            "reachable": True,
            "served_models": ["expected"],
        },
        configured_model="expected",
        skip_model_check=False,
    )


def test_server_status_rejects_unreachable_or_mismatched_model() -> None:
    for status in (
        {"reachable": False, "served_models": []},
        {"reachable": True, "served_models": ["other"]},
    ):
        try:
            validate_server_status(
                status,
                configured_model="expected",
                skip_model_check=False,
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("status should have been rejected")


def test_server_status_can_be_explicitly_bypassed() -> None:
    validate_server_status(
        {"reachable": False, "served_models": []},
        configured_model="expected",
        skip_model_check=True,
    )
