from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ...dependencies import get_session_factory
from ...responses import ApiEnvelope, envelope
from .schemas import HealthData

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=ApiEnvelope[HealthData],
    responses={503: {"model": ApiEnvelope[HealthData]}},
)
def health(
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> Any:
    try:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content=envelope(
                {"status": "degraded", "database": "unavailable"},
                message="数据库不可用",
                code=503,
                success=False,
            ),
        )
    return envelope({"status": "ok", "database": "ok"})
