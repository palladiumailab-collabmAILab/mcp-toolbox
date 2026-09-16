import subprocess
from pathlib import Path
from typing import Any

import pytest

from qwen_mcp.repo_tools import RepoContext, RepoToolError


def test_read_and_search_are_scoped(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "demo.py").write_text("alpha\nbeta\n", encoding="utf-8")
    repo = RepoContext.create(str(tmp_path))

    assert "src/demo.py" in repo.list_files()
    assert "src/demo.py:2: beta" in repo.search_text("beta")
    assert repo.read_file("src/demo.py", start_line=2, end_line=2) == "2: beta"


def test_search_falls_back_without_rg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "demo.py").write_text("needle\n", encoding="utf-8")
    monkeypatch.setattr("qwen_mcp.repo_tools.shutil.which", lambda _: None)
    repo = RepoContext.create(str(tmp_path))

    assert repo.search_text("needle") == "demo.py:1: needle"


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    repo = RepoContext.create(str(tmp_path))
    with pytest.raises(RepoToolError, match="escapes workspace"):
        repo.read_file("../outside.txt")


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")

    repo = RepoContext.create(str(tmp_path))
    with pytest.raises(RepoToolError, match="escapes workspace"):
        repo.read_file("link/secret.txt")


def test_sensitive_and_runtime_paths_are_not_visible(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("TOKEN=example\n", encoding="utf-8")
    repo = RepoContext.create(str(tmp_path))

    with pytest.raises(RepoToolError, match="excluded"):
        repo.read_file(".git/config")
    with pytest.raises(RepoToolError, match="excluded"):
        repo.read_file(".env")
    with pytest.raises(RepoToolError, match="excluded"):
        repo.read_file(".env.example")
    assert ".env" not in repo.list_files()
    assert ".env.example" not in repo.list_files()


def test_model_controlled_limits_have_hard_caps(tmp_path: Path) -> None:
    repo = RepoContext.create(str(tmp_path))

    with pytest.raises(RepoToolError, match="max_entries"):
        repo.list_files(max_entries=1001)
    with pytest.raises(RepoToolError, match="max_matches"):
        repo.search_text("x", max_matches=501)
    with pytest.raises(RepoToolError, match="query exceeds"):
        repo.search_text("x" * 513)


def test_git_inspection_disables_writes_and_external_filters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("qwen_mcp.repo_tools.subprocess.run", fake_run)
    repo = RepoContext.create(str(tmp_path))

    repo.git_status()
    repo.git_diff()

    status_args, status_kwargs = calls[0]
    diff_args, diff_kwargs = calls[1]
    for args, kwargs in ((status_args, status_kwargs), (diff_args, diff_kwargs)):
        assert "--no-optional-locks" in args
        assert "core.fsmonitor=false" in args
        assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"

    assert "--ignore-submodules=all" in status_args
    assert "--no-ext-diff" in diff_args
    assert "--no-textconv" in diff_args
    assert "--ignore-submodules=all" in diff_args
