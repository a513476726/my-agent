from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings
from .errors import KnowledgeError
from .provider import KnowledgeProvider
from .ragflow import RAGFlowProvider
from .responses import ApiEnvelope, envelope, error_envelope
from .schemas import (
    DatasetCreateRequest,
    DatasetResponse,
    DocumentUploadResponse,
    RetrievalRequest,
    RetrievalResponse,
)
from .service import KnowledgeGatewayService

logger = logging.getLogger(__name__)


def build_provider(settings: Settings) -> KnowledgeProvider:
    return RAGFlowProvider(
        base_url=settings.ragflow_base_url,
        api_key=settings.ragflow_api_key,
        embedding_model=settings.ragflow_embedding_model,
        timeout_seconds=settings.ragflow_timeout_seconds,
    )


def create_app(
    *,
    provider: KnowledgeProvider | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    app_settings = settings or Settings.from_env()
    app_provider = provider or build_provider(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        close = getattr(app_provider, "aclose", None)
        if close is not None:
            await close()

    app = FastAPI(
        title="知识库网关",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.provider = app_provider
    app.state.service = KnowledgeGatewayService(app_provider)

    @app.exception_handler(KnowledgeError)
    async def knowledge_error_handler(request: object, exc: KnowledgeError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(exc.status_code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: object, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_envelope(422, "请求参数校验失败"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: object, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(exc.status_code, message),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: object, exc: Exception) -> JSONResponse:
        logger.exception("知识库网关未处理异常")
        return JSONResponse(status_code=500, content=error_envelope(500, "服务器内部错误"))

    @app.get("/health")
    async def health() -> dict[str, object]:
        return envelope({"status": "ok", "provider": "ragflow"})

    @app.post("/v1/datasets", response_model=ApiEnvelope[DatasetResponse])
    async def create_dataset(payload: DatasetCreateRequest) -> dict[str, object]:
        dataset = await app.state.service.ensure_dataset(payload.project_id, payload.name)
        return envelope(
            DatasetResponse(
                project_id=payload.project_id,
                dataset_id=dataset.id,
                name=dataset.name,
            )
        )

    @app.post(
        "/v1/datasets/{dataset_id}/documents",
        response_model=ApiEnvelope[DocumentUploadResponse],
    )
    async def upload_document(
        dataset_id: str,
        project_id: Annotated[UUID, Form()],
        file: Annotated[UploadFile, File()],
        parse: Annotated[bool, Form()] = True,
    ) -> dict[str, object]:
        document = await app.state.service.upload_document(
            project_id=project_id,
            dataset_id=dataset_id,
            filename=file.filename or "",
            content=await file.read(),
            content_type=file.content_type,
            parse=parse,
        )
        return envelope(
            DocumentUploadResponse(
                dataset_id=document.dataset_id,
                document_id=document.document_id,
                filename=document.filename,
                parse_started=document.parse_started,
            )
        )

    @app.delete("/v1/datasets/{dataset_id}/documents/{document_id}")
    async def delete_document(
        dataset_id: str,
        document_id: str,
        project_id: UUID,
    ) -> dict[str, object]:
        await app.state.service.delete_document(
            project_id=project_id,
            dataset_id=dataset_id,
            document_id=document_id,
        )
        return envelope({"deleted": True})

    @app.post("/v1/retrieval", response_model=ApiEnvelope[RetrievalResponse])
    async def retrieve(payload: RetrievalRequest) -> dict[str, object]:
        result = await app.state.service.retrieve(
            project_id=payload.project_id,
            query=payload.query,
            top_k=payload.top_k,
        )
        return envelope(result)

    return app
