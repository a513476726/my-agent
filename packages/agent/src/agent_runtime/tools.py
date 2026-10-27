from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from agentscope.message import TextBlock, ToolResultState
from agentscope.permission import PermissionBehavior, PermissionDecision
from agentscope.tool import FunctionTool, ToolChunk

from agent_core import (
    Citation,
    CodeAccess,
    DomainError,
    DomainValidationError,
    KnowledgeGateway,
    Project,
    RetrievalQuery,
)


@dataclass(frozen=True, slots=True)
class ToolContext:
    project: Project | None
    knowledge: KnowledgeGateway | None
    code: CodeAccess


def citation_from_hit_metadata(item: dict[str, object]) -> Citation:
    heading_path = item.get("heading_path") or []
    if not isinstance(heading_path, list):
        heading_path = []
    score = item.get("score")
    return Citation(
        document_id=item["document_id"],  # type: ignore[arg-type]
        document_title=str(item["document_title"]),
        heading_path=tuple(str(value) for value in heading_path),
        snippet=str(item["snippet"]),
        score=float(score) if score is not None else None,
        page=int(item["page"]) if item.get("page") is not None else None,
    )


class ProjectToolbox:
    """项目绑定的只读工具集合。模型无法通过参数改变项目边界。"""

    def __init__(self, context: ToolContext) -> None:
        self._context = context

    def build_tools(self) -> tuple[FunctionTool, ...]:
        permission = PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="平台内置只读工具，执行范围限定在当前项目。",
        )
        return tuple(
            FunctionTool(
                func=func,
                is_read_only=True,
                is_concurrency_safe=False,
                permission=permission,
            )
            for func in (
                self.search_knowledge,
                self.fs_read,
                self.fs_search,
                self.git_log,
                self.git_diff,
            )
        )

    def search_knowledge(self, query: str, top_k: int = 5) -> ToolChunk:
        """检索当前项目知识库，返回带文档标识与章节路径的可追溯片段。

        Args:
            query: 要检索的问题或关键词。
            top_k: 返回片段数量，范围 1 到 20。
        """
        try:
            project = self._require_project()
            knowledge = self._require_knowledge()
            if not 1 <= top_k <= 20:
                raise DomainValidationError("top_k 必须在 1 到 20 之间")
            hits = knowledge.retrieve(
                RetrievalQuery(project_id=project.id, text=query, top_k=top_k)
            )
            citations = [
                {
                    "document_id": str(hit.document_id),
                    "document_title": hit.title,
                    "heading_path": list(hit.heading_path),
                    "snippet": hit.snippet,
                    "score": hit.score,
                    "page": hit.page,
                    "source_path": hit.source_path,
                }
                for hit in hits
            ]
            if not hits:
                return _success("未命中任何知识库内容。", {"citations": [], "matched": False})
            lines = ["知识库检索结果："]
            for index, hit in enumerate(hits, start=1):
                heading = " / ".join(hit.heading_path) or "正文"
                lines.append(
                    f"{index}. {hit.title}（{hit.source_path}）\n"
                    f"   章节：{heading}\n"
                    f"   片段：{hit.snippet}\n"
                    f"   相关度：{hit.score:.4f}"
                )
            return _success("\n".join(lines), {"citations": citations, "matched": True})
        except Exception as exc:
            return _failure(exc)

    def fs_read(self, path: str, max_bytes: int = 256000) -> ToolChunk:
        """读取当前项目内的文本文件。

        Args:
            path: 相对于项目根目录的文件路径。
            max_bytes: 最大读取字节数。
        """
        try:
            project = self._require_project()
            content = self._context.code.read_file(project, path, max_bytes=max_bytes)
            return _success(
                content,
                {"path": path, "bytes": len(content.encode("utf-8"))},
            )
        except Exception as exc:
            return _failure(exc)

    def fs_search(self, query: str, max_results: int = 50) -> ToolChunk:
        """在当前项目内按文本内容搜索文件。

        Args:
            query: 要搜索的文本，不区分大小写。
            max_results: 最多返回的匹配行数。
        """
        try:
            project = self._require_project()
            matches = self._context.code.search(project, query, max_results=max_results)
            if not matches:
                return _success("未找到匹配内容。", {"matches": [], "matched": False})
            lines = ["搜索匹配："]
            for match in matches:
                lines.append(f"{match.path}:{match.line}: {match.snippet}")
            return _success(
                "\n".join(lines),
                {
                    "matched": True,
                    "matches": [
                        {"path": item.path, "line": item.line, "snippet": item.snippet}
                        for item in matches
                    ],
                },
            )
        except Exception as exc:
            return _failure(exc)

    def git_log(
        self,
        since: str | None = None,
        until: str | None = None,
        limit: int = 100,
    ) -> ToolChunk:
        """读取当前项目 Git 提交历史。

        Args:
            since: 起始时间，ISO 8601 格式，可省略。
            until: 结束时间，ISO 8601 格式，可省略。
            limit: 最多返回的提交数，范围 1 到 1000。
        """
        try:
            project = self._require_project()
            commits = self._context.code.git_log(
                project,
                since=_parse_datetime(since, "since"),
                until=_parse_datetime(until, "until"),
                limit=limit,
            )
            if not commits:
                return _success("指定范围内没有提交记录。", {"commits": []})
            lines = ["Git 提交记录："]
            for commit in commits:
                lines.append(
                    f"- {commit.sha[:12]} {commit.committed_at.isoformat()} "
                    f"{commit.author}: {commit.message}"
                )
            return _success(
                "\n".join(lines),
                {
                    "commits": [
                        {
                            "sha": item.sha,
                            "author": item.author,
                            "committed_at": item.committed_at.isoformat(),
                            "message": item.message,
                        }
                        for item in commits
                    ]
                },
            )
        except Exception as exc:
            return _failure(exc)

    def git_diff(self, base: str, head: str, max_bytes: int = 256000) -> ToolChunk:
        """查看当前项目两个 Git 引用之间的差异。

        Args:
            base: 起始引用，例如 main 或某个提交 SHA。
            head: 结束引用，例如 HEAD 或某个提交 SHA。
            max_bytes: 最大返回字节数。
        """
        try:
            project = self._require_project()
            diff = self._context.code.git_diff(project, base=base, head=head, max_bytes=max_bytes)
            return _success(
                diff or "(两个引用之间没有差异)",
                {"base": base, "head": head, "truncated": "[diff 已截断" in diff},
            )
        except Exception as exc:
            return _failure(exc)

    def _require_project(self) -> Project:
        if self._context.project is None:
            raise DomainValidationError("请先选择项目")
        return self._context.project

    def _require_knowledge(self) -> KnowledgeGateway:
        if self._context.knowledge is None:
            raise DomainValidationError("知识库服务未配置")
        return self._context.knowledge


def _parse_datetime(value: str | None, label: str) -> datetime | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise DomainValidationError(f"{label} 不是有效的 ISO 8601 时间") from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _success(text: str, metadata: dict[str, object] | None = None) -> ToolChunk:
    return ToolChunk(
        content=[TextBlock(text=text)],
        state=ToolResultState.SUCCESS,
        metadata=metadata or {},
    )


def _failure(exc: Exception) -> ToolChunk:
    message = exc.message if isinstance(exc, DomainError) else f"工具执行失败: {exc}"
    metadata: dict[str, object] = {"error": message}
    if isinstance(exc, DomainError):
        metadata["error_code"] = exc.code.value
    if isinstance(exc, DomainValidationError) and "请先选择项目" in message:
        metadata["error_code"] = "PROJECT_REQUIRED"
    return ToolChunk(
        content=[TextBlock(text=message)],
        state=ToolResultState.ERROR,
        metadata=metadata,
    )


def tool_result_payload(chunk: ToolChunk) -> str:
    return "\n".join(block.text for block in chunk.content if isinstance(block, TextBlock))


def tool_metadata_json(chunk: ToolChunk) -> str:
    return json.dumps(chunk.metadata, ensure_ascii=False, default=str)
