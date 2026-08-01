"""Qdrant-backed document and chunk repository."""

import uuid
from datetime import datetime, timezone

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.adapters.qdrant.schema import (
    EMBEDDING_DIM,
    QDRANT_COLLECTION,
    ChunkRecord,
    DocumentRecord,
    RecordType,
)
from app.domain.entities import ChunkToSave, Document, DocumentStatus, DocumentType


def _record_to_document(document_id: uuid.UUID, record: DocumentRecord) -> Document:
    return Document(
        id=document_id,
        name=record.name,
        document_type=record.document_type,
        status=record.status,
        ingested_at=record.ingested_at,
        total_chunks=record.total_chunks,
        error=record.error,
    )


class QdrantDocumentRepository:
    def __init__(self, client: QdrantClient):
        self._client = client

    def create(self, *, name: str, document_type: DocumentType) -> Document:
        document_id = uuid.uuid4()
        record = DocumentRecord(
            name=name,
            document_type=document_type,
            status=DocumentStatus.PROCESSING,
            ingested_at=datetime.now(timezone.utc),
        )
        self._client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[
                qmodels.PointStruct(
                    id=str(document_id),
                    vector=[0.0] * EMBEDDING_DIM,
                    payload=record.model_dump(mode="json"),
                )
            ],
        )
        return _record_to_document(document_id, record)

    def update_status(
        self,
        document_id: uuid.UUID,
        *,
        status: DocumentStatus,
        total_chunks: int | None = None,
        error: str | None = None,
    ) -> None:
        self._client.set_payload(
            collection_name=QDRANT_COLLECTION,
            points=[str(document_id)],
            payload={
                "status": status.value,
                "total_chunks": total_chunks,
                "error": error,
            },
        )

    def get(self, document_id: uuid.UUID) -> Document | None:
        points = self._client.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=[str(document_id)],
        )
        if not points:
            return None
        return _record_to_document(
            document_id,
            DocumentRecord(**points[0].payload),
        )

    def list_documents(
        self,
        *,
        page: int,
        limit: int,
        status: DocumentStatus | None = None,
    ) -> tuple[list[Document], int]:
        conditions = [
            qmodels.FieldCondition(
                key="record_type",
                match=qmodels.MatchValue(value=RecordType.DOCUMENT.value),
            )
        ]
        if status is not None:
            conditions.append(
                qmodels.FieldCondition(
                    key="status",
                    match=qmodels.MatchValue(value=status.value),
                )
            )
        query_filter = qmodels.Filter(must=conditions)
        total = self._client.count(
            collection_name=QDRANT_COLLECTION,
            count_filter=query_filter,
        ).count

        all_points: list = []
        next_offset = None
        while True:
            points, next_offset = self._client.scroll(
                collection_name=QDRANT_COLLECTION,
                scroll_filter=query_filter,
                limit=100,
                offset=next_offset,
            )
            all_points.extend(points)
            if next_offset is None:
                break

        all_points.sort(key=lambda point: point.payload["ingested_at"])
        start = (page - 1) * limit
        page_points = all_points[start : start + limit]
        documents = [
            _record_to_document(
                uuid.UUID(point.id),
                DocumentRecord(**point.payload),
            )
            for point in page_points
        ]
        return documents, total

    def delete(self, document_id: uuid.UUID) -> bool:
        if self.get(document_id) is None:
            return False

        self._client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=qmodels.PointIdsList(points=[str(document_id)]),
        )
        self._client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )
        return True

    def save_chunks(
        self,
        *,
        document_id: uuid.UUID,
        document_name: str,
        chunks: list[ChunkToSave],
    ) -> int:
        points = [
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=chunk.embedding,
                payload=ChunkRecord(
                    document_id=document_id,
                    document_name=document_name,
                    page=chunk.page,
                    chunk_index=index,
                    text=chunk.text,
                ).model_dump(mode="json"),
            )
            for index, chunk in enumerate(chunks)
        ]
        if points:
            self._client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=points,
            )
        return len(points)

    def reconcile_stuck_processing(self) -> int:
        documents, _ = self.list_documents(
            page=1,
            limit=10_000,
            status=DocumentStatus.PROCESSING,
        )
        for document in documents:
            self.update_status(
                document.id,
                status=DocumentStatus.FAILED,
                error=(
                    "Ingestion was interrupted before completion. "
                    "Upload the document again."
                ),
            )
        return len(documents)

    def count(self) -> int:
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="record_type",
                    match=qmodels.MatchValue(value=RecordType.DOCUMENT.value),
                )
            ]
        )
        return self._client.count(
            collection_name=QDRANT_COLLECTION,
            count_filter=query_filter,
        ).count
