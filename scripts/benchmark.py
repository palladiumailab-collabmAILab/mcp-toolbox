from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from gemma_jev import DecisionEngine, DecisionRequest, VLLMClient


@dataclass(frozen=True)
class Target:
    label: str
    base_url: str
    denoising_steps: int | None = None


def parse_target(value: str) -> Target:
    parts = value.split(",")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError("target must be LABEL,BASE_URL[,DENOISING_STEPS]")
    steps = int(parts[2]) if len(parts) == 3 else None
    return Target(parts[0], parts[1], steps)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark one or more separately launched DiffusionGemma/vLLM servers"
    )
    parser.add_argument("input", help="Decision JSON file")
    parser.add_argument("--target", action="append", type=parse_target, required=True)
    parser.add_argument("--model", default="google/diffusiongemma-26B-A4B-it")
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=1)
    args = parser.parse_args()

    request = DecisionRequest.from_dict(json.loads(Path(args.input).read_text(encoding="utf-8")))
    reports = []
    for target in args.target:
        engine = DecisionEngine(VLLMClient(base_url=target.base_url, model=args.model))
        for _ in range(args.warmup):
            engine.decide(request)

        results = [engine.decide(request) for _ in range(args.trials)]
        latencies = [result.latency_ms for result in results]
        selections = Counter(result.selected_option_id for result in results)
        modal_id, modal_count = selections.most_common(1)[0]
        reports.append(
            {
                "label": target.label,
                "base_url": target.base_url,
                "denoising_steps": target.denoising_steps,
                "trials": args.trials,
                "latency_ms": {
                    "mean": statistics.fmean(latencies),
                    "median": statistics.median(latencies),
                    "min": min(latencies),
                    "max": max(latencies),
                },
                "selection_agreement": modal_count / args.trials,
                "modal_selection": modal_id,
                "selection_counts": dict(selections),
            }
        )

    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
