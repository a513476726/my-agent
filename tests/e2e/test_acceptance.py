from __future__ import annotations

import json
import subprocess
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from agentscope.credential import CredentialBase
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg, TextBlock, ToolCallBlock
from agentscope.model import ChatModelBase, ChatResponse
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from agent_api.config import Settings, get_settings
from agent_api.dependencies import get_chat_model_or_none, get_knowledge_client, get_session_factory
from agent_api.main import create_app
from agent_core import Job, JobKind, JobRunStatus, PageRequest, RetrievalHit, utc_now
from agent_data import UnitOfWork
from agent_worker.jobs import process_pending_runs


class FakeCredential(CredentialBase):
    @classmethod
    def get_chat_model_class(cls) -> type[ChatModelBase]:
        return FakeModel


class FakeModel(ChatModelBase):
    def __init__(self) -> None:
        super().__init__(
            credential=FakeCredential(),
            model="fake-model",
            parameters=ChatModelBase.Parameters(),
            stream=False,
        )
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
        if tools and tool_result is None:
            query = _last_user_text(messages)
            return ChatResponse(
                content=[
                    ToolCallBlock(
                        id=f"call-{uuid4().hex}",
                        name="search_knowledge",
                        input=json.dumps({"query": query}, ensure_ascii=False),
                    )
                ],
                is_last=True,
            )
        return ChatResponse(
            content=[TextBlock(text=f"根据知识库：{tool_result}")],
            is_last=True,
        )


class FakeKnowledge:
    def __init__(self, project_id: UUID, document_id: UUID) -> None:
        self.project_id = project_id
        self.documents = [
            {
                "document_id": document_id,
                "title": "登录需求",
                "source_path": "docs/login.md",
                "content": "用户输入账号密码。",
            }
        ]

    def ensure_dataset(self, project_id: UUID, name: str) -> object:
        from agent_api.knowledge import KnowledgeDataset

        return KnowledgeDataset(
            project_id=project_id,
            dataset_id=f"dataset-{project_id}",
            name=name,
        )

    def upload_document(
        self,
        project_id: UUID,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> object:
        from agent_api.knowledge import KnowledgeDocument

        document_id = uuid4()
        text = content.decode("utf-8")
        title = text.splitlines()[0].removeprefix("# ").strip()
        self.documents.append(
            {
                "document_id": document_id,
                "title": title,
                "source_path": f"capabilities/{filename}",
                "content": text,
            }
        )
        return KnowledgeDocument(
            dataset_id=dataset_id,
            document_id=str(document_id),
            filename=filename,
            parse_started=True,
        )

    def delete_document(self, project_id: UUID, dataset_id: str, document_id: str) -> None:
        self.documents = [
            item for item in self.documents if str(item["document_id"]) != document_id
        ]

    def retrieve(self, query: object) -> tuple[RetrievalHit, ...]:
        if query.project_id != self.project_id:  # type: ignore[attr-defined]
            return ()
        text = query.text  # type: ignore[attr-defined]
        for item in reversed(self.documents):
            title = str(item["title"])
            content = str(item["content"])
            if text not in content and text not in title and title not in text:
                continue
            return (
                RetrievalHit(
                    document_id=item["document_id"],  # type: ignore[arg-type]
                    title=title,
                    source_path=str(item["source_path"]),
                    heading_path=("正文",),
                    snippet=content[:300],
                    score=0.95,
                ),
            )
        return ()


def _last_tool_output(messages: list[Msg]) -> str | None:
    for message in reversed(messages):
        for block in message.content:
            if block.type == "tool_result":
                return "需求已读取"
    return None


def _last_user_text(messages: list[Msg]) -> str:
    for message in reversed(messages):
        if message.role != "user":
            continue
        for block in message.content:
            if block.type == "text":
                return block.text
    return "登录需求"


@pytest.fixture
def e2e_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+psycopg://unused",
        auth_secret=SecretStr("e2e-secret-" + "x" * 32),
        admin_username="admin",
        admin_password=SecretStr("e2e-password"),
    )


