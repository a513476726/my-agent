from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from agent_core import (
    CodeMatch,
    DomainValidationError,
    ForbiddenError,
    GitCommit,
    NotFoundError,
    Project,
    UnavailableError,
    VcsType,
)

_SKIPPED_DIRECTORIES = {
    ".git",
    ".hg",
    ".idea",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}
_GIT_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@{}~^:-]*$")


class LocalCodeAccess:
    """只读、限定在项目根目录内的代码访问实现。"""

    def __init__(self, *, git_timeout_seconds: float = 20.0) -> None:
        self._git_timeout_seconds = git_timeout_seconds

    def read_file(self, project: Project, relative_path: str, *, max_bytes: int = 256_000) -> str:
        if max_bytes <= 0:
            raise DomainValidationError("max_bytes 必须大于 0")
        path = self._resolve_project_path(project, relative_path)
        if not path.is_file():
            raise NotFoundError(f"文件不存在: {relative_path}")
        size = path.stat().st_size
        if size > max_bytes:
            raise DomainValidationError(f"文件大小 {size} 字节超过上限 {max_bytes} 字节")
        content = path.read_bytes()
        if len(content) > max_bytes:
            raise DomainValidationError(f"文件内容超过上限 {max_bytes} 字节")
        if b"\x00" in content:
            raise DomainValidationError("不支持读取二进制文件")
        return content.decode("utf-8", errors="replace")

    def search(
        self, project: Project, query: str, *, max_results: int = 50
    ) -> tuple[CodeMatch, ...]:
        normalized_query = query.strip()
        if not normalized_query:
            raise DomainValidationError("搜索关键词不能为空")
        if not 1 <= max_results <= 500:
            raise DomainValidationError("max_results 必须在 1 到 500 之间")

        root = self._project_root(project)
        matches: list[CodeMatch] = []
        lowered = normalized_query.lower()

        for current_root, directory_names, file_names in os.walk(root, followlinks=False):
            directory_names[:] = sorted(
                name
                for name in directory_names
                if name not in _SKIPPED_DIRECTORIES and not (Path(current_root) / name).is_symlink()
            )
            for file_name in sorted(file_names):
                path = Path(current_root) / file_name
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    if path.stat().st_size > 1_000_000:
                        continue
                    content = path.read_bytes()
                except OSError:
                    continue
                if b"\x00" in content[:8192]:
                    continue
                text = content.decode("utf-8", errors="replace")
                relative = path.relative_to(root).as_posix()
                for line_number, line in enumerate(text.splitlines(), start=1):
                    if lowered not in line.lower():
                        continue
                    matches.append(
                        CodeMatch(
                            path=relative,
                            line=line_number,
                            snippet=line.strip()[:500] or "(空行)",
                        )
                    )
                    if len(matches) >= max_results:
                        return tuple(matches)
        return tuple(matches)

    def git_log(
        self,
        project: Project,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> tuple[GitCommit, ...]:
        if not 1 <= limit <= 1000:
            raise DomainValidationError("limit 必须在 1 到 1000 之间")
        for label, value in (("since", since), ("until", until)):
            if value is not None and value.tzinfo is None:
                raise DomainValidationError(f"{label} 必须是带时区的时间")
        if since is not None and until is not None and until <= since:
            raise DomainValidationError("until 必须晚于 since")

        root = self._git_root(project)
        args = [
            "git",
            "-C",
            str(root),
            "log",
            f"--max-count={limit}",
            "--pretty=format:%H%x1f%an%x1f%aI%x1f%s%x1e",
        ]
        if since is not None:
            args.append(f"--since={since.isoformat()}")
        if until is not None:
            args.append(f"--until={until.isoformat()}")
        output = self._run_git(args, root)

        commits: list[GitCommit] = []
        for record in output.split("\x1e"):
            record = record.strip()
            if not record:
                continue
            parts = record.split("\x1f", maxsplit=3)
            if len(parts) != 4:
                continue
            sha, author, committed_at, message = parts
            commits.append(
                GitCommit(
                    sha=sha,
                    author=author or "unknown",
                    committed_at=datetime.fromisoformat(committed_at),
                    message=message or "(无提交说明)",
                )
            )
        return tuple(commits)

    def git_diff(self, project: Project, *, base: str, head: str, max_bytes: int = 256_000) -> str:
        if max_bytes <= 0:
            raise DomainValidationError("max_bytes 必须大于 0")
        for label, value in (("base", base), ("head", head)):
            if not _GIT_REF_PATTERN.fullmatch(value):
                raise DomainValidationError(f"{label} 不是有效的 Git 引用")
        root = self._git_root(project)
        output = self._run_git(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--no-ext-diff",
                "--unified=3",
                base,
                head,
                "--",
            ],
            root,
        )
        encoded = output.encode("utf-8")
        if len(encoded) <= max_bytes:
            return output
        truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
        return f"{truncated}\n\n[diff 已截断，超过 {max_bytes} 字节]"

    def _project_root(self, project: Project) -> Path:
        root = Path(project.path)
        if not root.is_absolute():
            raise DomainValidationError("项目路径必须是绝对路径")
        resolved = root.resolve()
        if not resolved.is_dir():
            raise NotFoundError(f"项目目录不存在: {project.path}")
        return resolved

    def _resolve_project_path(self, project: Project, relative_path: str) -> Path:
        value = relative_path.strip()
        if not value:
            raise DomainValidationError("路径不能为空")
        relative = Path(value)
        if relative.is_absolute():
            raise ForbiddenError("不允许访问项目根目录之外的绝对路径")
        root = self._project_root(project)
        resolved = (root / relative).resolve(strict=False)
        if resolved == root or not resolved.is_relative_to(root):
            raise ForbiddenError("访问路径超出项目根目录")
        return resolved

    def _git_root(self, project: Project) -> Path:
        if project.vcs_type is not VcsType.GIT:
            raise DomainValidationError("项目未登记为 Git 仓库")
        return self._project_root(project)

    def _run_git(self, args: list[str], root: Path) -> str:
        try:
            result = subprocess.run(
                args,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=self._git_timeout_seconds,
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
