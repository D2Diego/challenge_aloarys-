"""Source mapping shared by query pipelines."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import FoundChunk


@dataclass(frozen=True)
class QuerySource:
    document_id: UUID
    document_name: str
    page: int | None
    excerpt: str
    score: float


def build_sources(
    chunks: list[FoundChunk],
    cited_indexes: set[int],
) -> list[QuerySource]:
    return [
        QuerySource(
            document_id=chunk.document_id,
            document_name=chunk.document_name,
            page=chunk.page,
            excerpt=chunk.text,
            score=chunk.score,
        )
        for index, chunk in enumerate(chunks, start=1)
        if not cited_indexes or index in cited_indexes
    ]
