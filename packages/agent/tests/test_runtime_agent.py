from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from agentscope.credential import CredentialBase
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg, TextBlock, ToolCallBlock
from agentscope.model import ChatModelBase, ChatResponse

from agent_core import KnowledgeGateway, Project, RetrievalHit, VcsType
from agent_runtime.code_access import LocalCodeAccess
from agent_runtime.runtime import AgentRunResult, build_agent, stream_agent_reply


class FakeCredential(CredentialBase):
    @classmethod
    def get_chat_model_class(cls) -> type[ChatModelBase]:
        return FakeModel


class FakeModel(ChatModelBase):
    def __init__(self, *, tool_name: str, arguments: str, answer: str = "完成") -> None:
        super().__init__(
            credential=FakeCredential(),
            model="fake-model",
            parameters=ChatModelBase.Parameters(),
            stream=False,
        )
        self.tool_name = tool_name
        self.arguments = arguments
        self.answer = answer
        self.calls = 0
        self.formatter = OpenAIChatFormatter()

    async def _call_api(
        self,
        model_name: str,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: object = None,
        **kwargs: object,
    ) -> ChatResponse | AsyncGenerator[ChatResponse, None]:
        self.calls += 1
        has_tool_result = any(
            block.type == "tool_result" for message in messages for block in message.content
        )
        if tools and not has_tool_result:
            return ChatResponse(
                content=[
                    ToolCallBlock(
                        id="call-1",
                        name=self.tool_name,
                        input=self.arguments,
                    )
                ],
                is_last=True,
            )
        return ChatResponse(content=[TextBlock(text=self.answer)], is_last=True)


class FakeKnowledge:
    def __init__(self, hits: tuple[RetrievalHit, ...]) -> None:
        self.hits = hits

    def retrieve(self, query: object) -> tuple[RetrievalHit, ...]:
        return self.hits


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


async def _collect(agent: object, text: str) -> tuple[str, AgentRunResult]:
    deltas: list[str] = []
    result: AgentRunResult | None = None
    async for update in stream_agent_reply(agent=agent, text=text):  # type: ignore[arg-type]
        if update.delta:
            deltas.append(update.delta)
        if update.result is not None:
            result = update.result
    assert result is not None
    return "".join(deltas), result


def test_agent_executes_read_tool_and_returns_answer(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("项目说明\n", encoding="utf-8")
    model = FakeModel(tool_name="fs_read", arguments='{"path": "README.md"}', answer="已读取")
    agent = build_agent(
        model=model,
        project=_project(tmp_path),
        knowledge=None,
        code=LocalCodeAccess(),
    )

    deltas, result = asyncio.run(_collect(agent, "读取说明"))

    assert "已读取" in deltas
    assert result.content == "已读取"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "fs_read"
    assert result.tool_calls[0].success is True
    assert result.tool_calls[0].arguments == (("path", "README.md"),)


def test_agent_surfaces_tool_failure_in_summary(tmp_path: Path) -> None:
    model = FakeModel(
        tool_name="fs_read",
        arguments='{"path": "../secret.txt"}',
        answer="读取失败，路径越界。",
    )
    agent = build_agent(
        model=model,
        project=_project(tmp_path),
        knowledge=None,
        code=LocalCodeAccess(),
    )

    _, result = asyncio.run(_collect(agent, "读取项目外文件"))

    assert result.tool_calls[0].success is False
    assert "超出项目根目录" in (result.tool_calls[0].error or "")


def test_agent_keeps_citations_from_knowledge_tool(tmp_path: Path) -> None:
    document_id = uuid4()
    knowledge = FakeKnowledge(
        (
            RetrievalHit(
                document_id=document_id,
                title="需求说明",
                source_path="docs/requirement.md",
                heading_path=("登录",),
                snippet="用户输入账号密码",
                score=0.8,
            ),
        )
    )
    model = FakeModel(
        tool_name="search_knowledge",
        arguments='{"query": "登录"}',
        answer="需求要求用户输入账号密码。",
    )
    agent = build_agent(
        model=model,
        project=_project(tmp_path),
        knowledge=cast(KnowledgeGateway, knowledge),
        code=LocalCodeAccess(),
    )

    _, result = asyncio.run(_collect(agent, "登录需求是什么"))

    assert len(result.citations) == 1
    assert result.citations[0].document_id == document_id
    assert result.citations[0].heading_path == ("登录",)