@pytest.fixture
def e2e_app(e2e_settings: Settings, session_factory: sessionmaker[Session]) -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: e2e_settings
    application.dependency_overrides[get_session_factory] = lambda: session_factory
    return application


@pytest.fixture
def e2e_client(e2e_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(e2e_app) as client:
        yield client


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "e2e-password"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "e2e@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "E2E"], cwd=path, check=True)
    (path / "app.py").write_text("def login():\n    return True\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: 增加登录"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _seed_job(session_factory: sessionmaker[Session], kind: JobKind, name: str) -> Job:
    now = utc_now()
    job = Job(
        id=uuid4(),
        name=name,
        kind=kind,
        cron="0 2 * * *",
        config=(("lookback_days", 8),),
        created_at=now,
        updated_at=now,
    )
    with UnitOfWork(session_factory) as uow:
        return uow.jobs.add(job)


def test_full_acceptance_flow(
    e2e_app: FastAPI,
    e2e_client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    headers = _login(e2e_client)
    repository = tmp_path / "repo-a"
    _init_repo(repository)
    project_response = e2e_client.post(
        "/api/projects",
        headers=headers,
        json={
            "name": "项目 A",
            "path": str(repository),
            "vcs_type": "git",
            "enabled": True,
        },
    )
    assert project_response.status_code == 200, project_response.text
    project_id = UUID(str(project_response.json()["data"]["id"]))

    document_id = uuid4()
    knowledge = FakeKnowledge(project_id, document_id)
    e2e_app.dependency_overrides[get_knowledge_client] = lambda: knowledge
    e2e_app.dependency_overrides[get_chat_model_or_none] = lambda: FakeModel()

    chat = e2e_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": f"project-{project_id}",
            "messages": [{"role": "user", "content": "登录需求是什么？"}],
        },
    )
    assert chat.status_code == 200, chat.text
    chat_body = chat.json()
    assert chat_body["citations"][0]["document_id"] == str(document_id)

    daily_job = _seed_job(session_factory, JobKind.DAILY_GIT, "每日 Git 日报")
    trigger = e2e_client.post(
        f"/api/jobs/{daily_job.id}/run",
        headers=headers,
        json={"project_id": str(project_id)},
    )
    assert trigger.status_code == 200, trigger.text
    runs = process_pending_runs(session_factory)
    assert [run.status for run in runs] == [JobRunStatus.SUCCEEDED]
    assert runs[0].report_id is not None

    report = e2e_client.get(
        f"/api/reports/{runs[0].report_id}?project_id={project_id}", headers=headers
    )
    assert report.status_code == 200, report.text
    assert "增加登录" in report.json()["data"]["body"]
    assert len(report.json()["data"]["items"]) == 1

    sediment_job = _seed_job(session_factory, JobKind.CAPABILITY_SEDIMENT, "能力沉淀")
    trigger = e2e_client.post(
        f"/api/jobs/{sediment_job.id}/run",
        headers=headers,
        json={"project_id": str(project_id)},
    )
    assert trigger.status_code == 200, trigger.text
    sediment_runs = process_pending_runs(session_factory)
    assert [run.status for run in sediment_runs] == [JobRunStatus.SUCCEEDED]

    with UnitOfWork(session_factory) as uow:
        page = uow.capabilities.list_by_project(project_id, PageRequest())
        assert page.total == 1
        note = page.records[0]
        assert note.topic == "增加登录"
        assert note.source_report_ids == (runs[0].report_id,)

    confirm = e2e_client.patch(
        f"/api/capabilities/{note.id}",
        headers=headers,
        json={"project_id": str(project_id), "status": "confirmed"},
    )
    assert confirm.status_code == 200, confirm.text
    sync = e2e_client.post(
        f"/api/capabilities/{note.id}/sync",
        headers=headers,
        json={"project_id": str(project_id)},
    )
    assert sync.status_code == 200, sync.text

    chat = e2e_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": f"project-{project_id}",
            "messages": [{"role": "user", "content": "增加登录"}],
        },
    )
    assert chat.status_code == 200, chat.text
    assert chat.json()["citations"][0]["document_title"] == "增加登录"
