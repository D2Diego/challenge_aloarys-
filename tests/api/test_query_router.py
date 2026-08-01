from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user, get_query_service
from app.main import app
from app.services.query_service import QueryResult


class _FakeQueryService:
    def answer_question(
        self,
        question,
        document_ids=None,
        top_k=5,
        min_score=0.5,
        conversation_id=None,
    ):
        return QueryResult(answer="answer [Source 1].", sources=[])


async def _test_user():
    return "test-user"


async def _fake_query_service():
    return _FakeQueryService()


async def test_query_without_conversation_id():
    app.dependency_overrides[get_current_user] = _test_user
    app.dependency_overrides[get_query_service] = _fake_query_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/query",
                json={"question": "What is the warranty period?"},
            )
        assert response.status_code == 200
        assert response.json()["answer"] == "answer [Source 1]."
    finally:
        app.dependency_overrides.clear()


async def test_forwards_conversation_id_to_service():
    call = {}

    class _RecordingQueryService(_FakeQueryService):
        def answer_question(self, question, **kwargs):
            call.update(kwargs)
            return super().answer_question(question, **kwargs)

    conversation_id = uuid4()
    async def recording_query_service():
        return _RecordingQueryService()

    app.dependency_overrides[get_current_user] = _test_user
    app.dependency_overrides[get_query_service] = recording_query_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/query",
                json={
                    "question": "question",
                    "conversation_id": str(conversation_id),
                },
            )
        assert call["conversation_id"] == conversation_id
    finally:
        app.dependency_overrides.clear()
