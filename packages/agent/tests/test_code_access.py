from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_core import DomainValidationError, ForbiddenError, NotFoundError, Project, VcsType
from agent_runtime.code_access import LocalCodeAccess


def _project(root: Path, *, vcs_type: VcsType = VcsType.GIT) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=__import__("uuid").uuid4(),
        name="测试项目",
        path=str(root),
        vcs_type=vcs_type,
        created_at=now,
        updated_at=now,
    )


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_read_file_returns_utf8_content(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('你好')\n", encoding="utf-8")

    content = LocalCodeAccess().read_file(_project(tmp_path), "src/app.py")

    assert content == "print('你好')\n"


def test_read_file_rejects_absolute_and_parent_paths(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    project = _project(tmp_path)
    access = LocalCodeAccess()

    with pytest.raises(ForbiddenError):
        access.read_file(project, str(outside))
    with pytest.raises(ForbiddenError):
        access.read_file(project, "../outside.txt")


def test_read_file_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(outside)

    with pytest.raises(ForbiddenError):
        LocalCodeAccess().read_file(_project(tmp_path), "link.txt")


def test_read_file_enforces_size_limit_and_missing_file(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_text("x" * 20, encoding="utf-8")
    access = LocalCodeAccess()
    project = _project(tmp_path)

    with pytest.raises(DomainValidationError):
        access.read_file(project, "large.txt", max_bytes=10)
    with pytest.raises(NotFoundError):
        access.read_file(project, "missing.txt")


def test_search_skips_build_directories_and_returns_lines(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("needle = 1\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "secret.js").write_text("needle\n", encoding="utf-8")

    matches = LocalCodeAccess().search(_project(tmp_path), "NEEDLE")

    assert len(matches) == 1
    assert matches[0].path == "src/app.py"
    assert matches[0].line == 1
    assert matches[0].snippet == "needle = 1"


def test_git_log_and_diff_are_limited_to_repository(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "测试用户")
    (tmp_path / "README.md").write_text("first\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "first commit")
    first = _git(tmp_path, "rev-parse", "HEAD").strip()
    (tmp_path / "README.md").write_text("second\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "second commit")

    access = LocalCodeAccess()
    project = _project(tmp_path)
    commits = access.git_log(project, limit=2)
    diff = access.git_diff(project, base=first, head="HEAD")

    assert [item.message for item in commits] == ["second commit", "first commit"]
    assert "-first" in diff
    assert "+second" in diff


def test_git_operations_require_git_project(tmp_path: Path) -> None:
    project = _project(tmp_path, vcs_type=VcsType.NONE)

    with pytest.raises(DomainValidationError):
        LocalCodeAccess().git_log(project)
