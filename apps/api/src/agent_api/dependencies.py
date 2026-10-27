from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from agentscope.model import ChatModelBase
from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from agent_core import UnavailableError
from agent_data import UnitOfWork, build_engine, build_session_factory
from agent_runtime.code_access import LocalCodeAccess
from agent_runtime.runtime import build_volcengine_model

from .config import Settings, get_settings
from .knowledge import KnowledgeClient


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    engine = build_engine(settings.database_url)
    return build_session_factory(engine)


def get_uow(
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> Iterator[UnitOfWork]:
    with UnitOfWork(session_factory) as uow:
        yield uow


def get_knowledge_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[KnowledgeClient]:
    with KnowledgeClient(
        base_url=settings.knowledge_base_url,
        timeout_seconds=settings.knowledge_timeout_seconds,
    ) as client:
        yield client


@lru_cache
def get_code_access() -> LocalCodeAccess:
    return LocalCodeAccess()


@lru_cache
def _build_chat_model(
    *,
    api_key: str,
    model: str,
    base_url: str,
    temperature: float | None,
    max_tokens: int | None,
) -> ChatModelBase:
    return build_volcengine_model(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_chat_model(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatModelBase:
    if settings.ark_api_key is None:
        raise UnavailableError("未配置火山方舟模型密钥 ARK_API_KEY")
    return _build_chat_model(
        api_key=settings.ark_api_key.get_secret_value(),
        model=settings.agent_model,
        base_url=settings.ark_base_url,
        temperature=settings.agent_temperature,
        max_tokens=settings.agent_max_tokens,
    )


def get_chat_model_or_none(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatModelBase | None:
    if settings.ark_api_key is None:
        return None
    return get_chat_model(settings)
