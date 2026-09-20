from pathlib import Path

import pytest

from gemma_jev.model_assets import load_model_spec
from gemma_jev.serve import (
    DENY_REMOTE_MEDIA_DOMAIN,
    build_vllm_command,
    build_vllm_environment,
)


def test_remote_command_pins_revision_and_served_name() -> None:
    spec = load_model_spec()
    command = build_vllm_command(spec, local=False, host="127.0.0.1", port=8010)

    assert command[:3] == ["vllm", "serve", spec.repo_id]
    assert command[command.index("--revision") + 1] == spec.revision
    assert command[command.index("--served-model-name") + 1] == spec.repo_id
    assert command[command.index("--port") + 1] == "8010"


def test_launcher_denies_remote_media_when_allowlist_is_empty() -> None:
    spec = load_model_spec()
    command = build_vllm_command(spec, local=False)
    index = command.index("--allowed-media-domains")

    assert command[index + 1 :] == [DENY_REMOTE_MEDIA_DOMAIN]


def test_launcher_passes_configured_media_domains() -> None:
    spec = load_model_spec()
    command = build_vllm_command(
        spec,
        local=False,
        allowed_media_domains=("images.example.com", "cdn.example.com"),
    )
    index = command.index("--allowed-media-domains")

    assert command[index + 1 :] == ["images.example.com", "cdn.example.com"]


@pytest.mark.parametrize(
    "argument",
    [
        "--allowed-media-domains",
        "--allowed-media-domains=evil.example",
        "--allowed-local-media-path",
        "--allowed-local-media-path=/",
    ],
)
def test_launcher_rejects_pass_through_media_policy_overrides(argument: str) -> None:
    spec = load_model_spec()

    with pytest.raises(ValueError, match="controlled by Gemma-Jev"):
        build_vllm_command(spec, local=False, extra_args=[argument])


def test_launcher_disables_media_redirects_by_default() -> None:
    assert build_vllm_environment({})["VLLM_MEDIA_URL_ALLOW_REDIRECTS"] == "0"
    assert (
        build_vllm_environment({"VLLM_MEDIA_URL_ALLOW_REDIRECTS": "1"})[
            "VLLM_MEDIA_URL_ALLOW_REDIRECTS"
        ]
        == "1"
    )


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
