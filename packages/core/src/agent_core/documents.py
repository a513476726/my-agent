from __future__ import annotations

from pathlib import PurePosixPath

SUPPORTED_DOCUMENT_SUFFIXES = frozenset(
    {
        ".csv",
        ".doc",
        ".docx",
        ".eml",
        ".gif",
        ".htm",
        ".html",
        ".jpeg",
        ".jpg",
        ".json",
        ".markdown",
        ".md",
        ".msg",
        ".pdf",
        ".png",
        ".ppt",
        ".pptx",
        ".txt",
        ".xls",
        ".xlsx",
    }
)


def is_supported_document_filename(filename: str) -> bool:
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.casefold()
    return suffix in SUPPORTED_DOCUMENT_SUFFIXES
