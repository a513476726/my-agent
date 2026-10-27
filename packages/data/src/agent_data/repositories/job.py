from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from agent_core import (
    Agent,
    Job,
    JobKind,
    JobRun,
    JobRunStatus,
    Page,
    PageRequest,
    TriggerType,
)

from ..models.job import Agent as AgentModel
from ..models.job import Job as JobModel
from ..models.job import JobRun as JobRunModel
from .base import BaseRepository


def _agent_to_domain(row: AgentModel) -> Agent:
    return Agent(
        id=row.id,
        name=row.name,
        model=row.model,
        system_prompt=row.system_prompt,
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _job_to_domain(row: JobModel) -> Job:
    return Job(
        id=row.id,
        name=row.name,
        kind=JobKind(row.kind),
        cron=row.cron,
        enabled=row.enabled,
        config=tuple(row.config.items()),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _run_to_domain(row: JobRunModel) -> JobRun:
    return JobRun(
        id=row.id,
        job_id=row.job_id,
        project_id=row.project_id,
        run_key=row.run_key,
        status=JobRunStatus(row.status),
        trigger=TriggerType(row.trigger),
        started_at=row.started_at,
        finished_at=row.finished_at,
        error_message=row.error_message,
        report_id=row.report_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class AgentRepository(BaseRepository[AgentModel]):
    model = AgentModel

    def add(self, agent: Agent) -> Agent:
        row = AgentModel(
            id=agent.id,
            name=agent.name,
            model=agent.model,
            system_prompt=agent.system_prompt,
            enabled=agent.enabled,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
        return _agent_to_domain(self._add(row))

    def update(self, agent: Agent) -> Agent:
        row = self._require(agent.id)
        row.name = agent.name
        row.model = agent.model
        row.system_prompt = agent.system_prompt
        row.enabled = agent.enabled
        self.session.flush()
        self.session.refresh(row)
        return _agent_to_domain(row)

    def get(self, agent_id: UUID) -> Agent | None:
        row = self._get(agent_id)
        return _agent_to_domain(row) if row else None

    def list(self) -> tuple[Agent, ...]:
        rows = self.session.scalars(select(AgentModel).order_by(AgentModel.name)).all()
        return tuple(_agent_to_domain(row) for row in rows)


class JobRepository(BaseRepository[JobModel]):
    model = JobModel

    def add(self, job: Job) -> Job:
        row = JobModel(
            id=job.id,
            name=job.name,
            kind=job.kind.value,
            cron=job.cron,
            enabled=job.enabled,
            config=dict(job.config),
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        return _job_to_domain(self._add(row))

    def update(self, job: Job) -> Job:
        row = self._require(job.id)
        row.name = job.name
        row.kind = job.kind.value
        row.cron = job.cron
        row.enabled = job.enabled
        row.config = dict(job.config)
        self.session.flush()
        self.session.refresh(row)
        return _job_to_domain(row)

    def get(self, job_id: UUID) -> Job | None:
        row = self._get(job_id)
        return _job_to_domain(row) if row else None

    def list(self) -> tuple[Job, ...]:
        rows = self.session.scalars(select(JobModel).order_by(JobModel.name)).all()
        return tuple(_job_to_domain(row) for row in rows)

    def list_enabled(self) -> tuple[Job, ...]:
        rows = self.session.scalars(
            select(JobModel).where(JobModel.enabled.is_(True)).order_by(JobModel.name)
        ).all()
        return tuple(_job_to_domain(row) for row in rows)

    def list_page(self, page: PageRequest) -> Page[Job]:
        stmt = select(JobModel).order_by(JobModel.name, JobModel.id)
        rows, total = self._paginate(stmt, page)
        return Page(records=tuple(_job_to_domain(row) for row in rows), total=total)


class JobRunRepository(BaseRepository[JobRunModel]):
    model = JobRunModel

    def add(self, run: JobRun) -> JobRun:
        row = JobRunModel(
            id=run.id,
            job_id=run.job_id,
            project_id=run.project_id,
            run_key=run.run_key,
            status=run.status.value,
            trigger=run.trigger.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error_message=run.error_message,
            report_id=run.report_id,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
        return _run_to_domain(self._add(row))

    def update(self, run: JobRun) -> JobRun:
        row = self._require(run.id)
        row.status = run.status.value
        row.trigger = run.trigger.value
        row.started_at = run.started_at
        row.finished_at = run.finished_at
        row.error_message = run.error_message
        row.report_id = run.report_id
        self.session.flush()
        self.session.refresh(row)
        return _run_to_domain(row)

    def get(self, run_id: UUID) -> JobRun | None:
        row = self._get(run_id)
        return _run_to_domain(row) if row else None

    def find_by_run_key(self, run_key: str) -> JobRun | None:
        row = self.session.scalar(select(JobRunModel).where(JobRunModel.run_key == run_key))
        return _run_to_domain(row) if row else None

    def list_by_job(self, job_id: UUID, page: PageRequest) -> Page[JobRun]:
        stmt = (
            select(JobRunModel)
            .where(JobRunModel.job_id == job_id)
            .order_by(JobRunModel.created_at.desc(), JobRunModel.id)
        )
        rows, total = self._paginate(stmt, page)
        return Page(records=tuple(_run_to_domain(row) for row in rows), total=total)

    def list_pending(self, limit: int = 100) -> tuple[JobRun, ...]:
        rows = self.session.scalars(
            select(JobRunModel)
            .where(JobRunModel.status == JobRunStatus.PENDING.value)
            .order_by(JobRunModel.created_at, JobRunModel.id)
            .limit(limit)
        ).all()
        return tuple(_run_to_domain(row) for row in rows)
