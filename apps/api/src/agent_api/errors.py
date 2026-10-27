from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from agent_core import DomainError, ErrorCode

from .responses import error_envelope

logger = logging.getLogger(__name__)

ERROR_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.UNAVAILABLE: 503,
    ErrorCode.INTERNAL: 500,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        status = ERROR_STATUS.get(exc.code, 500)
        return JSONResponse(
            status_code=status,
            content=error_envelope(status, exc.message, jsonable_encoder(exc.details)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_envelope(422, "请求参数校验失败", jsonable_encoder(exc.errors())),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(exc.status_code, message),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_envelope(500, "服务器内部错误"),
        )
