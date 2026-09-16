from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
_MAX_FILE_BYTES = 2_000_000


class RepoToolError(ValueError):
    pass


@dataclass(frozen=True)
class RepoContext:
    root: Path
    max_output_chars: int = 24_000

    @classmethod
    def create(cls, workspace: str, max_output_chars: int = 24_000) -> RepoContext:
        root = Path(workspace).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise RepoToolError(f"workspace is not a directory: {root}")
        return cls(root=root, max_output_chars=max_output_chars)

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise RepoToolError("path escapes workspace")
        return candidate

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_output_chars:
            return text
        return text[: self.max_output_chars] + "\n...[truncated]"

    def list_files(self, path: str = ".", max_entries: int = 200) -> str:
        start = self._resolve(path)
        if not start.exists():
            raise RepoToolError(f"path does not exist: {path}")
        if start.is_file():
            return str(start.relative_to(self.root))

        results: list[str] = []
        for current, dirs, files in os.walk(start):
            dirs[:] = sorted(d for d in dirs if d not in _EXCLUDED_DIRS)
            current_path = Path(current)
            for name in sorted(files):
                file_path = current_path / name
                resolved = file_path.resolve(strict=False)
                if not resolved.is_relative_to(self.root):
                    continue
                results.append(str(file_path.relative_to(self.root)))
                if len(results) >= max_entries:
                    return self._truncate("\n".join(results) + "\n...[entry limit reached]")
        return self._truncate("\n".join(results))

    def read_file(
        self,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise RepoToolError(f"not a file: {path}")
        if target.stat().st_size > _MAX_FILE_BYTES:
            raise RepoToolError(f"file exceeds {_MAX_FILE_BYTES} bytes: {path}")
        if start_line < 1:
            raise RepoToolError("start_line must be >= 1")
        if end_line is not None and end_line < start_line:
            raise RepoToolError("end_line must be >= start_line")

        text = target.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        selected = lines[start_line - 1 : end_line]
        numbered = [f"{index}: {line}" for index, line in enumerate(selected, start=start_line)]
        return self._truncate("\n".join(numbered))

    def search_text(self, query: str, path: str = ".", max_matches: int = 100) -> str:
        if not query:
            raise RepoToolError("query must not be empty")
        if max_matches < 1:
            raise RepoToolError("max_matches must be >= 1")
        start = self._resolve(path)
        if not start.exists():
            raise RepoToolError(f"path does not exist: {path}")
        rg = shutil.which("rg")
        if rg is not None:
            return self._search_with_rg(rg, query, start, max_matches)
        return self._search_python(query, start, max_matches)

    def git_status(self) -> str:
        return self._git(["status", "--short", "--branch"])

    def git_diff(self, staged: bool = False, path: str | None = None) -> str:
        args = ["diff"]
        if staged:
            args.append("--cached")
        if path is not None:
            resolved = self._resolve(path)
            args.extend(["--", str(resolved.relative_to(self.root))])
        return self._git(args)

    def execute(self, tool: str, arguments: dict[str, Any]) -> str:
        if tool == "list_files":
            return self.list_files(
                path=str(arguments.get("path", ".")),
                max_entries=int(arguments.get("max_entries", 200)),
            )
        if tool == "read_file":
            end = arguments.get("end_line")
            return self.read_file(
                path=str(arguments["path"]),
                start_line=int(arguments.get("start_line", 1)),
                end_line=None if end is None else int(end),
            )
        if tool == "search_text":
            return self.search_text(
                query=str(arguments["query"]),
                path=str(arguments.get("path", ".")),
                max_matches=int(arguments.get("max_matches", 100)),
            )
        if tool == "git_status":
            return self.git_status()
        if tool == "git_diff":
            path = arguments.get("path")
            return self.git_diff(
                staged=bool(arguments.get("staged", False)),
                path=None if path is None else str(path),
            )
        raise RepoToolError(f"unsupported tool: {tool}")

    def _search_with_rg(self, rg: str, query: str, start: Path, max_matches: int) -> str:
        relative_start = str(start.relative_to(self.root)) if start != self.root else "."
        args = [
            rg,
            "--fixed-strings",
            "--line-number",
            "--no-heading",
            "--color",
            "never",
            "--hidden",
            "--no-ignore",
            "--max-filesize",
            str(_MAX_FILE_BYTES),
        ]
        for directory in sorted(_EXCLUDED_DIRS):
            args.extend(["--glob", f"!{directory}/**", "--glob", f"!**/{directory}/**"])
        args.extend(["--", query, relative_start])

        process = subprocess.Popen(
            args,
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        matches: list[str] = []
        assert process.stdout is not None
        try:
            for raw_line in process.stdout:
                line = raw_line.rstrip("\r\n")
                if not line:
                    continue
                parts = line.split(":", 2)
                if len(parts) == 3:
                    line = f"{parts[0]}:{parts[1]}: {parts[2]}"
                matches.append(line)
                if len(matches) >= max_matches:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)
                    return self._truncate("\n".join(matches) + "\n...[match limit reached]")
        finally:
            process.stdout.close()

        assert process.stderr is not None
        stderr = process.stderr.read().strip()
        process.stderr.close()
        return_code = process.wait(timeout=15)
        if return_code not in (0, 1):
            raise RepoToolError(stderr or f"rg exited {return_code}")
        return self._truncate("\n".join(matches))

    def _search_python(self, query: str, start: Path, max_matches: int) -> str:
        candidates = [start] if start.is_file() else self._iter_files(start)
        matches: list[str] = []
        for file_path in candidates:
            try:
                if file_path.stat().st_size > _MAX_FILE_BYTES:
                    continue
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeError):
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if query in line:
                    rel = file_path.relative_to(self.root)
                    matches.append(f"{rel}:{line_number}: {line}")
                    if len(matches) >= max_matches:
                        return self._truncate("\n".join(matches) + "\n...[match limit reached]")
        return self._truncate("\n".join(matches))

    def _iter_files(self, start: Path) -> list[Path]:
        files: list[Path] = []
        for current, dirs, names in os.walk(start):
            dirs[:] = sorted(d for d in dirs if d not in _EXCLUDED_DIRS)
            current_path = Path(current)
            for name in sorted(names):
                candidate = current_path / name
                resolved = candidate.resolve(strict=False)
                if resolved.is_relative_to(self.root) and candidate.is_file():
                    files.append(candidate)
        return files

    def _git(self, args: list[str]) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = completed.stdout if completed.returncode == 0 else completed.stderr
        if completed.returncode != 0:
            raise RepoToolError(output.strip() or f"git exited {completed.returncode}")
        return self._truncate(output)
