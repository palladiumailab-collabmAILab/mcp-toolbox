import subprocess
from pathlib import Path

import pytest

from gemma_jev.model_assets import load_model_spec
from gemma_jev.serve import (
    DENY_REMOTE_MEDIA_DOMAIN,
    build_vllm_command,
    build_vllm_environment,
    check_vllm_runtime,
    load_vllm_compatibility,
)


def test_vllm_compatibility_manifest_is_pinned() -> None:
    compatibility = load_vllm_compatibility()

    assert compatibility.version == "0.29.0"
    assert compatibility.python_min == (3, 11)
    assert compatibility.python_max_exclusive == (3, 14)
    assert compatibility.cuda == "13.0"


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


def test_runtime_preflight_accepts_pinned_vllm_version() -> None:
    calls: list[list[str]] = []

    def fake_runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="vllm 0.29.0\n", stderr="")

    compatibility = check_vllm_runtime(runner=fake_runner, python_version=(3, 13))

    assert compatibility.version == "0.29.0"
    assert calls == [["vllm", "--version"]]


def test_runtime_preflight_reports_missing_vllm() -> None:
    def missing_runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(command[0])

    with pytest.raises(RuntimeError, match=r"\.\[serve\]"):
        check_vllm_runtime(runner=missing_runner, python_version=(3, 13))


def test_runtime_preflight_rejects_incompatible_vllm() -> None:
    def fake_runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="vllm 0.28.0\n", stderr="")

    with pytest.raises(RuntimeError, match=r"requires vLLM 0\.29\.0"):
        check_vllm_runtime(runner=fake_runner, python_version=(3, 13))


def test_runtime_preflight_rejects_unsupported_python() -> None:
    def unexpected_runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError(f"runner should not be called: {command}")

    with pytest.raises(RuntimeError, match=r"unsupported Python 3\.10"):
        check_vllm_runtime(runner=unexpected_runner, python_version=(3, 10))
