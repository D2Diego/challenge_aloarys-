"""Mapping between application results and transport contracts."""

from dataclasses import asdict

from app.api.schemas import DocumentResponse, QueryResponse, Source
from app.domain.entities import Document
from app.services.query_service import (
    QueryCompletedEvent,
    QueryResult,
    QueryStreamEvent,
    QueryTokenEvent,
)
from app.services.sources import QuerySource


def to_document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(**asdict(document))


def to_source_response(source: QuerySource) -> Source:
    return Source(**asdict(source))


def to_query_response(result: QueryResult) -> QueryResponse:
    return QueryResponse(
        answer=result.answer,
        sources=[to_source_response(source) for source in result.sources],
    )


def to_stream_payload(event: QueryStreamEvent) -> dict:
    if isinstance(event, QueryTokenEvent):
        return {"type": event.type, "text": event.text}
    if isinstance(event, QueryCompletedEvent):
        return {
            "type": event.type,
            "answer": event.answer,
            "sources": [
                to_source_response(source).model_dump(mode="json")
                for source in event.sources
            ],
        }
    raise TypeError(f"Unknown query event: {type(event)!r}")
