from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import UUID, uuid4

from agentscope.credential import CredentialBase
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg, TextBlock, ToolCallBlock
from agentscope.model import ChatModelBase, ChatResponse
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from agent_api.config import Settings
from agent_api.dependencies import get_chat_model_or_none, get_knowledge_client
from agent_core import RetrievalHit
from agent_data.models.conversation import Conversation as ConversationModel


class FakeCredential(CredentialBase):
    @classmethod
    def get_chat_model_class(cls) -> type[ChatModelBase]:
        return FakeModel


class FakeModel(ChatModelBase):
    def __init__(
        self,
        *,
        tool_name: str | None = None,
        arguments: str = "{}",
        answer: str = "测试回答",
        echo_tool_result: bool = False,
    ) -> None:
        super().__init__(
            credential=FakeCredential(),
            model="fake-model",
            parameters=ChatModelBase.Parameters(),
            stream=False,
        )
        self.tool_name = tool_name
        self.arguments = arguments
        self.answer = answer
        self.echo_tool_result = echo_tool_result
        self.formatter = OpenAIChatFormatter()

    async def _call_api(
        self,
        model_name: str,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: object = None,
        **kwargs: object,
    ) -> ChatResponse | AsyncGenerator[ChatResponse, None]:
        tool_result = _last_tool_output(messages)
        if self.tool_name and tools and tool_result is None:
            return ChatResponse(
                content=[
                    ToolCallBlock(
                        id=f"call-{uuid4().hex}",
                        name=self.tool_name,
                        input=self.arguments,
                    )
                ],
                is_last=True,
            )
        answer = f"读取到：{tool_result}" if self.echo_tool_result and tool_result else self.answer
        return ChatResponse(content=[TextBlock(text=answer)], is_last=True)


class FakeKnowledge:
    def __init__(self, hits: dict[UUID, RetrievalHit] | None = None) -> None:
        self.hits = hits or {}

    def retrieve(self, query: object) -> tuple[RetrievalHit, ...]:
        hit = self.hits.get(query.project_id)  # type: ignore[attr-defined]
        return (hit,) if hit is not None else ()


def _last_tool_output(messages: list[Msg]) -> str | None:
    for message in reversed(messages):
        for block in message.content:
            if block.type != "tool_result":
                continue
            output = block.output
            if isinstance(output, str):
                return output
            return "".join(item.text for item in output if item.type == "text")
    return None


def _create_project(
    client: TestClient, headers: dict[str, str], name: str, path: Path
) -> dict[str, object]:
    response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": name, "path": str(path), "vcs_type": "git", "enabled": True},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _install_model(app: FastAPI, model: FakeModel) -> None:
    app.dependency_overrides[get_chat_model_or_none] = lambda: model


def _install_knowledge(app: FastAPI, knowledge: FakeKnowledge) -> None:
    app.dependency_overrides[get_knowledge_client] = lambda: knowledge


def _chat(
    client: TestClient,
    headers: dict[str, str],
    *,
    model: str,
    text: str,
    stream: bool = False,
) -> object:
    response = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": [{"role": "user", "content": text}],
            "stream": stream,
        },
    )
    assert response.status_code == 200, response.text
    return response


def test_models_endpoint_requires_auth_and_lists_project_models(client: TestClient) -> None:
    response = client.get("/v1/models")

    assert response.status_code == 401


def test_models_endpoint_lists_project_scoped_models(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    project = _create_project(client, auth_headers, "项目 A", tmp_path)

    response = client.get("/v1/models", headers=auth_headers)

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert f"project-{project['id']}" in ids


def test_models_endpoint_accepts_librechat_static_key(
    client: TestClient, test_settings: Settings
) -> None:
    test_settings.openai_api_key = SecretStr("librechat-test-token")

    response = client.get(
        "/v1/models",
        headers={"Authorization": "Bearer librechat-test-token"},
    )

    assert response.status_code == 200


def test_chat_without_project_returns_prompt_without_persisting(
    client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    response = _chat(
        client,
        auth_headers,
        model="doubao-seed-2-1-pro-260628",
        text="没有项目的提问",
    )

    body = response.json()  # type: ignore[attr-defined]
    assert "请先选择项目" in body["choices"][0]["message"]["content"]
    assert body["tool_calls"] == []
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ConversationModel)) == 0


