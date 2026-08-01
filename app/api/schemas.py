"""Pydantic contracts exposed by the HTTP and WebSocket API."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.domain.entities import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    id: UUID
    name: str
    document_type: DocumentType
    status: DocumentStatus
    ingested_at: datetime
    total_chunks: int | None = None
    error: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    limit: int


class QueryRequest(BaseModel):
    question: str
    document_ids: list[UUID] | None = None
    top_k: int | None = None
    conversation_id: UUID | None = None


class Source(BaseModel):
    document_id: UUID
    document_name: str
    page: int | None = None
    excerpt: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]


class DependencyStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


class HealthResponse(BaseModel):
    status: DependencyStatus
    dependencies: dict[str, DependencyStatus]


class StatusResponse(BaseModel):
    total_documents: int
    uptime_seconds: float


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class ConversationResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    total_turns: int


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


class ConversationTurnResponse(BaseModel):
    pipeline: Literal["simple", "agent"]
    question: str
    answer: str
    sources: list[Source]
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    turns: list[ConversationTurnResponse]
