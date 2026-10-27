from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agent_core import (
    DomainValidationError,
    Project,
    ReportPeriod,
    UnavailableError,
    VcsType,
)

_TRADITIONAL_CATEGORY = re.compile(r"^([a-zA-Z]+)(?:\([^)]*\))?!?:\s*")
_CATEGORY_MAP = {
    "feat": "feature",
    "feature": "feature",
    "fix": "fix",
    "bugfix": "fix",
    "docs": "docs",
    "doc": "docs",
    "refactor": "refactor",
    "test": "test",
    "tests": "test",
    "perf": "performance",
    "chore": "chore",
    "build": "build",
    "ci": "ci",
    "style": "style",
}


@dataclass(frozen=True, slots=True)
class FileChange:
    path: str
    added: int | None
    deleted: int | None


@dataclass(frozen=True, slots=True)
class CommitChange:
    sha: str
    author: str
    committed_at: datetime
    message: str
    files: tuple[FileChange, ...]
    diff_excerpt: str

    @property
    def added(self) -> int:
        return sum(item.added or 0 for item in self.files)

    @property
    def deleted(self) -> int:
        return sum(item.deleted or 0 for item in self.files)


@dataclass(frozen=True, slots=True)
class ReportItemDraft:
    title: str
    summary: str
    category: str
    start_commit: str
    end_commit: str


@dataclass(frozen=True, slots=True)
class ReportDraft:
    title: str
    body: str
    items: tuple[ReportItemDraft, ...]


def collect_git_changes(
    project: Project,
    period: ReportPeriod,
    *,
    timeout_seconds: float = 30.0,
    max_commits: int = 100,
    max_diff_chars: int = 3000,
) -> tuple[CommitChange, ...]:
    if project.vcs_type is not VcsType.GIT:
        raise DomainValidationError("日报任务只支持 Git 项目")
    root = Path(project.path)
    if not root.is_absolute() or not root.is_dir():
        raise DomainValidationError(f"项目目录不存在: {project.path}")
    root = root.resolve()

    output = _run_git(
        [
            "git",
            "-C",
            str(root),
            "log",
            f"--max-count={max_commits}",
            f"--since={period.start.isoformat()}",
            f"--until={period.end.isoformat()}",
            "--pretty=format:%H%x1f%an%x1f%aI%x1f%s",
        ],
        root,
        timeout_seconds,
    )

    changes: list[CommitChange] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f", maxsplit=3)
        if len(parts) != 4:
            continue
        sha, author, committed_at, message = parts
        files = _collect_file_changes(root, sha, timeout_seconds)
        diff = _run_git(
            [
                "git",
                "-C",
                str(root),
                "show",
                "--no-ext-diff",
                "--unified=1",
                "--format=",
                sha,
                "--",
            ],
            root,
            timeout_seconds,
        )
        changes.append(
            CommitChange(
                sha=sha,
                author=author,
                committed_at=datetime.fromisoformat(committed_at),
                message=message or "(无提交说明)",
                files=tuple(files),
                diff_excerpt=_truncate(diff.strip(), max_diff_chars),
            )
        )
    return tuple(changes)


def _collect_file_changes(
    root: Path,
    sha: str,
    timeout_seconds: float,
) -> tuple[FileChange, ...]:
    output = _run_git(
        [
            "git",
            "-C",
            str(root),
            "show",
            "--no-ext-diff",
            "--numstat",
            "--format=",
            sha,
            "--",
        ],
        root,
        timeout_seconds,
    )
    files: list[FileChange] = []
    for line in output.splitlines():
        fields = line.split("\t", maxsplit=2)
        if len(fields) != 3:
            continue
        added, deleted, path = fields
        files.append(
            FileChange(
                path=path,
                added=int(added) if added.isdigit() else None,
                deleted=int(deleted) if deleted.isdigit() else None,
            )
        )
    return tuple(files)


def build_report_draft(
    project: Project,
    period: ReportPeriod,
    changes: tuple[CommitChange, ...],
) -> ReportDraft:
    title = f"{project.name} 日报 {period.label}"
    if not changes:
        body = f"# {title}\n\n统计周期：{period.label}\n\n统计周期内没有提交记录。\n"
        return ReportDraft(title=title, body=body, items=())

    total_added = sum(change.added for change in changes)
    total_deleted = sum(change.deleted for change in changes)
    lines = [
        f"# {title}",
        "",
        f"统计周期：{period.label}",
        f"提交数：{len(changes)}",
        f"文件变更：{sum(len(change.files) for change in changes)} 处",
        f"代码行：+{total_added} / -{total_deleted}",
        "",
        "## 变更明细",
    ]
    items: list[ReportItemDraft] = []
    for change in changes:
        category = _category(change)
        files = "、".join(item.path for item in change.files[:8])
        if len(change.files) > 8:
            files += f" 等 {len(change.files)} 个文件"
        summary = (
            f"类别：{category}\n"
            f"变更：{files or '无文件列表'}\n"
            f"代码行：+{change.added} / -{change.deleted}\n"
            f"提交：{change.sha[:12]} · {change.author} · "
            f"{change.committed_at.isoformat()}"
        )
        lines.extend(
            [
                "",
                f"### {change.message}",
                "",
                summary,
            ]
        )
        if change.diff_excerpt:
            lines.extend(["", "```diff", change.diff_excerpt, "```"])
        items.append(
            ReportItemDraft(
                title=change.message[:500],
                summary=summary
                + (f"\n\n关键差异：\n{change.diff_excerpt}" if change.diff_excerpt else ""),
                category=category,
                start_commit=change.sha,
                end_commit=change.sha,
            )
        )
    return ReportDraft(title=title, body="\n".join(lines).strip() + "\n", items=tuple(items))


def _category(change: CommitChange) -> str:
    match = _TRADITIONAL_CATEGORY.match(change.message)
    if match is not None:
        category = _CATEGORY_MAP.get(match.group(1).lower())
        if category is not None:
            return category
    paths = [item.path.lower() for item in change.files]
    if paths and all(path.endswith((".md", ".rst", ".txt")) for path in paths):
        return "docs"
    if paths and all(path.startswith(("tests/", "test/")) or "/test" in path for path in paths):
        return "test"
    return "change"


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "\n... [差异已截断]"


def _run_git(args: list[str], root: Path, timeout_seconds: float) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except FileNotFoundError as exc:
        raise UnavailableError("当前环境未安装 git") from exc
    except subprocess.TimeoutExpired as exc:
        raise UnavailableError("Git 命令执行超时") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise DomainValidationError(message or "Git 命令执行失败")
    return result.stdout
