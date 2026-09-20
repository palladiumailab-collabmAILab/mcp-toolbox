from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from pathlib import Path
from typing import Mapping

from .media_policy import MediaPolicy
from .model_assets import ModelSpec, load_model_spec, resolve_local_model_dir

DENY_REMOTE_MEDIA_DOMAIN = "invalid.invalid"
_PROTECTED_MEDIA_ARGS = (
    "--allowed-media-domains",
    "--allowed-local-media-path",
)


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

    raise SystemExit(
        subprocess.run(
            command,
            check=False,
            env=build_vllm_environment(),
        ).returncode
    )


if __name__ == "__main__":
    main()
