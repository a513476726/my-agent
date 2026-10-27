from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    FORBIDDEN = "FORBIDDEN"
    UNAVAILABLE = "UNAVAILABLE"
    INTERNAL = "INTERNAL"


class DomainError(Exception):
    code: ErrorCode = ErrorCode.INTERNAL

    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DomainValidationError(DomainError):
    code = ErrorCode.VALIDATION_ERROR


class NotFoundError(DomainError):
    code = ErrorCode.NOT_FOUND


class ConflictError(DomainError):
    code = ErrorCode.CONFLICT


class ForbiddenError(DomainError):
    code = ErrorCode.FORBIDDEN


class UnavailableError(DomainError):
    code = ErrorCode.UNAVAILABLE
