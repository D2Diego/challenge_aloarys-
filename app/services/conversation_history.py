"""Failure-tolerant conversation history operations."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.domain.conversation import ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk
from app.ports.conversation_repository import ConversationRepositoryPort

logger = logging.getLogger("app")


def get_history_safely(
    repository: ConversationRepositoryPort | None,
    conversation_id: UUID | None,
    limit: int,
) -> list[ConversationTurn]:
    if repository is None or conversation_id is None:
        return []
    try:
        return repository.get_history(conversation_id, limit)
    except Exception:
        logger.warning("conversation_history_read_failed", exc_info=True)
        return []


def save_turn_safely(
    repository: ConversationRepositoryPort | None,
    conversation_id: UUID | None,
    question: str,
    answer: str,
    sources: list[FoundChunk],
    usage: TokenUsage,
) -> None:
    if repository is None or conversation_id is None:
        return
    try:
        repository.save_turn(
            ConversationTurn(
                conversation_id=conversation_id,
                question=question,
                answer=answer,
                sources=sources,
                usage=usage,
                created_at=datetime.now(timezone.utc),
            )
        )
    except Exception:
        logger.warning("conversation_turn_write_failed", exc_info=True)
