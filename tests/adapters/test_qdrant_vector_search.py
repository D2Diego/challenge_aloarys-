import uuid

from app.adapters.qdrant.schema import EMBEDDING_DIM
from app.adapters.qdrant.vector_search import QdrantVectorSearch
from tests.conftest import insert_chunk


def _vector(first: float, second: float) -> list[float]:
    return [first, second] + [0.0] * (EMBEDDING_DIM - 2)


def test_returns_most_similar_chunk(qdrant_memory):
    closest_document = uuid.uuid4()
    insert_chunk(
        qdrant_memory,
        document_id=closest_document,
        document_name="policy.pdf",
        text="The warranty lasts 12 months.",
        vector=_vector(1.0, 0.0),
    )
    insert_chunk(
        qdrant_memory,
        document_id=uuid.uuid4(),
        document_name="policy.pdf",
        text="Returns are accepted within 7 days.",
        vector=_vector(0.0, 1.0),
    )

    results = QdrantVectorSearch(qdrant_memory).search_chunks(
        _vector(1.0, 0.0),
        top_k=1,
        min_score=0.5,
        document_ids=None,
    )

    assert len(results) == 1
    assert results[0].document_id == closest_document


def test_filters_search_by_document_ids(qdrant_memory):
    document_a = uuid.uuid4()
    document_b = uuid.uuid4()
    for document_id in (document_a, document_b):
        insert_chunk(
            qdrant_memory,
            document_id=document_id,
            document_name=f"{document_id}.pdf",
            text="The warranty lasts 12 months.",
            vector=_vector(1.0, 0.0),
        )

    results = QdrantVectorSearch(qdrant_memory).search_chunks(
        _vector(1.0, 0.0),
        top_k=5,
        min_score=0.5,
        document_ids=[str(document_a)],
    )

    assert len(results) == 1
    assert results[0].document_id == document_a


def test_empty_document_filter_returns_nothing(qdrant_memory):
    insert_chunk(
        qdrant_memory,
        document_id=uuid.uuid4(),
        document_name="document.pdf",
        text="The warranty lasts 12 months.",
        vector=_vector(1.0, 0.0),
    )

    results = QdrantVectorSearch(qdrant_memory).search_chunks(
        _vector(1.0, 0.0),
        top_k=5,
        min_score=0.5,
        document_ids=[],
    )

    assert results == []
