from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

import agent_data.models  # noqa: F401
from agent_data.base import Base
from agent_data.session import build_session_factory


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL 或 DATABASE_URL 未设置")
    return url


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> Iterator[sessionmaker[Session]]:
    Base.metadata.drop_all(engine, checkfirst=True)
    Base.metadata.create_all(engine)
    yield build_session_factory(engine)
    Base.metadata.drop_all(engine, checkfirst=True)
