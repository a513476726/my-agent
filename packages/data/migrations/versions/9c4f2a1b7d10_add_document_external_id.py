"""add document external id

Revision ID: 9c4f2a1b7d10
Revises: 70c2bb38b1f3
Create Date: 2026-10-26 16:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c4f2a1b7d10"
down_revision: str | None = "70c2bb38b1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("external_document_id", sa.String(length=200), nullable=True),
    )
    op.create_unique_constraint(
        "uq_documents_external_document_id",
        "documents",
        ["external_document_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_documents_external_document_id",
        "documents",
        type_="unique",
    )
    op.drop_column("documents", "external_document_id")