def test_chat_executes_tool_and_persists_history(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("项目说明\n", encoding="utf-8")
    project = _create_project(client, auth_headers, "项目 A", tmp_path)
    _install_model(
        app,
        FakeModel(
            tool_name="fs_read",
            arguments='{"path": "README.md"}',
            answer="实现位于 README.md。",
        ),
    )

    response = _chat(
        client,
        auth_headers,
        model=f"project-{project['id']}",
        text="实现写在哪里？",
    )
    body = response.json()  # type: ignore[attr-defined]

    assert body["choices"][0]["message"]["content"] == "实现位于 README.md。"
    assert body["tool_calls"][0]["name"] == "fs_read"
    assert body["tool_calls"][0]["success"] is True

    conversations = client.get(
        f"/api/chat/conversations?project_id={project['id']}", headers=auth_headers
    ).json()["data"]["records"]
    conversation_id = conversations[0]["id"]
    messages = client.get(
        f"/api/chat/conversations/{conversation_id}/messages?project_id={project['id']}",
        headers=auth_headers,
    ).json()["data"]

    assert [item["role"] for item in messages] == ["user", "assistant"]
    assert messages[1]["tool_calls"][0]["name"] == "fs_read"

    audits = client.get("/admin/audit-logs", headers=auth_headers).json()["data"]["records"]
    assert any(item["action"] == "chat.tool_call" for item in audits)


def test_chat_stream_returns_sse_and_persists_assistant(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    project = _create_project(client, auth_headers, "项目 A", tmp_path)
    _install_model(app, FakeModel(answer="流式回答"))

    response = _chat(
        client,
        auth_headers,
        model=f"project-{project['id']}",
        text="流式问题",
        stream=True,
    )

    lines = [line for line in response.text.splitlines() if line.startswith("data: ")]  # type: ignore[attr-defined]
    payloads = [line.removeprefix("data: ") for line in lines]
    assert payloads[-1] == "[DONE]"
    content = "".join(
        json.loads(item)["choices"][0]["delta"].get("content", "")
        for item in payloads[:-1]
        if "choices" in json.loads(item)
    )
    assert "流式回答" in content


def test_knowledge_citation_is_returned_and_persisted(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    project = _create_project(client, auth_headers, "项目 A", tmp_path)
    document_id = uuid4()
    _install_knowledge(
        app,
        FakeKnowledge(
            {
                UUID(str(project["id"])): RetrievalHit(
                    document_id=document_id,
                    title="需求说明",
                    source_path="docs/requirement.md",
                    heading_path=("登录",),
                    snippet="用户输入账号密码",
                    score=0.9,
                )
            }
        ),
    )
    _install_model(
        app,
        FakeModel(
            tool_name="search_knowledge",
            arguments='{"query": "登录需求"}',
            answer="需求要求输入账号密码。",
        ),
    )

    response = _chat(
        client,
        auth_headers,
        model=f"project-{project['id']}",
        text="登录需求是什么？",
    )
    body = response.json()  # type: ignore[attr-defined]

    assert body["citations"][0]["document_id"] == str(document_id)
    assert "参考来源" in body["choices"][0]["message"]["content"]

    conversations = client.get(
        f"/api/chat/conversations?project_id={project['id']}", headers=auth_headers
    ).json()["data"]["records"]
    messages = client.get(
        f"/api/chat/conversations/{conversations[0]['id']}/messages?project_id={project['id']}",
        headers=auth_headers,
    ).json()["data"]
    assert messages[1]["citations"][0]["document_id"] == str(document_id)


def test_tool_failure_is_visible_and_persisted(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    project = _create_project(client, auth_headers, "项目 A", tmp_path)
    _install_model(
        app,
        FakeModel(
            tool_name="fs_read",
            arguments='{"path": "../secret.txt"}',
            answer="无法读取项目外文件。",
        ),
    )

    response = _chat(
        client,
        auth_headers,
        model=f"project-{project['id']}",
        text="读取项目外文件",
    )
    body = response.json()  # type: ignore[attr-defined]

    assert body["tool_calls"][0]["success"] is False
    assert "超出项目根目录" in body["tool_calls"][0]["error"]
    assert "工具调用失败" in body["choices"][0]["message"]["content"]

    conversations = client.get(
        f"/api/chat/conversations?project_id={project['id']}", headers=auth_headers
    ).json()["data"]["records"]
    messages = client.get(
        f"/api/chat/conversations/{conversations[0]['id']}/messages?project_id={project['id']}",
        headers=auth_headers,
    ).json()["data"]
    assert messages[1]["tool_calls"][0]["success"] is False


def test_same_question_is_isolated_between_projects(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    (root_a / "README.md").write_text("项目 A 的说明\n", encoding="utf-8")
    (root_b / "README.md").write_text("项目 B 的说明\n", encoding="utf-8")
    project_a = _create_project(client, auth_headers, "项目 A", root_a)
    project_b = _create_project(client, auth_headers, "项目 B", root_b)
    _install_model(
        app,
        FakeModel(
            tool_name="fs_read",
            arguments='{"path": "README.md"}',
            echo_tool_result=True,
        ),
    )

    response_a = _chat(
        client, auth_headers, model=f"project-{project_a['id']}", text="说明是什么？"
    ).json()  # type: ignore[attr-defined]
    response_b = _chat(
        client, auth_headers, model=f"project-{project_b['id']}", text="说明是什么？"
    ).json()  # type: ignore[attr-defined]
    content_a = response_a["choices"][0]["message"]["content"]
    content_b = response_b["choices"][0]["message"]["content"]

    assert "项目 A 的说明" in content_a
    assert "项目 B 的说明" not in content_a
    assert "项目 B 的说明" in content_b
    assert "项目 A 的说明" not in content_b
