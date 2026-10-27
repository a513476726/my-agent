from __future__ import annotations

from dataclasses import dataclass

from .errors import DomainValidationError


@dataclass(frozen=True, slots=True, kw_only=True)
class PageRequest:
    limit: int = 20
    offset: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 200:
            raise DomainValidationError("limit 必须在 1 到 200 之间")
        if self.offset < 0:
            raise DomainValidationError("offset 不能为负数")


@dataclass(frozen=True, slots=True, kw_only=True)
class Page[T]:
    records: tuple[T, ...]
    total: int

    def __post_init__(self) -> None:
        if self.total < 0:
            raise DomainValidationError("total 不能为负数")
        if len(self.records) > self.total:
            raise DomainValidationError("records 数量不能超过 total")
