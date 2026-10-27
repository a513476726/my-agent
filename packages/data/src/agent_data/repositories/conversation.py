from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from agent_core import (
    AuditLog,
    Conversation,
    Message,
    MessageRole,
    Page,
    PageRequest,
)

from ..models.conversation import AuditLog as AuditLogModel
from ..models.conversation import Conversation as ConversationModel
from ..models.conversation import Message as MessageModel
from .base import BaseRepository
from .mappers import (
    citations_from_json,
    citations_to_json,
    tool_calls_from_json,
    tool_calls_to_json,
)


def _conversation_to_domain(row: ConversationModel) -> Conversation:
    return Conversation(
        id=row.id,
        project_id=row.project_id,
        agent_id=row.agent_id,
        title=row.title,
        external_id=row.external_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _message_to_domain(row: MessageModel) -> Message:
    return Message(
        id=row.id,
        conversation_id=row.conversation_id,
        role=MessageRole(row.role),
        content=row.content,
        tool_calls=tool_calls_from_json(row.tool_calls),
        citations=citations_from_json(row.citations),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _audit_to_domain(row: AuditLogModel) -> AuditLog:
    return AuditLog(
        id=row.id,
        project_id=row.project_id,
        actor=row.actor,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        detail=row.detail,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ConversationRepository(BaseRepository[ConversationModel]):
    model = ConversationModel

    def add(self, conversation: Conversation) -> Conversation:
        row = ConversationModel(
            id=conversation.id,
            project_id=conversation.project_id,
            agent_id=conversation.agent_id,
            title=conversation.title,
            external_id=conversation.external_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        return _conversation_to_domain(self._add(row))

    def update(self, conversation: Conversation) -> Conversation:
        row = self._require(conversation.id)
        row.agent_id = conversation.agent_id
        row.title = conversation.title
        row.external_id = conversation.external_id
        self.session.flush()
        self.session.refresh(row)
        return _conversation_to_domain(row)

    def get(self, conversation_id: UUID) -> Conversation | None:
        row = self._get(conversation_id)
        return _conversation_to_domain(row) if row else None

    def find_by_external_id(self, external_id: str) -> Conversation | None:
        row = self.session.scalar(
            select(ConversationModel).where(ConversationModel.external_id == external_id)
        )
        return _conversation_to_domain(row) if row else None

    def list_by_project(self, project_id: UUID, page: PageRequest) -> Page[Conversation]:
        stmt = (
            select(ConversationModel)
            .where(ConversationModel.project_id == project_id)
            .order_by(ConversationModel.updated_at.desc(), ConversationModel.id)
        )
        rows, total = self._paginate(stmt, page)
        return Page(records=tuple(_conversation_to_domain(row) for row in rows), total=total)


class MessageRepository(BaseRepository[MessageModel]):
    model = MessageModel

    def add(self, message: Message) -> Message:
        row = MessageModel(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role.value,
            content=message.content,
            tool_calls=tool_calls_to_json(message.tool_calls),
            citations=citations_to_json(message.citations),
            created_at=message.created_at,
            updated_at=message.updated_at,
        )
        return _message_to_domain(self._add(row))

    def list_by_conversation(self, conversation_id: UUID) -> tuple[Message, ...]:
        rows = self.session.scalars(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at, MessageModel.id)
        ).all()
        return tuple(_message_to_domain(row) for row in rows)


class AuditLogRepository(BaseRepository[AuditLogModel]):
    model = AuditLogModel

    def add(self, log: AuditLog) -> AuditLog:
        row = AuditLogModel(
            id=log.id,
            project_id=log.project_id,
            actor=log.actor,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            detail=None if log.detail is None else dict(log.detail),
            created_at=log.created_at,
            updated_at=log.updated_at,
        )
        return _audit_to_domain(self._add(row))

    def list(self, page: PageRequest, *, project_id: UUID | None = None) -> Page[AuditLog]:
        stmt = select(AuditLogModel).order_by(
            AuditLogModel.created_at.desc(), AuditLogModel.id.desc()
        )
        if project_id is not None:
            stmt = stmt.where(AuditLogModel.project_id == project_id)
        rows, total = self._paginate(stmt, page)
        return Page(records=tuple(_audit_to_domain(row) for row in rows), total=total)
