from __future__ import annotations

import logging
import os
import signal
import threading
from datetime import datetime
from uuid import UUID

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session, sessionmaker

from agent_core import JobRunStatus, TriggerType
from agent_data import UnitOfWork, build_engine, build_session_factory

from .jobs import process_job, process_pending_runs

logger = logging.getLogger(__name__)

_CRON_PREFIX = "cron:"
_PENDING_JOB_ID = "pending-runs"
_SCHEDULE_SYNC_JOB_ID = "sync-schedules"


def build_scheduler(
    session_factory: sessionmaker[Session],
    *,
    timezone: str = "Asia/Shanghai",
    pending_interval_seconds: int = 10,
    schedule_sync_interval_seconds: int = 30,
) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(
        process_pending_runs,
        trigger=IntervalTrigger(seconds=pending_interval_seconds),
        args=[session_factory],
        id=_PENDING_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        sync_schedules,
        trigger=IntervalTrigger(seconds=schedule_sync_interval_seconds),
        args=[scheduler, session_factory],
        kwargs={"timezone": timezone},
        id=_SCHEDULE_SYNC_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sync_schedules(scheduler, session_factory, timezone=timezone)
    return scheduler


def sync_schedules(
    scheduler: BackgroundScheduler,
    session_factory: sessionmaker[Session],
    *,
    timezone: str = "Asia/Shanghai",
) -> None:
    with UnitOfWork(session_factory) as uow:
        jobs = uow.jobs.list_enabled()

    desired = {str(job.id): job for job in jobs}
    for scheduled in scheduler.get_jobs():
        if not scheduled.id.startswith(_CRON_PREFIX):
            continue
        job_id = scheduled.id.removeprefix(_CRON_PREFIX)
        if job_id not in desired:
            scheduler.remove_job(scheduled.id)

    for job_id, job in desired.items():
        trigger = CronTrigger.from_crontab(job.cron, timezone=timezone)
        scheduler.add_job(
            _run_cron_job,
            trigger=trigger,
            args=[session_factory, job.id],
            id=f"{_CRON_PREFIX}{job_id}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )


def _run_cron_job(
    session_factory: sessionmaker[Session],
    job_id: UUID,
) -> None:
    with UnitOfWork(session_factory) as uow:
        job = uow.jobs.get(job_id)
        if job is None or not job.enabled:
            return
    process_job(
        session_factory,
        job_id,
        trigger=TriggerType.SCHEDULE,
        actor="scheduler",
    )


def run_pending_once(session_factory: sessionmaker[Session]) -> tuple[JobRunStatus, ...]:
    return tuple(run.status for run in process_pending_runs(session_factory))


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL 未设置")
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    scheduler = build_scheduler(session_factory)
    stop = threading.Event()

    def handle_signal(signum: int, frame: object) -> None:
        logger.info("收到信号 %s，准备停止调度器", signum)
        stop.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    scheduler.start()
    logger.info("调度器已启动，任务数=%s", len(scheduler.get_jobs()))
    try:
        stop.wait()
    finally:
        scheduler.shutdown(wait=False)
        engine.dispose()


if __name__ == "__main__":
    main()
