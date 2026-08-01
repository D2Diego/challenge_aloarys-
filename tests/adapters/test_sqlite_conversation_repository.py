"""Tests for the in-memory SQLite conversation repository."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.adapters.sqlite.connection import open_connection
from app.adapters.sqlite.conversation_repository import SQLiteConversationRepository
from app.domain.conversation import ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk


@pytest.fixture
def conversation_repository():
    connection = open_connection(":memory:")
    yield SQLiteConversationRepository(connection)
    connection.close()


def _turn(conversation_id, question="question", pipeline="simple"):
    return ConversationTurn(
        conversation_id=conversation_id,
        pipeline=pipeline,
        question=question,
        answer="answer",
        sources=[
            FoundChunk(
                document_id=uuid4(),
                document_name="document.pdf",
                page=1,
                chunk_index=0,
                text="excerpt",
                score=0.9,
            )
        ],
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
        created_at=datetime.now(timezone.utc),
    )


def test_saves_turn_and_creates_retrievable_conversation(conversation_repository):
    conversation_id = uuid4()
    conversation_repository.save_turn(_turn(conversation_id))

    history = conversation_repository.get_history(conversation_id, limit=10)

    assert len(history) == 1
    assert history[0].question == "question"
    assert history[0].sources[0].text == "excerpt"
    assert history[0].usage.prompt_tokens == 10


def test_history_respects_limit_and_chronological_order(conversation_repository):
    conversation_id = uuid4()
    for index in range(3):
        conversation_repository.save_turn(
            _turn(conversation_id, question=f"question {index}")
        )

    history = conversation_repository.get_history(conversation_id, limit=2)

    assert [turn.question for turn in history] == ["question 1", "question 2"]


def test_lists_conversations_by_recent_update_and_counts_turns(
    conversation_repository,
):
    conversation_a, conversation_b = uuid4(), uuid4()
    conversation_repository.save_turn(_turn(conversation_a))
    conversation_repository.save_turn(_turn(conversation_b))
    conversation_repository.save_turn(_turn(conversation_b))

    conversations = conversation_repository.list_conversations()

    assert conversations[0].id == conversation_b
    assert conversations[0].total_turns == 2
    assert conversations[1].id == conversation_a
    assert conversations[1].total_turns == 1


def test_returns_none_for_missing_conversation(conversation_repository):
    assert conversation_repository.get_conversation(uuid4()) is None


def test_deletes_conversation_and_turns_in_cascade(conversation_repository):
    conversation_id = uuid4()
    conversation_repository.save_turn(_turn(conversation_id))

    conversation_repository.delete_conversation(conversation_id)

    assert conversation_repository.get_conversation(conversation_id) is None
    assert conversation_repository.get_history(conversation_id, limit=10) == []


def test_deleting_missing_conversation_is_safe(conversation_repository):
    conversation_repository.delete_conversation(uuid4())
