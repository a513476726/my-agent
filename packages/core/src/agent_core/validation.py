from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath

from .errors import DomainValidationError


def require_text(value: str, field: str) -> str:
    if not value or not value.strip():
        raise DomainValidationError(f"{field} 不能为空")
    return value


def ensure_aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError(f"{field} 必须是带时区的时间")
    return value


def require_absolute_path(value: str, field: str) -> str:
    require_text(value, field)
    if not PurePosixPath(value).is_absolute():
        raise DomainValidationError(f"{field} 必须是绝对路径")
    return value


def require_non_negative(value: int | float, field: str) -> int | float:
    if value < 0:
        raise DomainValidationError(f"{field} 不能为负数")
    return value


def require_positive(value: int, field: str) -> int:
    if value < 1:
        raise DomainValidationError(f"{field} 必须大于 0")
    return value
