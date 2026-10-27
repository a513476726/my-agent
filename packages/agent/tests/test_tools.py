from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from agentscope.message import ToolResultState

from agent_core import KnowledgeGateway, Project, RetrievalHit, VcsType
from agent_runtime.code_access import LocalCodeAccess
from agent_runtime.tools import ProjectToolbox, ToolContext


def _project(root: Path) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=uuid4(),
        name="项目 A",
        path=str(root),
        vcs_type=VcsType.GIT,
        created_at=now,
        updated_at=now,
    )


class FakeKnowledge:
    def __init__(self, hits: tuple[RetrievalHit, ...]) -> None:
        self.hits = hits
        self.calls = 0

    def retrieve(self, query: object) -> tuple[RetrievalHit, ...]:
        self.calls += 1
        return self.hits


def _text(chunk: object) -> str:
    return "\n".join(block.text for block in chunk.content if block.type == "text")  # type: ignore[attr-defined]


def test_search_knowledge_returns_citations(tmp_path: Path) -> None:
    document_id = uuid4()
    knowledge = FakeKnowledge(
        (
            RetrievalHit(
                document_id=document_id,
                title="需求说明",
                source_path="docs/requirement.md",
                heading_path=("登录", "流程"),
                snippet="用户先输入账号密码",
                score=0.92,
            ),
        )
    )
    toolbox = ProjectToolbox(
        ToolContext(
            project=_project(tmp_path),
            knowledge=cast(KnowledgeGateway, knowledge),
            code=LocalCodeAccess(),
        )
    )

    chunk = toolbox.search_knowledge("登录流程")

    assert chunk.state == ToolResultState.SUCCESS
    assert "需求说明" in _text(chunk)
    citations = chunk.metadata["citations"]
    assert citations[0]["document_id"] == str(document_id)
    assert citations[0]["heading_path"] == ["登录", "流程"]


def test_search_knowledge_reports_empty_result(tmp_path: Path) -> None:
    toolbox = ProjectToolbox(
        ToolContext(
            project=_project(tmp_path),
            knowledge=cast(KnowledgeGateway, FakeKnowledge(())),
            code=LocalCodeAccess(),
        )
    )

    chunk = toolbox.search_knowledge("不存在")

    assert chunk.metadata["matched"] is False
    assert "未命中" in _text(chunk)


def test_fs_read_and_search_are_scoped_to_project(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def handler():\n    return 1\n", encoding="utf-8")
    toolbox = ProjectToolbox(
        ToolContext(project=_project(tmp_path), knowledge=None, code=LocalCodeAccess())
    )

    read = toolbox.fs_read("src/app.py")
    search = toolbox.fs_search("handler")
    escaped = toolbox.fs_read("../outside.txt")

    assert "def handler" in _text(read)
    assert "src/app.py:1" in _text(search)
    assert escaped.state == ToolResultState.ERROR
    assert "超出项目根目录" in _text(escaped)


def test_git_tools_return_visible_results(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "测试用户"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "首次提交"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()
    (tmp_path / "a.txt").write_text("world\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "第二次提交"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    toolbox = ProjectToolbox(
        ToolContext(project=_project(tmp_path), knowledge=None, code=LocalCodeAccess())
    )
    log = toolbox.git_log(limit=2)
    diff = toolbox.git_diff(first, "HEAD")

    assert "第二次提交" in _text(log)
    assert "-hello" in _text(diff)
    assert "+world" in _text(diff)


def test_tools_reject_missing_project_without_touching_knowledge(tmp_path: Path) -> None:
    knowledge = FakeKnowledge(())
    toolbox = ProjectToolbox(
        ToolContext(
            project=None,
            knowledge=cast(KnowledgeGateway, knowledge),
            code=LocalCodeAccess(),
        )
    )

    results = (
        toolbox.search_knowledge("任意问题"),
        toolbox.fs_read("README.md"),
        toolbox.fs_search("任意"),
        toolbox.git_log(),
        toolbox.git_diff("main", "HEAD"),
    )

    assert all(item.state == ToolResultState.ERROR for item in results)
    assert all(item.metadata["error_code"] == "PROJECT_REQUIRED" for item in results)
    assert knowledge.calls == 0


def test_build_tools_exposes_five_named_tools(tmp_path: Path) -> None:
    toolbox = ProjectToolbox(
        ToolContext(project=_project(tmp_path), knowledge=None, code=LocalCodeAccess())
    )

    assert [tool.name for tool in toolbox.build_tools()] == [
        "search_knowledge",
        "fs_read",
        "fs_search",
        "git_log",
        "git_diff",
    ]
