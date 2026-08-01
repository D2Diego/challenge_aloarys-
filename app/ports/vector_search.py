from typing import Protocol

from app.domain.entities import FoundChunk

TOP_K_DEFAULT = 5
MIN_SCORE = 0.5


class VectorSearchPort(Protocol):
    def search_chunks(
        self,
        question_embedding: list[float],
        *,
        top_k: int,
        min_score: float,
        document_ids: list[str] | None,
    ) -> list[FoundChunk]: ...
