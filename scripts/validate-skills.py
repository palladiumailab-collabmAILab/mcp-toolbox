from __future__ import annotations

import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$", re.MULTILINE)
DESCRIPTION_RE = re.compile(r"^description:\s*.+$", re.MULTILINE)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for skill_file in sorted(root.glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            errors.append(f"{skill_file}: missing YAML frontmatter")
            continue
        if not NAME_RE.search(text):
            errors.append(f"{skill_file}: missing valid name")
        if not DESCRIPTION_RE.search(text):
            errors.append(f"{skill_file}: missing description")
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "skills")
    errors = validate(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
