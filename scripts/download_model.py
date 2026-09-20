from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "models" / "manifest.json"


@dataclass(frozen=True, slots=True)
class DownloadSpec:
    repo_id: str
    revision: str
    local_dir: Path


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_download_spec(
    manifest: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    local_dir_override: Path | None = None,
) -> DownloadSpec:
    source = manifest["source"]
    local_dir = local_dir_override or (repo_root / manifest["local_dir"])
    return DownloadSpec(
        repo_id=str(source["repo_id"]),
        revision=str(source["revision"]),
        local_dir=local_dir,
    )


def materialize_model(
    spec: DownloadSpec,
    *,
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

    spec.local_dir.mkdir(parents=True, exist_ok=True)
    return downloader(
        repo_id=spec.repo_id,
        revision=spec.revision,
        local_dir=str(spec.local_dir),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the revision-pinned DiffusionGemma model assets"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--local-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    spec = resolve_download_spec(
        manifest,
        local_dir_override=args.local_dir,
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "repo_id": spec.repo_id,
                    "revision": spec.revision,
                    "local_dir": str(spec.local_dir),
                },
                indent=2,
            )
        )
        return

    path = materialize_model(spec)
    print(path)


if __name__ == "__main__":
    main()
