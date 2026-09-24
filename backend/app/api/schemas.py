"""Request/response models for the public API."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from backend.app.config import get_settings

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class ChatContext(BaseModel):
    previous_intent: str | None = Field(None, max_length=64)
    depth: int = Field(0, ge=0, le=1)


class ChatRequest(BaseModel):
    message: str
    context: ChatContext = Field(default_factory=ChatContext)
    input_mode: str = Field("text", pattern="^(text|voice)$")  # informational only

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        value = re.sub(r"\s+", " ", CONTROL_CHARS.sub(" ", value)).strip()
        if not value:
            raise ValueError("Message must not be empty")
        limit = get_settings().max_message_length
        if len(value) > limit:
            raise ValueError(f"Message must be at most {limit} characters")
        return value


class ChatResponse(BaseModel):
    reply: str
    intent: str
    confidence: float
    is_fallback: bool
    is_follow_up: bool
    topic: str | None
    sources: list[str]
    time_sensitive: bool
    context: ChatContext
    latency_ms: float


class Suggestion(BaseModel):
    intent: str
    question: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    num_intents: int
    knowledge_retrieved_on: str | None
