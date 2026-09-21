from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gemma_jev.benchmarking import (
    REPORT_SCHEMA_VERSION,
    canonical_request_payload,
    request_fingerprint,
    serialize_trial,
    summarize_results,
    validate_server_status,
)
from gemma_jev.client import VLLMClient
from gemma_jev.engine import DecisionEngine
from gemma_jev.media_policy import MediaPolicy
from gemma_jev.model_assets import load_model_spec
from gemma_jev.models import DecisionRequest


@dataclass(frozen=True, slots=True)
class Target:
    label: str
    base_url: str
    declared_denoising_steps: int | None = None


def parse_target(value: str) -> Target:
    parts = value.split(",")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError("target must be LABEL,BASE_URL[,DECLARED_DENOISING_STEPS]")

    label = parts[0].strip()
    base_url = parts[1].strip()
    if not label or not base_url:
        raise argparse.ArgumentTypeError("target label and base URL must be non-empty")

    steps = None
    if len(parts) == 3:
        try:
            steps = int(parts[2])
        except ValueError as exc:
            raise argparse.ArgumentTypeError("declared denoising steps must be an integer") from exc
        if steps <= 0:
            raise argparse.ArgumentTypeError("declared denoising steps must be positive")

    return Target(label, base_url, steps)


def build_report(
    *,
    request: DecisionRequest,
    model: str,
    warmup: int,
    trials: int,
    targets: list[Target],
    api_key: str | None,
    timeout_s: float,
    max_tokens: int,
    skip_model_check: bool,
) -> dict[str, Any]:
    model_spec = load_model_spec()
    option_ids = tuple(option.id for option in request.options)
    target_reports = []

    for target in targets:
        client = VLLMClient(
            base_url=target.base_url,
            model=model,
            api_key=api_key,
            timeout_s=timeout_s,
            max_tokens=max_tokens,
        )
        status = client.status()
        validate_server_status(
            status,
            configured_model=model,
            skip_model_check=skip_model_check,
        )
        engine = DecisionEngine(client, media_policy=MediaPolicy.from_env())

        for _ in range(warmup):
            engine.decide(request)

        results = [engine.decide(request) for _ in range(trials)]
        target_reports.append(
            {
                "label": target.label,
                "base_url": target.base_url,
                "declared_denoising_steps": target.declared_denoising_steps,
                "declared_denoising_steps_verified": False,
                "server_status": status,
                "raw_trials": [serialize_trial(result) for result in results],
                "summary": summarize_results(results, option_ids),
            }
        )

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_model": {
            "repo_id": model_spec.repo_id,
            "revision": model_spec.revision,
        },
        "configured_model": model,
        "request": {
            "sha256": request_fingerprint(request),
            "payload": canonical_request_payload(request),
        },
        "warmup": warmup,
        "trials": trials,
        "targets": target_reports,
    }


def main() -> None:
    model_spec = load_model_spec()
    parser = argparse.ArgumentParser(
        description="Benchmark separately launched DiffusionGemma/vLLM servers"
    )
    parser.add_argument("input", help="Decision JSON file")
    parser.add_argument("--target", action="append", type=parse_target, required=True)
    parser.add_argument("--model", default=model_spec.repo_id)
    parser.add_argument("--api-key", default=os.getenv("VLLM_API_KEY"))
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument(
        "--skip-model-check",
        action="store_true",
        help="benchmark even when /v1/models does not report the configured model",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.trials <= 0:
        parser.error("--trials must be positive")
    if args.warmup < 0:
        parser.error("--warmup must be non-negative")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.max_tokens <= 0:
        parser.error("--max-tokens must be positive")

    request = DecisionRequest.from_dict(json.loads(Path(args.input).read_text(encoding="utf-8")))
    report = build_report(
        request=request,
        model=args.model,
        warmup=args.warmup,
        trials=args.trials,
        targets=args.target,
        api_key=args.api_key,
        timeout_s=args.timeout,
        max_tokens=args.max_tokens,
        skip_model_check=args.skip_model_check,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
