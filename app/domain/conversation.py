"""Conversation and token usage domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.domain.entities import FoundChunk


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int


@dataclass(frozen=True)
class Conversation:
    id: UUID
    created_at: datetime
    updated_at: datetime
    total_turns: int


@dataclass(frozen=True)
class ConversationTurn:
    conversation_id: UUID
    pipeline: Literal["simple", "agent"]
    question: str
    answer: str
    sources: list[FoundChunk]
    usage: TokenUsage
    created_at: datetime
