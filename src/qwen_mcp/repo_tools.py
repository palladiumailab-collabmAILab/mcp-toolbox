from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_EXCLUDED_DIRS = {
    ".git",
    ".local",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    ".aws",
    ".azure",
    ".gnupg",
    ".kube",
    ".ssh",
    ".terraform.d",
    "build",
    "dist",
    "models",
    "node_modules",
    "venv",
}
_SENSITIVE_FILENAMES = {
    ".env",
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "token.json",
}
_SENSITIVE_SUFFIXES = (".key", ".pem", ".p12", ".pfx")
_MAX_FILE_BYTES = 2_000_000
_MAX_LIST_ENTRIES = 1_000
_MAX_SEARCH_MATCHES = 500
_MAX_QUERY_CHARS = 512


class RepoToolError(ValueError):
    pass


@dataclass(frozen=True)
class RepoContext:
    root: Path
    max_output_chars: int = 24_000

    @classmethod
    def create(
        cls,
        workspace: str,
        max_output_chars: int = 24_000,
        allowed_workspace_roots: Iterable[str | Path] = (),
    ) -> RepoContext:
        root = Path(workspace).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise RepoToolError(f"workspace is not a directory: {root}")
        allowed_roots = cls._resolve_allowed_roots(allowed_workspace_roots)
        if root not in allowed_roots:
            raise RepoToolError(
                "workspace is not allowlisted; configure QWEN_ALLOWED_WORKSPACE_ROOTS"
            )
        worktree_root = cls._git_worktree_root(root)
        if worktree_root != root:
            raise RepoToolError("workspace must be the top-level Git worktree root")
        return cls(root=root, max_output_chars=max_output_chars)

    @staticmethod
    def _resolve_allowed_roots(roots: Iterable[str | Path]) -> frozenset[Path]:
        resolved: set[Path] = set()
        for value in roots:
            candidate = Path(value).expanduser()
            try:
                candidate = candidate.resolve(strict=True)
            except OSError as exc:
                raise RepoToolError(f"allowed workspace root is invalid: {value}") from exc
            if not candidate.is_dir():
                raise RepoToolError(f"allowed workspace root is not a directory: {candidate}")
            resolved.add(candidate)
        if not resolved:
            raise RepoToolError(
                "no allowed workspace roots configured; set QWEN_ALLOWED_WORKSPACE_ROOTS"
            )
        return frozenset(resolved)

    @staticmethod
    def _git_worktree_root(path: Path) -> Path:
        env = os.environ.copy()
        env["GIT_OPTIONAL_LOCKS"] = "0"
        env["GIT_TERMINAL_PROMPT"] = "0"
        completed = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        if completed.returncode != 0:
            raise RepoToolError("workspace must be a Git worktree root")
        output = completed.stdout.strip()
        if not output:
            raise RepoToolError("workspace must be a Git worktree root")
        try:
            return Path(output).resolve(strict=True)
        except OSError as exc:
            raise RepoToolError("workspace must be a Git worktree root") from exc

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise RepoToolError("path escapes workspace")
        self._ensure_allowed(candidate)
        return candidate

    def _ensure_allowed(self, path: Path) -> None:
        relative = path.relative_to(self.root)
        lowered_parts = {part.lower() for part in relative.parts}
        if lowered_parts.intersection(_EXCLUDED_DIRS):
            raise RepoToolError("path is excluded from the local worker")
        if path.name and self._is_sensitive_filename(path.name):
            raise RepoToolError("path is excluded from the local worker")

    @staticmethod
    def _is_sensitive_filename(name: str) -> bool:
        lowered = name.lower()
        return (
            lowered in _SENSITIVE_FILENAMES
            or lowered.startswith(".env.")
            or lowered.endswith(_SENSITIVE_SUFFIXES)
        )

    @staticmethod
    def _git_exclude_pathspecs() -> list[str]:
        pathspecs: list[str] = []
        for name in sorted(_SENSITIVE_FILENAMES):
            pathspecs.extend(
                [
                    f":(exclude,glob){name}",
                    f":(exclude,glob)**/{name}",
                ]
            )
        pathspecs.extend(
            [
                ":(exclude,glob).env.*",
                ":(exclude,glob)**/.env.*",
            ]
        )
        for suffix in _SENSITIVE_SUFFIXES:
            pathspecs.extend(
                [
                    f":(exclude,glob)*{suffix}",
                    f":(exclude,glob)**/*{suffix}",
                ]
            )
        for directory in sorted(_EXCLUDED_DIRS):
            pathspecs.extend(
                [
                    f":(exclude,glob){directory}",
                    f":(exclude,glob){directory}/**",
                    f":(exclude,glob)**/{directory}",
                    f":(exclude,glob)**/{directory}/**",
                ]
            )
        return pathspecs

    def _git_pathspecs(self, path: str | None = None) -> list[str]:
        if path is None:
            include = "."
        else:
            resolved = self._resolve(path)
            include = str(resolved.relative_to(self.root))
        return [include, *self._git_exclude_pathspecs()]

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_output_chars:
            return text
        return text[: self.max_output_chars] + "\n...[truncated]"

    def list_files(self, path: str = ".", max_entries: int = 200) -> str:
        if not 1 <= max_entries <= _MAX_LIST_ENTRIES:
            raise RepoToolError(f"max_entries must be between 1 and {_MAX_LIST_ENTRIES}")
        start = self._resolve(path)
        if not start.exists():
            raise RepoToolError(f"path does not exist: {path}")
        if start.is_file():
            return str(start.relative_to(self.root))

        results: list[str] = []
        for current, dirs, files in os.walk(start):
            dirs[:] = sorted(d for d in dirs if d.lower() not in _EXCLUDED_DIRS)
            current_path = Path(current)
            for name in sorted(files):
                if self._is_sensitive_filename(name):
                    continue
                file_path = current_path / name
                resolved = file_path.resolve(strict=False)
                if not resolved.is_relative_to(self.root):
                    continue
                try:
                    self._ensure_allowed(resolved)
                except RepoToolError:
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
        if len(query) > _MAX_QUERY_CHARS:
            raise RepoToolError(f"query exceeds {_MAX_QUERY_CHARS} characters")
        if not 1 <= max_matches <= _MAX_SEARCH_MATCHES:
            raise RepoToolError(f"max_matches must be between 1 and {_MAX_SEARCH_MATCHES}")
        start = self._resolve(path)
        if not start.exists():
            raise RepoToolError(f"path does not exist: {path}")
        rg = shutil.which("rg")
        if rg is not None:
            return self._search_with_rg(rg, query, start, max_matches)
        return self._search_python(query, start, max_matches)

    def git_status(self) -> str:
        return self._git(
            [
                "status",
                "--short",
                "--branch",
                "--untracked-files=normal",
                "--ignore-submodules=all",
                "--",
                *self._git_pathspecs(),
            ]
        )

    def git_diff(self, staged: bool = False, path: str | None = None) -> str:
        args = [
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--ignore-submodules=all",
            "--relative",
        ]
        if staged:
            args.append("--cached")
        args.extend(["--", *self._git_pathspecs(path)])
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
            "--max-filesize",
            str(_MAX_FILE_BYTES),
            "--glob",
            "!.env",
            "--glob",
            "!.env.*",
            "--glob",
            "!.git-credentials",
            "--glob",
            "!.netrc",
            "--glob",
            "!.npmrc",
            "--glob",
            "!.pypirc",
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
            dirs[:] = sorted(d for d in dirs if d.lower() not in _EXCLUDED_DIRS)
            current_path = Path(current)
            for name in sorted(names):
                if self._is_sensitive_filename(name):
                    continue
                candidate = current_path / name
                resolved = candidate.resolve(strict=False)
                if not resolved.is_relative_to(self.root) or not candidate.is_file():
                    continue
                try:
                    self._ensure_allowed(resolved)
                except RepoToolError:
                    continue
                files.append(candidate)
        return files

    def _git(self, args: list[str]) -> str:
        env = os.environ.copy()
        env["GIT_OPTIONAL_LOCKS"] = "0"
        env["GIT_TERMINAL_PROMPT"] = "0"
        completed = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(self.root),
                *args,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        output = completed.stdout if completed.returncode == 0 else completed.stderr
        if completed.returncode != 0:
            raise RepoToolError(output.strip() or f"git exited {completed.returncode}")
        return self._truncate(output)
