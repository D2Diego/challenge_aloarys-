"""Qdrant payload schemas for documents and chunks."""

import os
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from app.domain.entities import DocumentStatus, DocumentType

QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "documents")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "768"))


class RecordType(str, Enum):
    DOCUMENT = "document"
    CHUNK = "chunk"


class DocumentRecord(BaseModel):
    record_type: RecordType = RecordType.DOCUMENT
    name: str
    document_type: DocumentType
    status: DocumentStatus
    ingested_at: datetime
    total_chunks: int | None = None
    error: str | None = None


class ChunkRecord(BaseModel):
    record_type: RecordType = RecordType.CHUNK
    document_id: UUID
    document_name: str
    page: int | None = None
    chunk_index: int
    text: str
