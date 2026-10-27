from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from agent_core import (
    Document,
    DocumentStatus,
    KnowledgeBase,
    Page,
    PageRequest,
    Project,
    VcsType,
)

from ..models.project import Document as DocumentModel
from ..models.project import KnowledgeBase as KnowledgeBaseModel
from ..models.project import Project as ProjectModel
from .base import BaseRepository


def _project_to_domain(row: ProjectModel) -> Project:
    return Project(
        id=row.id,
        name=row.name,
        path=row.path,
        vcs_type=VcsType(row.vcs_type),
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _knowledge_base_to_domain(row: KnowledgeBaseModel) -> KnowledgeBase:
    return KnowledgeBase(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        dataset_id=row.dataset_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _document_to_domain(row: DocumentModel) -> Document:
    return Document(
        id=row.id,
        project_id=row.project_id,
        knowledge_base_id=row.knowledge_base_id,
        title=row.title,
        source_path=row.source_path,
        content_hash=row.content_hash,
        version=row.version,
        external_document_id=row.external_document_id,
        status=DocumentStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ProjectRepository(BaseRepository[ProjectModel]):
    model = ProjectModel

    def add(self, project: Project) -> Project:
        row = ProjectModel(
            id=project.id,
            name=project.name,
            path=project.path,
            vcs_type=project.vcs_type.value,
            enabled=project.enabled,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
        return _project_to_domain(self._add(row))

    def update(self, project: Project) -> Project:
        row = self._require(project.id)
        row.name = project.name
        row.path = project.path
        row.vcs_type = project.vcs_type.value
        row.enabled = project.enabled
        self.session.flush()
        self.session.refresh(row)
        return _project_to_domain(row)

    def get(self, project_id: UUID) -> Project | None:
        row = self._get(project_id)
        return _project_to_domain(row) if row else None

    def get_by_path(self, path: str) -> Project | None:
        row = self.session.scalar(select(ProjectModel).where(ProjectModel.path == path))
        return _project_to_domain(row) if row else None

    def list(self, page: PageRequest, *, enabled: bool | None = None) -> Page[Project]:
        stmt = select(ProjectModel).order_by(ProjectModel.created_at, ProjectModel.id)
        if enabled is not None:
            stmt = stmt.where(ProjectModel.enabled == enabled)
        rows, total = self._paginate(stmt, page)
        return Page(records=tuple(_project_to_domain(row) for row in rows), total=total)

    def delete(self, project_id: UUID) -> None:
        self._delete(self._require(project_id))


class KnowledgeBaseRepository(BaseRepository[KnowledgeBaseModel]):
    model = KnowledgeBaseModel

    def add(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        row = KnowledgeBaseModel(
            id=knowledge_base.id,
            project_id=knowledge_base.project_id,
            name=knowledge_base.name,
            dataset_id=knowledge_base.dataset_id,
            created_at=knowledge_base.created_at,
            updated_at=knowledge_base.updated_at,
        )
        return _knowledge_base_to_domain(self._add(row))

    def update(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        row = self._require(knowledge_base.id)
        row.name = knowledge_base.name
        row.dataset_id = knowledge_base.dataset_id
        self.session.flush()
        self.session.refresh(row)
        return _knowledge_base_to_domain(row)

    def get_by_project(self, project_id: UUID) -> KnowledgeBase | None:
        row = self.session.scalar(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.project_id == project_id)
        )
        return _knowledge_base_to_domain(row) if row else None


class DocumentRepository(BaseRepository[DocumentModel]):
    model = DocumentModel

    def add(self, document: Document) -> Document:
        row = DocumentModel(
            id=document.id,
            project_id=document.project_id,
            knowledge_base_id=document.knowledge_base_id,
            title=document.title,
            source_path=document.source_path,
            content_hash=document.content_hash,
            version=document.version,
            external_document_id=document.external_document_id,
            status=document.status.value,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        return _document_to_domain(self._add(row))

    def update(self, document: Document) -> Document:
        row = self._require(document.id)
        row.knowledge_base_id = document.knowledge_base_id
        row.title = document.title
        row.source_path = document.source_path
        row.content_hash = document.content_hash
        row.version = document.version
        row.external_document_id = document.external_document_id
        row.status = document.status.value
        self.session.flush()
        self.session.refresh(row)
        return _document_to_domain(row)

    def get(self, document_id: UUID) -> Document | None:
        row = self._get(document_id)
        return _document_to_domain(row) if row else None

    def find_by_hash(self, project_id: UUID, content_hash: str) -> Document | None:
        row = self.session.scalar(
            select(DocumentModel).where(
                DocumentModel.project_id == project_id,
                DocumentModel.content_hash == content_hash,
            )
        )
        return _document_to_domain(row) if row else None

    def find_by_source_path(self, project_id: UUID, source_path: str) -> Document | None:
        row = self.session.scalar(
            select(DocumentModel).where(
                DocumentModel.project_id == project_id,
                DocumentModel.source_path == source_path,
            )
        )
        return _document_to_domain(row) if row else None

    def list_by_project(self, project_id: UUID, page: PageRequest) -> Page[Document]:
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.project_id == project_id)
            .order_by(DocumentModel.created_at, DocumentModel.id)
        )
        rows, total = self._paginate(stmt, page)
        return Page(records=tuple(_document_to_domain(row) for row in rows), total=total)
