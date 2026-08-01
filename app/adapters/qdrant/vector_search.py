"""Qdrant-backed vector search adapter."""

import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.adapters.qdrant.schema import QDRANT_COLLECTION, RecordType
from app.domain.entities import FoundChunk


class QdrantVectorSearch:
    def __init__(self, client: QdrantClient):
        self._client = client

    def search_chunks(
        self,
        question_embedding: list[float],
        *,
        top_k: int,
        min_score: float,
        document_ids: list[str] | None,
    ) -> list[FoundChunk]:
        conditions = [
            qmodels.FieldCondition(
                key="record_type",
                match=qmodels.MatchValue(value=RecordType.CHUNK.value),
            )
        ]
        if document_ids is not None:
            conditions.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchAny(any=document_ids),
                )
            )

        response = self._client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=question_embedding,
            query_filter=qmodels.Filter(must=conditions),
            limit=top_k,
            score_threshold=min_score,
        )
        return [
            FoundChunk(
                document_id=uuid.UUID(point.payload["document_id"]),
                document_name=point.payload["document_name"],
                page=point.payload.get("page"),
                chunk_index=point.payload["chunk_index"],
                text=point.payload["text"],
                score=point.score,
            )
            for point in response.points
        ]
