from __future__ import annotations

import zipfile
from pathlib import Path

REQUIRED_MEMBER_SUFFIX = "gemma_jev/model_manifest.json"


def wheel_contains_manifest(dist_dir: Path = Path("dist")) -> bool:
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("no wheel found under dist/")

    wheel = wheels[-1]
    with zipfile.ZipFile(wheel) as archive:
        return any(name.endswith(REQUIRED_MEMBER_SUFFIX) for name in archive.namelist())


def main() -> None:
    if not wheel_contains_manifest():
        raise SystemExit(f"built wheel is missing {REQUIRED_MEMBER_SUFFIX}")


if __name__ == "__main__":
    main()
