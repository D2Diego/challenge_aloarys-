"""Deterministic moderation based on document retrieval results."""

from dataclasses import dataclass

from app.domain.entities import FoundChunk
from app.services.retrieval_service import RetrievalService


@dataclass(frozen=True)
class ModerationResult:
    approved: bool
    chunks: list[FoundChunk]


class ModerationService:
    def __init__(self, retrieval: RetrievalService):
        self._retrieval = retrieval

    def evaluate(
        self,
        question: str,
        document_ids: list[str] | None,
        top_k: int,
        min_score: float,
    ) -> ModerationResult:
        chunks = self._retrieval.retrieve(
            question,
            document_ids,
            top_k,
            min_score,
        )
        return ModerationResult(approved=bool(chunks), chunks=chunks)
