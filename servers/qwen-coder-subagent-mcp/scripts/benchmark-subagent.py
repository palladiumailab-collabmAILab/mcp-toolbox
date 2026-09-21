from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qwen_mcp.agent import run_agent

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK = REPO_ROOT / "benchmarks" / "representative-task.txt"


def _git_output(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(workspace), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _load_throughput(path: Path, n_cpu_moe: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if int(payload["n_cpu_moe"]) != n_cpu_moe:
        raise ValueError("throughput benchmark n_cpu_moe does not match --n-cpu-moe")
    return payload


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    workspace = args.workspace.resolve()
    if _git_output(workspace, "status", "--porcelain"):
        raise RuntimeError("benchmark workspace must be clean so all candidates use one snapshot")

    commit = _git_output(workspace, "rev-parse", "HEAD")
    task = args.task_file.read_text(encoding="utf-8").strip()
    if not task:
        raise ValueError("representative task must not be empty")

    throughput = _load_throughput(args.throughput_json, args.n_cpu_moe)
    runs: list[dict[str, Any]] = []
    for run_number in range(1, args.repetitions + 1):
        started = time.perf_counter()
        result = await run_agent(task, str(workspace))
        elapsed = time.perf_counter() - started
        answer = str(result["answer"])
        runs.append(
            {
                "run": run_number,
                "latency_seconds": elapsed,
                "rounds": int(result["rounds"]),
                "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            }
        )

    latencies = [float(run["latency_seconds"]) for run in runs]
    rounds = [int(run["rounds"]) for run in runs]
    return {
        "schema_version": 1,
        "snapshot_commit": commit,
        "task_sha256": hashlib.sha256(task.encode("utf-8")).hexdigest(),
        "n_cpu_moe": args.n_cpu_moe,
        "repetitions": args.repetitions,
        "prompt_tokens_per_second": float(throughput["prompt_tokens_per_second"]),
        "generation_tokens_per_second": float(throughput["generation_tokens_per_second"]),
        "e2e_latency_seconds_mean": statistics.fmean(latencies),
        "e2e_latency_seconds_median": statistics.median(latencies),
        "rounds_mean": statistics.fmean(rounds),
        "runs": runs,
        "throughput_build_commit": str(throughput["build_commit"]),
        "throughput_build_number": int(throughput["build_number"]),
        "cpu_info": str(throughput["cpu_info"]),
        "gpu_info": str(throughput["gpu_info"]),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark a representative qwen_delegate workload"
    )
    parser.add_argument("--n-cpu-moe", type=int, required=True)
    parser.add_argument("--throughput-json", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=REPO_ROOT)
    parser.add_argument("--task-file", type=Path, default=DEFAULT_TASK)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repetitions < 3:
        parser.error("--repetitions must be at least 3")
    if args.output is None:
        args.output = REPO_ROOT / ".local" / f"qwen-subagent-{args.n_cpu_moe}.json"
    return args


def main() -> None:
    args = _parse_args()
    result = asyncio.run(_run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    args.output.write_text(output_text, encoding="utf-8")
    summary = (
        "n_cpu_moe={n} e2e_median={latency:.2f}s prompt={prompt:.2f}t/s "
        "generation={generation:.2f}t/s"
    )
    print(
        summary.format(
            n=result["n_cpu_moe"],
            latency=result["e2e_latency_seconds_median"],
            prompt=result["prompt_tokens_per_second"],
            generation=result["generation_tokens_per_second"],
        )
    )
    print(f"Saved benchmark to {args.output}")


if __name__ == "__main__":
    main()
