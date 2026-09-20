from pathlib import Path

import pytest

from gemma_jev.model_assets import load_model_spec
from gemma_jev.serve import build_vllm_command


def test_remote_command_pins_revision_and_served_name() -> None:
    spec = load_model_spec()
    command = build_vllm_command(spec, local=False, host="127.0.0.1", port=8010)

    assert command[:3] == ["vllm", "serve", spec.repo_id]
    assert command[command.index("--revision") + 1] == spec.revision
    assert command[command.index("--served-model-name") + 1] == spec.repo_id
    assert command[command.index("--port") + 1] == "8010"


def test_local_command_keeps_stable_api_model_name(tmp_path: Path) -> None:
    spec = load_model_spec()
    local_dir = tmp_path / "checkpoint"
    local_dir.mkdir()

    command = build_vllm_command(spec, local=True, local_dir=local_dir)

    assert command[:3] == ["vllm", "serve", str(local_dir)]
    assert "--revision" not in command
    assert command[command.index("--served-model-name") + 1] == spec.repo_id


def test_local_command_requires_downloaded_directory(tmp_path: Path) -> None:
    spec = load_model_spec()

    with pytest.raises(FileNotFoundError):
        build_vllm_command(spec, local=True, local_dir=tmp_path / "missing")
