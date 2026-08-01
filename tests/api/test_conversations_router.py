from datetime import datetime, timezone
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_conversation_repository, get_current_user
from app.domain.conversation import Conversation, ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk
from app.main import app


class _FakeRepository:
    def __init__(self, conversations=None, turns_by_conversation=None):
        self.conversations = conversations or []
        self.turns_by_conversation = turns_by_conversation or {}
        self.deleted = []

    def list_conversations(self):
        return self.conversations

    def get_conversation(self, conversation_id):
        return next(
            (
                conversation
                for conversation in self.conversations
                if conversation.id == conversation_id
            ),
            None,
        )

    def get_history(self, conversation_id, limit):
        return self.turns_by_conversation.get(conversation_id, [])

    def delete_conversation(self, conversation_id):
        self.deleted.append(conversation_id)

    def save_turn(self, turn):
        raise NotImplementedError


async def _test_user():
    return "test-user"


def _override_auth_and_repository(repository):
    async def repository_override():
        return repository

    app.dependency_overrides[get_current_user] = _test_user
    app.dependency_overrides[get_conversation_repository] = repository_override


async def test_lists_conversations_in_repository_order():
    conversation = Conversation(
        id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        total_turns=2,
    )
    _override_auth_and_repository(_FakeRepository(conversations=[conversation]))
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/conversations")
        assert response.status_code == 200
        assert response.json()["conversations"][0]["total_turns"] == 2
    finally:
        app.dependency_overrides.clear()


async def test_returns_404_for_missing_conversation():
    _override_auth_and_repository(_FakeRepository())
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/conversations/{uuid4()}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_returns_conversation_turns():
    conversation_id = uuid4()
    conversation = Conversation(
        id=conversation_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        total_turns=1,
    )
    chunk = FoundChunk(
        document_id=uuid4(),
        document_name="manual.pdf",
        page=3,
        chunk_index=0,
        text="relevant document excerpt",
        score=0.87,
    )
    turn = ConversationTurn(
        conversation_id=conversation_id,
        pipeline="simple",
        question="question",
        answer="answer",
        sources=[chunk],
        usage=TokenUsage(10, 5),
        created_at=datetime.now(timezone.utc),
    )
    repository = _FakeRepository(
        conversations=[conversation],
        turns_by_conversation={conversation_id: [turn]},
    )
    _override_auth_and_repository(repository)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/conversations/{conversation_id}")
        assert response.status_code == 200
        body = response.json()
        assert len(body["turns"]) == 1
        assert body["turns"][0]["prompt_tokens"] == 10
        source = body["turns"][0]["sources"][0]
        assert source["excerpt"] == chunk.text
        assert source["document_id"] == str(chunk.document_id)
        assert source["document_name"] == chunk.document_name
        assert source["page"] == chunk.page
        assert source["score"] == chunk.score
    finally:
        app.dependency_overrides.clear()


async def test_delete_conversation_is_idempotent():
    repository = _FakeRepository()
    _override_auth_and_repository(repository)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first_response = await client.delete(f"/conversations/{uuid4()}")
            second_response = await client.delete(f"/conversations/{uuid4()}")
        assert first_response.status_code == 204
        assert second_response.status_code == 204
    finally:
        app.dependency_overrides.clear()
