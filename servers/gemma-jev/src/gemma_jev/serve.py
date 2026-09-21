from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Callable, Mapping

from .media_policy import MediaPolicy
from .model_assets import ModelSpec, load_model_spec, resolve_local_model_dir

DENY_REMOTE_MEDIA_DOMAIN = "invalid.invalid"
_PROTECTED_MEDIA_ARGS = (
    "--allowed-media-domains",
    "--allowed-local-media-path",
)
VLLM_COMPATIBILITY_RESOURCE = "vllm_compatibility.json"
_VLLM_VERSION_PATTERN = re.compile(r"(?<![0-9])([0-9]+\.[0-9]+\.[0-9]+)(?![0-9])")


@dataclass(frozen=True, slots=True)
class VLLMCompatibility:
    version: str
    python_min: tuple[int, int]
    python_max_exclusive: tuple[int, int]
    cuda: str
    gpu_compute_capability_min: str


def _parse_python_version(value: Any, *, field: str) -> tuple[int, int]:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+\.[0-9]+", value):
        raise ValueError(f"vLLM compatibility {field} must be in MAJOR.MINOR form")
    major, minor = value.split(".")
    return int(major), int(minor)


def load_vllm_compatibility() -> VLLMCompatibility:
    resource = files("gemma_jev").joinpath(VLLM_COMPATIBILITY_RESOURCE)
    manifest = json.loads(resource.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("vLLM compatibility schema_version must be 1")
    python = manifest["python"]
    gpu = manifest["gpu"]
    version = str(manifest["vllm_version"]).strip()
    if not _VLLM_VERSION_PATTERN.fullmatch(version):
        raise ValueError("vLLM compatibility vllm_version must be a stable semantic version")
    return VLLMCompatibility(
        version=version,
        python_min=_parse_python_version(python["minimum"], field="python.minimum"),
        python_max_exclusive=_parse_python_version(
            python["maximum_exclusive"], field="python.maximum_exclusive"
        ),
        cuda=str(gpu["cuda"]),
        gpu_compute_capability_min=str(gpu["compute_capability_min"]),
    )


def check_vllm_runtime(
    executable: str = "vllm",
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    python_version: tuple[int, int] | None = None,
) -> VLLMCompatibility:
    compatibility = load_vllm_compatibility()
    current_python = python_version or sys.version_info[:2]
    if not (compatibility.python_min <= current_python < compatibility.python_max_exclusive):
        minimum = ".".join(str(part) for part in compatibility.python_min)
        maximum = ".".join(str(part) for part in compatibility.python_max_exclusive)
        raise RuntimeError(
            f"unsupported Python {current_python[0]}.{current_python[1]} for vLLM "
            f"{compatibility.version}; use Python >= {minimum}, < {maximum}"
        )

    try:
        result = runner(
            [executable, "--version"],
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"{executable!r} was not found; install the pinned runtime with "
            "python -m pip install -e '.[serve]'"
        ) from exc

    output = f"{result.stdout}\n{result.stderr}"
    match = _VLLM_VERSION_PATTERN.search(output)
    if result.returncode != 0 or match is None:
        raise RuntimeError(
            f"unable to verify vLLM with {executable} --version; "
            f"install vLLM {compatibility.version} from the serve extra"
        )
    detected = match.group(1)
    if detected != compatibility.version:
        raise RuntimeError(
            f"unsupported vLLM version {detected}; Gemma-Jev requires vLLM {compatibility.version}"
        )
    return compatibility


def _validate_extra_args(extra_args: list[str] | None) -> None:
    for argument in extra_args or []:
        if any(
            argument == protected or argument.startswith(protected + "=")
            for protected in _PROTECTED_MEDIA_ARGS
        ):
            raise ValueError(
                f"{argument.split('=', 1)[0]} is controlled by Gemma-Jev media policy "
                "and cannot be overridden through pass-through arguments"
            )


def build_vllm_command(
    spec: ModelSpec,
    *,
    local: bool,
    local_dir: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    allowed_media_domains: tuple[str, ...] = (),
    extra_args: list[str] | None = None,
) -> list[str]:
    _validate_extra_args(extra_args)

    if local:
        model_path = resolve_local_model_dir(spec, override=local_dir)
        if not model_path.exists():
            raise FileNotFoundError(
                f"local model directory does not exist: {model_path}; "
                "run scripts/download_model.py first"
            )
        model_arg = str(model_path)
    else:
        model_arg = spec.repo_id

    command = [
        "vllm",
        "serve",
        model_arg,
    ]
    if not local:
        command.extend(["--revision", spec.revision])

    domains = allowed_media_domains or (DENY_REMOTE_MEDIA_DOMAIN,)
    command.extend(
        [
            "--served-model-name",
            spec.repo_id,
            "--host",
            host,
            "--port",
            str(port),
            "--allowed-media-domains",
            *domains,
        ]
    )
    if extra_args:
        command.extend(extra_args)
    return command


def build_vllm_environment(base: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if base is None else base)
    environment.setdefault("VLLM_MEDIA_URL_ALLOW_REDIRECTS", "0")
    return environment


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch vLLM with the revision-pinned Gemma-Jev model configuration"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="serve the locally downloaded checkpoint instead of loading from Hugging Face",
    )
    parser.add_argument("--local-dir", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="print the resolved command without starting vLLM",
    )
    parser.add_argument(
        "--check-runtime",
        action="store_true",
        help="verify the installed vLLM and Python versions without starting the server",
    )
    args, extra_args = parser.parse_known_args()

    policy = MediaPolicy.from_env()
    command = build_vllm_command(
        load_model_spec(),
        local=args.local,
        local_dir=args.local_dir,
        host=args.host,
        port=args.port,
        allowed_media_domains=policy.allowed_domains,
        extra_args=extra_args,
    )

    if args.print_only:
        print(shlex.join(command))
        return

    try:
        compatibility = check_vllm_runtime()
    except RuntimeError as exc:
        raise SystemExit(f"Runtime preflight failed: {exc}") from None
    if args.check_runtime:
        print(
            f"vLLM {compatibility.version} preflight passed "
            f"(Python {sys.version_info[0]}.{sys.version_info[1]}, CUDA {compatibility.cuda})"
        )
        return

    raise SystemExit(
        subprocess.run(
            command,
            check=False,
            env=build_vllm_environment(),
        ).returncode
    )


if __name__ == "__main__":
    main()
