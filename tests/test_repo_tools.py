from pathlib import Path

import pytest

from qwen_mcp.repo_tools import RepoContext, RepoToolError


def test_read_and_search_are_scoped(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "demo.py").write_text("alpha\nbeta\n", encoding="utf-8")
    repo = RepoContext.create(str(tmp_path))

    assert "src/demo.py" in repo.list_files()
    assert "src/demo.py:2: beta" in repo.search_text("beta")
    assert repo.read_file("src/demo.py", start_line=2, end_line=2) == "2: beta"


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
