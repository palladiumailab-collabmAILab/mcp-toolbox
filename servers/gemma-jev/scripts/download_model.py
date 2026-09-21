from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from gemma_jev.model_assets import ModelSpec, load_model_spec, resolve_local_model_dir


def materialize_model(
    spec: ModelSpec,
    *,
    local_dir: Path,
    downloader: Callable[..., str] | None = None,
) -> str:
    if downloader is None:
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise RuntimeError(
                'model download support is not installed; run: python -m pip install -e ".[model]"'
            ) from exc
        downloader = snapshot_download

    local_dir.mkdir(parents=True, exist_ok=True)
    return downloader(
        repo_id=spec.repo_id,
        revision=spec.revision,
        local_dir=str(local_dir),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the revision-pinned DiffusionGemma model assets"
    )
    parser.add_argument("--local-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    spec = load_model_spec()
    local_dir = resolve_local_model_dir(spec, override=args.local_dir)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "repo_id": spec.repo_id,
                    "revision": spec.revision,
                    "local_dir": str(local_dir),
                },
                indent=2,
            )
        )
        return

    path = materialize_model(spec, local_dir=local_dir)
    print(path)


if __name__ == "__main__":
    main()
