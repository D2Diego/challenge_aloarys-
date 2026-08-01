import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.adapters.qdrant.schema import EMBEDDING_DIM, QDRANT_COLLECTION


@pytest.fixture
def qdrant_memory() -> QdrantClient:
    """Provide an embedded in-memory Qdrant instance."""
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=qmodels.VectorParams(
            size=EMBEDDING_DIM,
            distance=qmodels.Distance.COSINE,
        ),
    )
    return client


def insert_chunk(
    client: QdrantClient,
    *,
    document_id: uuid.UUID,
    document_name: str,
    text: str,
    vector: list[float],
    chunk_index: int = 0,
    page: int | None = None,
) -> str:
    point_id = str(uuid.uuid4())
    client.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[
            qmodels.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "record_type": "chunk",
                    "document_id": str(document_id),
                    "document_name": document_name,
                    "page": page,
                    "chunk_index": chunk_index,
                    "text": text,
                },
            )
        ],
    )
    return point_id


def insert_document(
    client: QdrantClient,
    *,
    document_id: uuid.UUID,
    name: str,
    status: str = "ready",
) -> None:
    client.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[
            qmodels.PointStruct(
                id=str(document_id),
                vector=[0.0] * EMBEDDING_DIM,
                payload={
                    "record_type": "document",
                    "name": name,
                    "document_type": "text",
                    "status": status,
                    "ingested_at": "2026-07-31T00:00:00Z",
                },
            )
        ],
    )
