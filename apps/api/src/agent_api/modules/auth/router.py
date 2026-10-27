from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ...config import Settings, get_settings
from ...responses import ApiEnvelope, envelope
from ...security import create_access_token
from .schemas import LoginRequest, LoginResponse
from .service import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiEnvelope[LoginResponse])
def login(
    body: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    if not authenticate(settings, body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(settings.admin_username, "admin", settings)
    return envelope(
        {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.access_token_ttl_minutes * 60,
            "username": settings.admin_username,
            "role": "admin",
        }
    )
