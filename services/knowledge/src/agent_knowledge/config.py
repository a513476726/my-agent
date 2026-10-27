from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    ragflow_base_url: str = "http://127.0.0.1:9380"
    ragflow_api_key: str = ""
    ragflow_embedding_model: str = ""
    ragflow_timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            ragflow_base_url=os.getenv("RAGFLOW_BASE_URL", "http://127.0.0.1:9380"),
            ragflow_api_key=os.getenv("RAGFLOW_API_KEY", ""),
            ragflow_embedding_model=os.getenv("RAGFLOW_EMBEDDING_MODEL", ""),
            ragflow_timeout_seconds=float(os.getenv("RAGFLOW_TIMEOUT_SECONDS", "30")),
        )
