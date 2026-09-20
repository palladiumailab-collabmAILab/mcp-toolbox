from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def validation_commands(include_docker: bool) -> list[list[str]]:
    python = sys.executable
    commands = [
        [python, "-m", "pip", "check"],
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "ruff", "format", "--check", "."],
        [python, "-m", "pytest", "-q"],
        [python, "-m", "build"],
        [python, "scripts/check_wheel.py"],
    ]
    if include_docker:
        commands.append(["docker", "build", "-t", "gemma-jev:validation", "."])
    return commands


def run_validation(include_docker: bool) -> int:
    for command in validation_commands(include_docker):
        print("+", " ".join(command), file=sys.stderr, flush=True)
        result = subprocess.run(command, cwd=REPO_ROOT, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical Gemma-Jev validation gates")
    parser.add_argument(
        "--docker",
        action="store_true",
        help="also build the validation Docker image",
    )
    args = parser.parse_args()
    raise SystemExit(run_validation(include_docker=args.docker))


if __name__ == "__main__":
    main()
