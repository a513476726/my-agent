"""知识库网关（封装 RAGFlow）。"""

from .app import create_app
from .errors import (
    DatasetNotConfiguredError,
    DatasetProjectMismatchError,
    KnowledgeError,
    KnowledgeUnavailableError,
    KnowledgeUpstreamError,
    KnowledgeValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "DatasetNotConfiguredError",
    "DatasetProjectMismatchError",
    "KnowledgeError",
    "KnowledgeUnavailableError",
    "KnowledgeUpstreamError",
    "KnowledgeValidationError",
    "create_app",
]
