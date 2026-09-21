from pathlib import Path
from zipfile import ZipFile

from scripts.check_wheel import wheel_contains_manifest


def test_wheel_manifest_checker(tmp_path: Path) -> None:
    wheel = tmp_path / "package.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("gemma_jev/model_manifest.json", "{}")
        archive.writestr("gemma_jev/vllm_compatibility.json", "{}")

    assert wheel_contains_manifest(tmp_path) is True


def test_wheel_manifest_checker_detects_missing_manifest(tmp_path: Path) -> None:
    wheel = tmp_path / "package.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("gemma_jev/__init__.py", "")

    assert wheel_contains_manifest(tmp_path) is False
