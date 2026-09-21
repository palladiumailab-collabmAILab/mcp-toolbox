from __future__ import annotations

import zipfile
from pathlib import Path

REQUIRED_MEMBER_SUFFIXES = (
    "gemma_jev/model_manifest.json",
    "gemma_jev/vllm_compatibility.json",
)


def wheel_contains_manifest(dist_dir: Path = Path("dist")) -> bool:
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("no wheel found under dist/")

    wheel = wheels[-1]
    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
        return all(
            any(name.endswith(suffix) for name in members) for suffix in REQUIRED_MEMBER_SUFFIXES
        )


def main() -> None:
    if not wheel_contains_manifest():
        missing = ", ".join(REQUIRED_MEMBER_SUFFIXES)
        raise SystemExit(f"built wheel is missing one of: {missing}")


if __name__ == "__main__":
    main()
