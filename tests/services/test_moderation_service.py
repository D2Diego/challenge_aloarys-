from uuid import uuid4

from app.domain.entities import FoundChunk
from app.services.moderation_service import ModerationService
from app.services.retrieval_service import RetrievalService


class _FakeSearch:
    def __init__(self, results):
        self.results = results

    def search_chunks(
        self,
        question_embedding,
        *,
        top_k,
        min_score,
        document_ids,
    ):
        return self.results


class _FakeEmbeddings:
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


def _chunk() -> FoundChunk:
    return FoundChunk(
        document_id=uuid4(),
        document_name="document.pdf",
        page=1,
        chunk_index=0,
        text="excerpt",
        score=0.9,
    )


def test_rejects_question_when_retrieval_finds_nothing():
    retrieval = RetrievalService(_FakeSearch([]), _FakeEmbeddings())

    result = ModerationService(retrieval).evaluate(
        "question",
        document_ids=None,
        top_k=5,
        min_score=0.5,
    )

    assert result.approved is False
    assert result.chunks == []


def test_approves_question_and_returns_retrieved_chunks():
    chunks = [_chunk()]
    retrieval = RetrievalService(_FakeSearch(chunks), _FakeEmbeddings())

    result = ModerationService(retrieval).evaluate(
        "question",
        document_ids=None,
        top_k=5,
        min_score=0.5,
    )

    assert result.approved is True
    assert result.chunks == chunks
