from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ApiEnvelope[T](BaseModel):
    code: int = 0
    data: T
    message: str = "ok"
    success: bool = True


def envelope(data: Any = None, *, message: str = "ok", code: int = 0) -> dict[str, Any]:
    return {"code": code, "data": data, "message": message, "success": code == 0}


def error_envelope(code: int, message: str) -> dict[str, Any]:
    return envelope(None, message=message, code=code)
