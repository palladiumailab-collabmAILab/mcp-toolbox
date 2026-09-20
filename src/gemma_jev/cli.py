from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .models import DecisionRequest
from .runtime import DEFAULT_BASE_URL, DEFAULT_MAX_TOKENS, DEFAULT_MODEL, build_engine


def _load_json(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Jev-style decision on DiffusionGemma")
    parser.add_argument("input", help="Decision JSON file, or - for stdin")
    parser.add_argument("--base-url", default=os.getenv("VLLM_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.getenv("VLLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--api-key", default=os.getenv("VLLM_API_KEY"))
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    request = DecisionRequest.from_dict(_load_json(args.input))
    engine = build_engine(
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        max_tokens=args.max_tokens,
        timeout_s=args.timeout,
    )
    result = engine.decide(request)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
