from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .errors import register_exception_handlers
from .modules.admin.router import router as admin_router
from .modules.auth.router import router as auth_router
from .modules.capability.router import router as capability_router
from .modules.chat.openai_router import router as openai_router
from .modules.chat.router import router as chat_router
from .modules.document.router import router as document_router
from .modules.health.router import router as health_router
from .modules.job.router import router as job_router
from .modules.project.router import router as project_router
from .modules.report.router import router as report_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(project_router)
    app.include_router(document_router)
    app.include_router(report_router)
    app.include_router(capability_router)
    app.include_router(job_router)
    app.include_router(chat_router)
    app.include_router(openai_router)
    return app


app = create_app()
