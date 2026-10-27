from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    username: str
    role: str = "admin"


def create_access_token(username: str, role: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(
        payload,
        settings.auth_secret.get_secret_value(),
        algorithm="HS256",
    )


def _decode_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret.get_secret_value(),
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的凭证",
        ) from exc
    return payload


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Bearer 凭证",
        )
    payload = _decode_token(credentials.credentials, settings)
    username = payload.get("sub")
    if not isinstance(username, str) or not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="凭证缺少用户标识",
        )
    return CurrentUser(username=username, role=str(payload.get("role", "admin")))


def require_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )
    return user


def get_api_caller(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Bearer 凭证",
        )
    configured = settings.openai_api_key
    if configured is not None and compare_digest(
        credentials.credentials, configured.get_secret_value()
    ):
        return CurrentUser(username="api-client", role="admin")
    return get_current_user(credentials, settings)
