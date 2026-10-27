from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from agent_api.config import Settings, get_settings
from agent_api.dependencies import get_session_factory
from agent_api.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+psycopg://unused",
        auth_secret=SecretStr("test-secret-" + "x" * 32),
        admin_username="admin",
        admin_password=SecretStr("test-password"),
    )


@pytest.fixture
def app(test_settings: Settings, session_factory: sessionmaker[Session]) -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: test_settings
    application.dependency_overrides[get_session_factory] = lambda: session_factory
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "test-password"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
