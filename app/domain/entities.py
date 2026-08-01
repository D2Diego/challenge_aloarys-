"""Core domain entities with no infrastructure dependencies."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class DocumentType(str, Enum):
    PDF = "pdf"
    TEXT = "text"


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


@dataclass
class Document:
    id: UUID
    name: str
    type: DocumentType
    status: DocumentStatus
    ingested_at: datetime
    total_chunks: int | None = None
    error: str | None = None


@dataclass
class ChunkToSave:
    """Represent a document chunk ready for persistence."""

    text: str
    embedding: list[float]
    page: int | None = None


@dataclass
class FoundChunk:
    """Represent a document chunk returned by vector search."""

    document_id: UUID
    document_name: str
    page: int | None
    chunk_index: int
    text: str
    score: float
