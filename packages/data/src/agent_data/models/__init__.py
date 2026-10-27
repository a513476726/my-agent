"""SQLAlchemy 表模型。

导入本模块即完成全部表在 `Base.metadata` 中的注册，供 Alembic 使用。
"""

from .capability import CapabilityNote
from .conversation import AuditLog, Conversation, Message
from .job import Agent, Job, JobRun
from .project import Document, KnowledgeBase, Project
from .report import Report, ReportItem

__all__ = [
    "Agent",
    "AuditLog",
    "CapabilityNote",
    "Conversation",
    "Document",
    "Job",
    "JobRun",
    "KnowledgeBase",
    "Message",
    "Project",
    "Report",
    "ReportItem",
]
