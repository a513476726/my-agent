from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ApiEnvelope[T](BaseModel):
    code: int = 0
    data: T
    message: str = "ok"
    success: bool = True


class PageData[T](BaseModel):
    records: list[T]
    total: int


def envelope(
    data: Any = None,
    *,
    message: str = "ok",
    code: int = 0,
    success: bool = True,
) -> dict[str, Any]:
    return {"code": code, "data": data, "message": message, "success": success}


def error_envelope(code: int, message: str, data: Any = None) -> dict[str, Any]:
    return envelope(data, message=message, code=code, success=False)


def page_payload(records: tuple[Any, ...] | list[Any], total: int) -> dict[str, Any]:
    return {"records": list(records), "total": total}
