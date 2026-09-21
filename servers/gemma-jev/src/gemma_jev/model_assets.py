from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

MANIFEST_RESOURCE = "model_manifest.json"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    repo_id: str
    revision: str
    license: str
    format: str
    approx_size_gb: float
    weight_shards: int
    local_dir: Path


def load_model_manifest() -> dict[str, Any]:
    resource = files("gemma_jev").joinpath(MANIFEST_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_model_spec() -> ModelSpec:
    manifest = load_model_manifest()
    source = manifest["source"]

    repo_id = str(source["repo_id"]).strip()
    revision = str(source["revision"]).strip()
    local_dir = Path(str(manifest["local_dir"]))

    if source.get("provider") != "huggingface":
        raise ValueError("model manifest provider must be huggingface")
    if not repo_id:
        raise ValueError("model manifest repo_id must be non-empty")
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision.lower()):
        raise ValueError("model manifest revision must be a 40-character git SHA")
    if local_dir.is_absolute():
        raise ValueError("model manifest local_dir must be repository-relative")

    return ModelSpec(
        name=str(manifest["name"]),
        repo_id=repo_id,
        revision=revision,
        license=str(manifest["license"]),
        format=str(manifest["format"]),
        approx_size_gb=float(manifest["approx_size_gb"]),
        weight_shards=int(manifest["weight_shards"]),
        local_dir=local_dir,
    )


def resolve_local_model_dir(
    spec: ModelSpec | None = None,
    *,
    repo_root: Path | None = None,
    override: Path | None = None,
) -> Path:
    if override is not None:
        return override
    resolved_spec = spec or load_model_spec()
    root = repo_root or Path.cwd()
    return root / resolved_spec.local_dir
