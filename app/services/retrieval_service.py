"""Reusable vector retrieval for document question answering."""

from app.domain.entities import FoundChunk
from app.ports.embeddings import EmbeddingPort
from app.ports.vector_search import VectorSearchPort


class RetrievalService:
    def __init__(self, search: VectorSearchPort, embeddings: EmbeddingPort):
        self._search = search
        self._embeddings = embeddings

    def retrieve(
        self,
        question: str,
        document_ids: list[str] | None,
        top_k: int,
        min_score: float,
    ) -> list[FoundChunk]:
        embedding = self._embeddings.embed_query(question)
        return self._search.search_chunks(
            embedding,
            top_k=top_k,
            min_score=min_score,
            document_ids=document_ids,
        )
