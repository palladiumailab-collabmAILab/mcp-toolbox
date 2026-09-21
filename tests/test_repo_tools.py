import subprocess
from pathlib import Path
from typing import Any

import pytest

from qwen_mcp.repo_tools import RepoContext, RepoToolError


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


@pytest.fixture
def git_workspace(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    return tmp_path


def test_read_and_search_are_scoped(git_workspace: Path) -> None:
    (git_workspace / "src").mkdir()
    (git_workspace / "src" / "demo.py").write_text("alpha\nbeta\n", encoding="utf-8")
    repo = RepoContext.create(str(git_workspace), allowed_workspace_roots=[git_workspace])

    assert "src/demo.py" in repo.list_files()
    assert "src/demo.py:2: beta" in repo.search_text("beta")
    assert repo.read_file("src/demo.py", start_line=2, end_line=2) == "2: beta"


def test_search_falls_back_without_rg(git_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (git_workspace / "demo.py").write_text("needle\n", encoding="utf-8")
    monkeypatch.setattr("qwen_mcp.repo_tools.shutil.which", lambda _: None)
    repo = RepoContext.create(str(git_workspace), allowed_workspace_roots=[git_workspace])

    assert repo.search_text("needle") == "demo.py:1: needle"


def test_path_escape_is_rejected(git_workspace: Path) -> None:
    repo = RepoContext.create(str(git_workspace), allowed_workspace_roots=[git_workspace])
    with pytest.raises(RepoToolError, match="escapes workspace"):
        repo.read_file("../outside.txt")


def test_symlink_escape_is_rejected(git_workspace: Path) -> None:
    outside = git_workspace.parent / f"{git_workspace.name}-outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = git_workspace / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")

    repo = RepoContext.create(str(git_workspace), allowed_workspace_roots=[git_workspace])
    with pytest.raises(RepoToolError, match="escapes workspace"):
        repo.read_file("link/secret.txt")


def test_sensitive_and_runtime_paths_are_not_visible(git_workspace: Path) -> None:
    (git_workspace / ".git" / "config").write_text("secret\n", encoding="utf-8")
    (git_workspace / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (git_workspace / ".env.example").write_text("TOKEN=example\n", encoding="utf-8")
    (git_workspace / ".aws").mkdir()
    (git_workspace / ".aws" / "credentials").write_text("secret\n", encoding="utf-8")
    (git_workspace / "private.pem").write_text("secret\n", encoding="utf-8")
    repo = RepoContext.create(str(git_workspace), allowed_workspace_roots=[git_workspace])

    with pytest.raises(RepoToolError, match="excluded"):
        repo.read_file(".git/config")
    with pytest.raises(RepoToolError, match="excluded"):
        repo.read_file(".env")
    with pytest.raises(RepoToolError, match="excluded"):
        repo.read_file(".env.example")
    with pytest.raises(RepoToolError, match="excluded"):
        repo.read_file(".aws/credentials")
    with pytest.raises(RepoToolError, match="excluded"):
        repo.read_file("private.pem")
    assert ".env" not in repo.list_files()
    assert ".env.example" not in repo.list_files()
    assert ".aws/credentials" not in repo.list_files()
    assert "private.pem" not in repo.list_files()


def test_model_controlled_limits_have_hard_caps(git_workspace: Path) -> None:
    repo = RepoContext.create(str(git_workspace), allowed_workspace_roots=[git_workspace])

    with pytest.raises(RepoToolError, match="max_entries"):
        repo.list_files(max_entries=1001)
    with pytest.raises(RepoToolError, match="max_matches"):
        repo.search_text("x", max_matches=501)
    with pytest.raises(RepoToolError, match="query exceeds"):
        repo.search_text("x" * 513)


def test_git_inspection_disables_writes_and_external_filters(
    git_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    repo = RepoContext.create(str(git_workspace), allowed_workspace_roots=[git_workspace])
    monkeypatch.setattr("qwen_mcp.repo_tools.subprocess.run", fake_run)

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
    assert "--relative" in diff_args


def test_git_inspection_stays_in_workspace_and_hides_sensitive_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace = repo_root
    runtime_dir = workspace / ".local"
    runtime_dir.mkdir(parents=True)

    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "test@example.invalid")
    _git(repo_root, "config", "user.name", "Test")

    visible = workspace / "visible.txt"
    sensitive = workspace / ".env"
    runtime = runtime_dir / "cache.txt"
    outside = tmp_path / "outside.txt"
    visible.write_text("visible before\n", encoding="utf-8")
    sensitive.write_text("TOKEN=before\n", encoding="utf-8")
    runtime.write_text("runtime before\n", encoding="utf-8")
    outside.write_text("outside before\n", encoding="utf-8")
    _git(repo_root, "add", "-f", ".")
    _git(repo_root, "commit", "-m", "initial")

    visible.write_text("visible after\n", encoding="utf-8")
    sensitive.write_text("TOKEN=after\n", encoding="utf-8")
    runtime.write_text("runtime after\n", encoding="utf-8")
    outside.write_text("outside after\n", encoding="utf-8")

    repo = RepoContext.create(str(workspace), allowed_workspace_roots=[workspace])
    status = repo.git_status()
    diff = repo.git_diff()

    assert "visible.txt" in status
    assert "outside.txt" not in status
    assert ".env" not in status
    assert ".local" not in status
    assert "visible after" in diff
    assert "outside after" not in diff
    assert "TOKEN=after" not in diff
    assert "runtime after" not in diff

    _git(repo_root, "add", "-f", ".")
    staged_diff = repo.git_diff(staged=True)
    assert "visible after" in staged_diff
    assert "outside after" not in staged_diff
    assert "TOKEN=after" not in staged_diff
    assert "runtime after" not in staged_diff


def test_workspace_requires_explicit_allowlist(tmp_path: Path) -> None:
    with pytest.raises(RepoToolError, match="no allowed workspace roots"):
        RepoContext.create(str(tmp_path))


def test_allowlisted_workspace_must_be_a_git_root(tmp_path: Path) -> None:
    with pytest.raises(RepoToolError, match="Git worktree"):
        RepoContext.create(str(tmp_path), allowed_workspace_roots=[tmp_path])


def test_sibling_repository_is_rejected(git_workspace: Path) -> None:
    sibling = git_workspace.parent / f"{git_workspace.name}-sibling"
    sibling.mkdir()
    _git(sibling, "init")
    with pytest.raises(RepoToolError, match="not allowlisted"):
        RepoContext.create(str(sibling), allowed_workspace_roots=[git_workspace])


def test_nested_workspace_is_rejected(git_workspace: Path) -> None:
    nested = git_workspace / "nested"
    nested.mkdir()
    with pytest.raises(RepoToolError, match="top-level Git worktree"):
        RepoContext.create(str(nested), allowed_workspace_roots=[nested])
