import argparse

import pytest

from gemma_jev.benchmarking import request_fingerprint
from gemma_jev.model_assets import load_model_spec
from gemma_jev.models import DecisionOption, DecisionRequest
from scripts import benchmark
from scripts.benchmark import Target, parse_target


def test_parse_target_records_declared_steps() -> None:
    assert parse_target("steps8,http://127.0.0.1:8008,8") == Target(
        "steps8",
        "http://127.0.0.1:8008",
        8,
    )


@pytest.mark.parametrize(
    "value",
    [
        "label-only",
        ",http://127.0.0.1:8000",
        "label,",
        "label,http://127.0.0.1:8000,0",
        "label,http://127.0.0.1:8000,-1",
        "label,http://127.0.0.1:8000,not-an-int",
    ],
)
def test_parse_target_rejects_invalid_values(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_target(value)


def test_build_report_preserves_provenance_and_raw_trials(monkeypatch) -> None:
    model_spec = load_model_spec()
    request = DecisionRequest(
        context="choose",
        criteria=("latency",),
        options=(
            DecisionOption("A", "alpha"),
            DecisionOption("B", "beta"),
        ),
    )

    class FakeVLLMClient:
        def __init__(self, *, base_url, model, api_key, timeout_s, max_tokens):
            self.model = model

        def status(self):
            return {
                "reachable": True,
                "configured_model": self.model,
                "served_models": [self.model],
                "model_available": True,
                "error": None,
            }

        def complete(self, messages):
            assert messages
            return '{"selected_option_id":"A","weights":{"A":3,"B":1},"rationale":"synthetic"}'

    monkeypatch.setattr(benchmark, "VLLMClient", FakeVLLMClient)

    report = benchmark.build_report(
        request=request,
        model=model_spec.repo_id,
        warmup=1,
        trials=2,
        targets=[Target("synthetic", "http://127.0.0.1:8000", 8)],
        api_key=None,
        timeout_s=5.0,
        max_tokens=64,
        skip_model_check=False,
    )

    assert report["schema_version"] == 1
    assert report["manifest_model"] == {
        "repo_id": model_spec.repo_id,
        "revision": model_spec.revision,
    }
    assert report["request"]["sha256"] == request_fingerprint(request)
    assert report["trials"] == 2
    target = report["targets"][0]
    assert target["declared_denoising_steps"] == 8
    assert target["declared_denoising_steps_verified"] is False
    assert len(target["raw_trials"]) == 2
    assert target["summary"]["selection_counts"] == {"A": 2, "B": 0}
