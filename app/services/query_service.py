"""Grounded question answering with vector retrieval."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.domain.citations import extract_citations
from app.domain.conversation import TokenUsage
from app.domain.prompts import build_prompt
from app.ports.conversation_repository import ConversationRepositoryPort
from app.ports.embeddings import EmbeddingPort
from app.ports.llm import LLMPort, LLMTextChunk, LLMUsageChunk
from app.ports.vector_search import MIN_SCORE, TOP_K_DEFAULT, VectorSearchPort
from app.services.conversation_history import get_history_safely, save_turn_safely
from app.services.retrieval_service import RetrievalService
from app.services.sources import QuerySource, build_sources


@dataclass(frozen=True)
class QueryResult:
    answer: str
    sources: list[QuerySource]


@dataclass(frozen=True)
class QueryTokenEvent:
    text: str
    type: Literal["token"] = "token"


@dataclass(frozen=True)
class QueryCompletedEvent:
    answer: str
    sources: list[QuerySource]
    type: Literal["complete"] = "complete"


QueryStreamEvent = QueryTokenEvent | QueryCompletedEvent

NO_CONTEXT_ANSWER = (
    "I could not find relevant information in the documents to answer this question."
)


class QueryService:
    def __init__(
        self,
        search: VectorSearchPort,
        embeddings: EmbeddingPort,
        llm: LLMPort,
        conversation_repository: ConversationRepositoryPort | None = None,
        max_history_turns: int = 5,
    ):
        self._retrieval = RetrievalService(search, embeddings)
        self._llm = llm
        self._conversation_repository = conversation_repository
        self._max_history_turns = max_history_turns

    def answer_question(
        self,
        question: str,
        document_ids: list[str] | None = None,
        top_k: int = TOP_K_DEFAULT,
        min_score: float = MIN_SCORE,
        conversation_id: UUID | None = None,
    ) -> QueryResult:
        history = get_history_safely(
            self._conversation_repository,
            conversation_id,
            self._max_history_turns,
        )
        chunks = self._retrieval.retrieve(
            question,
            document_ids,
            top_k,
            min_score,
        )
        if not chunks:
            save_turn_safely(
                self._conversation_repository,
                conversation_id,
                "simple",
                question,
                NO_CONTEXT_ANSWER,
                [],
                TokenUsage(0, 0),
            )
            return QueryResult(answer=NO_CONTEXT_ANSWER, sources=[])

        llm_response = self._llm.generate_response(
            build_prompt(question, chunks, history)
        )
        sources = build_sources(chunks, extract_citations(llm_response.text))
        save_turn_safely(
            self._conversation_repository,
            conversation_id,
            "simple",
            question,
            llm_response.text,
            chunks,
            llm_response.usage,
        )
        return QueryResult(answer=llm_response.text, sources=sources)

    async def stream_answer(
        self,
        question: str,
        document_ids: list[str] | None = None,
        top_k: int = TOP_K_DEFAULT,
        min_score: float = MIN_SCORE,
        conversation_id: UUID | None = None,
    ) -> AsyncIterator[QueryStreamEvent]:
        history = get_history_safely(
            self._conversation_repository,
            conversation_id,
            self._max_history_turns,
        )
        chunks = self._retrieval.retrieve(
            question,
            document_ids,
            top_k,
            min_score,
        )
        if not chunks:
            yield QueryCompletedEvent(answer=NO_CONTEXT_ANSWER, sources=[])
            save_turn_safely(
                self._conversation_repository,
                conversation_id,
                "simple",
                question,
                NO_CONTEXT_ANSWER,
                [],
                TokenUsage(0, 0),
            )
            return

        complete_text = ""
        usage = TokenUsage(0, 0)
        prompt = build_prompt(question, chunks, history)
        async for chunk in self._llm.generate_response_stream(prompt):
            if isinstance(chunk, LLMTextChunk):
                complete_text += chunk.text
                yield QueryTokenEvent(text=chunk.text)
            elif isinstance(chunk, LLMUsageChunk):
                usage = chunk.usage

        sources = build_sources(chunks, extract_citations(complete_text))
        yield QueryCompletedEvent(answer=complete_text, sources=sources)
        save_turn_safely(
            self._conversation_repository,
            conversation_id,
            "simple",
            question,
            complete_text,
            chunks,
            usage,
        )
