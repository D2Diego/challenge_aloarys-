from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user, get_query_service
from app.main import app
from app.services.query_service import QueryResult
from app.services.sources import QuerySource


class _FakeQueryService:
    def answer_question(
        self,
        question,
        document_ids=None,
        top_k=5,
        min_score=0.5,
        conversation_id=None,
    ):
        return QueryResult(
            answer="Answer [Source 1].",
            sources=[
                QuerySource(
                    document_id=uuid4(),
                    document_name="document.pdf",
                    page=1,
                    excerpt="excerpt",
                    score=0.9,
                )
            ],
        )


async def _test_user():
    return "test-user"


async def _fake_query_service():
    return _FakeQueryService()


async def test_query_requires_authentication():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/query",
            json={"question": "hello"},
        )
    assert response.status_code == 401


async def test_query_returns_answer_and_sources():
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
        body = response.json()
        assert body["answer"] == "Answer [Source 1]."
        assert len(body["sources"]) == 1
    finally:
        app.dependency_overrides.clear()


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
    finally:
        app.dependency_overrides.clear()
