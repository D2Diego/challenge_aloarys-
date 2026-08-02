"""Tests for grounded prompt construction."""

from datetime import datetime, timezone
from uuid import uuid4

from app.domain.conversation import ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk
from app.domain.prompts import build_prompt


def _chunk(text: str, index: int) -> FoundChunk:
    return FoundChunk(
        document_id=uuid4(),
        document_name="document.pdf",
        page=None,
        chunk_index=index,
        text=text,
        score=0.9,
    )


def _turn(question: str, answer: str) -> ConversationTurn:
    return ConversationTurn(
        conversation_id=uuid4(),
        question=question,
        answer=answer,
        sources=[],
        usage=TokenUsage(0, 0),
        created_at=datetime.now(timezone.utc),
    )


def test_includes_question_and_numbered_chunks():
    chunks = [
        _chunk("The warranty lasts 12 months.", 0),
        _chunk("Returns are accepted within 7 days.", 1),
    ]

    prompt = build_prompt("How long is the warranty?", chunks)

    assert "How long is the warranty?" in prompt
    assert "[Source 1]" in prompt
    assert "The warranty lasts 12 months." in prompt
    assert "[Source 2]" in prompt
    assert "Returns are accepted within 7 days." in prompt


def test_handles_empty_chunk_list():
    prompt = build_prompt("Any question", [])
    assert "Any question" in prompt


def test_omits_history_section_when_history_is_absent():
    prompt = build_prompt("Current question", [_chunk("Relevant text", 0)])
    assert "Conversation history" not in prompt


def test_includes_previous_questions_and_answers_from_history():
    history = [_turn("Previous question", "Previous answer")]
    prompt = build_prompt(
        "Current question",
        [_chunk("Relevant text", 0)],
        history,
    )

    assert "Conversation history" in prompt
    assert "Previous question" in prompt
    assert "Previous answer" in prompt
    assert "Current question" in prompt
