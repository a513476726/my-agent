from __future__ import annotations

from typing import cast
from uuid import UUID

from agent_core import Citation, ToolCallSummary


def tool_calls_to_json(items: tuple[ToolCallSummary, ...]) -> list[dict[str, object]]:
    return [
        {
            "name": item.name,
            "success": item.success,
            "arguments": dict(item.arguments),
            "error": item.error,
            "duration_ms": item.duration_ms,
        }
        for item in items
    ]


def tool_calls_from_json(items: list[dict[str, object]]) -> tuple[ToolCallSummary, ...]:
    summaries: list[ToolCallSummary] = []
    for item in items:
        arguments = cast(dict[str, object], item.get("arguments") or {})
        summaries.append(
            ToolCallSummary(
                name=str(item["name"]),
                success=bool(item["success"]),
                arguments=tuple((str(key), value) for key, value in arguments.items()),
                error=cast(str | None, item.get("error")),
                duration_ms=cast(int | None, item.get("duration_ms")),
            )
        )
    return tuple(summaries)


def citations_to_json(items: tuple[Citation, ...]) -> list[dict[str, object]]:
    return [
        {
            "document_id": str(item.document_id),
            "document_title": item.document_title,
            "heading_path": list(item.heading_path),
            "snippet": item.snippet,
            "score": item.score,
            "page": item.page,
        }
        for item in items
    ]


def citations_from_json(items: list[dict[str, object]]) -> tuple[Citation, ...]:
    citations: list[Citation] = []
    for item in items:
        heading_path = cast(list[object], item.get("heading_path") or [])
        citations.append(
            Citation(
                document_id=UUID(str(item["document_id"])),
                document_title=str(item["document_title"]),
                heading_path=tuple(str(heading) for heading in heading_path),
                snippet=str(item["snippet"]),
                score=cast(float | None, item.get("score")),
                page=cast(int | None, item.get("page")),
            )
        )
    return tuple(citations)
