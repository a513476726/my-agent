from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .enums import JobKind, ReportKind
from .errors import DomainValidationError
from .validation import ensure_aware


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportPeriod:
    start: datetime
    end: datetime
    key: str
    label: str

    def __post_init__(self) -> None:
        ensure_aware(self.start, "start")
        ensure_aware(self.end, "end")
        if self.end <= self.start:
            raise DomainValidationError("报告周期结束时间必须晚于开始时间")


_REPORT_KIND_BY_JOB = {
    JobKind.DAILY_GIT: ReportKind.DAILY,
    JobKind.WEEKLY_GIT: ReportKind.WEEKLY,
    JobKind.QUARTERLY_GIT: ReportKind.QUARTERLY,
}


def report_kind_for_job(kind: JobKind) -> ReportKind:
    report_kind = _REPORT_KIND_BY_JOB.get(kind)
    if report_kind is None:
        raise DomainValidationError(f"任务类型不生成周期报告: {kind}")
    return report_kind


def period_for(
    kind: ReportKind,
    at: datetime,
    *,
    timezone: str = "Asia/Shanghai",
) -> ReportPeriod:
    ensure_aware(at, "at")
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise DomainValidationError(f"未知时区: {timezone}") from exc

    local = at.astimezone(zone)
    if kind is ReportKind.DAILY:
        start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)
        key = start_local.strftime("%Y-%m-%d")
        label = key
    elif kind is ReportKind.WEEKLY:
        day_start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_local = day_start - timedelta(days=day_start.weekday())
        end_local = start_local + timedelta(days=7)
        iso = start_local.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        label = f"{iso.year} 年第 {iso.week} 周"
    elif kind is ReportKind.QUARTERLY:
        quarter = (local.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        start_local = local.replace(
            month=start_month,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        if quarter == 4:
            end_local = start_local.replace(year=start_local.year + 1, month=1)
        else:
            end_local = start_local.replace(month=start_month + 3)
        key = f"{start_local.year}-Q{quarter}"
        label = f"{start_local.year} 年第 {quarter} 季度"
    else:
        raise DomainValidationError(f"不支持的报告类型: {kind}")

    return ReportPeriod(
        start=start_local.astimezone(UTC),
        end=end_local.astimezone(UTC),
        key=key,
        label=label,
    )
