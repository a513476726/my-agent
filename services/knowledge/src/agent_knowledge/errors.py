from __future__ import annotations


class KnowledgeError(Exception):
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class KnowledgeValidationError(KnowledgeError):
    status_code = 400


class DatasetNotConfiguredError(KnowledgeError):
    status_code = 404


class DatasetProjectMismatchError(KnowledgeError):
    status_code = 404


class KnowledgeUpstreamError(KnowledgeError):
    status_code = 502


class KnowledgeUnavailableError(KnowledgeError):
    status_code = 503
