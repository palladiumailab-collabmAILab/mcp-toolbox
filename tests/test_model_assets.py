from pathlib import Path

from gemma_jev.model_assets import load_model_manifest, load_model_spec, resolve_local_model_dir
from gemma_jev.runtime import DEFAULT_MODEL, DEFAULT_MODEL_REVISION
from scripts.download_model import materialize_model


def test_packaged_manifest_pins_upstream_revision() -> None:
    manifest = load_model_manifest()
    spec = load_model_spec()

    assert spec.repo_id == "google/diffusiongemma-26B-A4B-it"
    assert len(spec.revision) == 40
    assert spec.weight_shards == 11
    assert manifest["source"]["revision"] == spec.revision
    assert DEFAULT_MODEL == spec.repo_id
    assert DEFAULT_MODEL_REVISION == spec.revision


def test_local_cache_is_repository_relative(tmp_path: Path) -> None:
    spec = load_model_spec()
    local_dir = resolve_local_model_dir(spec, repo_root=tmp_path)

    assert local_dir == tmp_path / spec.local_dir
    assert spec.local_dir.parts[:2] == ("models", "cache")


def test_materialize_passes_pinned_coordinates_without_network(tmp_path: Path) -> None:
    spec = load_model_spec()
    local_dir = tmp_path / "model"
    calls = []

    def fake_download(**kwargs):
        calls.append(kwargs)
        return kwargs["local_dir"]

    result = materialize_model(spec, local_dir=local_dir, downloader=fake_download)

    assert result == str(local_dir)
    assert calls == [
        {
            "repo_id": spec.repo_id,
            "revision": spec.revision,
            "local_dir": str(local_dir),
        }
    ]
