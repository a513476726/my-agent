from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OpenAIMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, object]] | None = None
    name: str | None = None

    def text(self) -> str:
        if isinstance(self.content, str):
            return self.content
        if not isinstance(self.content, list):
            return ""
        parts: list[str] = []
        for item in self.content:
            if item.get("type") in {"text", "input_text"} and isinstance(item.get("text"), str):
                parts.append(str(item["text"]))
        return "\n".join(parts)


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(min_length=1)
    messages: list[OpenAIMessage] = Field(min_length=1)
    stream: bool = False
    project_id: UUID | None = None
    conversation_id: UUID | None = None
    external_conversation_id: str | None = Field(default=None, max_length=200)

    def last_user_text(self) -> str:
        for message in reversed(self.messages):
            if message.role == "user" and message.text().strip():
                return message.text().strip()
        return ""
