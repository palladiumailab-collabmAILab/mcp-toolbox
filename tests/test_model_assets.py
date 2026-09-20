import json
from pathlib import Path

from scripts.download_model import materialize_model, resolve_download_spec


def manifest() -> dict:
    path = Path("models/manifest.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_pins_upstream_revision_and_ignored_cache() -> None:
    data = manifest()
    spec = resolve_download_spec(data)

    assert spec.repo_id == "google/diffusiongemma-26B-A4B-it"
    assert len(spec.revision) == 40
    assert data["weight_shards"] == 11
    assert Path(data["local_dir"]).parts[:2] == ("models", "cache")


def test_materialize_passes_pinned_coordinates_without_network(tmp_path: Path) -> None:
    data = manifest()
    spec = resolve_download_spec(data, local_dir_override=tmp_path / "model")
    calls = []

    def fake_download(**kwargs):
        calls.append(kwargs)
        return kwargs["local_dir"]

    result = materialize_model(spec, downloader=fake_download)

    assert result == str(spec.local_dir)
    assert calls == [
        {
            "repo_id": spec.repo_id,
            "revision": spec.revision,
            "local_dir": str(spec.local_dir),
        }
    ]
