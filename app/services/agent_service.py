"""Moderated question answering through an agent runtime."""

import logging
from collections.abc import AsyncIterator
from uuid import UUID

from app.domain.citations import extract_citations
from app.domain.conversation import TokenUsage
from app.ports.agent_runtime import AgentCompletedChunk, AgentRuntimePort, AgentTextChunk
from app.ports.conversation_repository import ConversationRepositoryPort
from app.ports.vector_search import MIN_SCORE, TOP_K_DEFAULT
from app.services.conversation_history import get_history_safely, save_turn_safely
from app.services.moderation_service import ModerationService
from app.services.query_service import (
    NO_CONTEXT_ANSWER,
    QueryCompletedEvent,
    QueryResult,
    QueryStreamEvent,
    QueryTokenEvent,
)
from app.services.sources import build_sources

logger = logging.getLogger("app")

AGENT_ERROR_ANSWER = "Unable to generate an answer. Please try again."


class AgentQueryService:
    def __init__(
        self,
        moderation: ModerationService,
        runtime: AgentRuntimePort,
        conversation_repository: ConversationRepositoryPort | None = None,
        max_history_turns: int = 5,
    ):
        self._moderation = moderation
        self._runtime = runtime
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
        moderation = self._moderation.evaluate(
            question,
            document_ids,
            top_k,
            min_score,
        )

        if not moderation.approved:
            save_turn_safely(
                self._conversation_repository,
                conversation_id,
                "agent",
                question,
                NO_CONTEXT_ANSWER,
                [],
                TokenUsage(0, 0),
            )
            return QueryResult(answer=NO_CONTEXT_ANSWER, sources=[])

        try:
            result = self._runtime.run(
                question,
                moderation.chunks,
                document_ids,
                history,
            )
        except Exception:
            logger.exception("agent_runtime_failed")
            save_turn_safely(
                self._conversation_repository,
                conversation_id,
                "agent",
                question,
                AGENT_ERROR_ANSWER,
                [],
                TokenUsage(0, 0),
            )
            return QueryResult(answer=AGENT_ERROR_ANSWER, sources=[])

        sources = build_sources(result.sources, extract_citations(result.answer))
        save_turn_safely(
            self._conversation_repository,
            conversation_id,
            "agent",
            question,
            result.answer,
            result.sources,
            result.usage,
        )
        return QueryResult(answer=result.answer, sources=sources)

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
        moderation = self._moderation.evaluate(
            question,
            document_ids,
            top_k,
            min_score,
        )

        if not moderation.approved:
            yield QueryCompletedEvent(answer=NO_CONTEXT_ANSWER, sources=[])
            save_turn_safely(
                self._conversation_repository,
                conversation_id,
                "agent",
                question,
                NO_CONTEXT_ANSWER,
                [],
                TokenUsage(0, 0),
            )
            return

        complete_text = ""
        accumulated_sources = []
        usage = TokenUsage(0, 0)
        try:
            async for event in self._runtime.run_stream(
                question,
                moderation.chunks,
                document_ids,
                history,
            ):
                if isinstance(event, AgentTextChunk):
                    complete_text += event.text
                    yield QueryTokenEvent(text=event.text)
                elif isinstance(event, AgentCompletedChunk):
                    complete_text = event.answer
                    accumulated_sources = event.sources
                    usage = event.usage
        except Exception:
            logger.exception("agent_runtime_stream_failed")
            yield QueryCompletedEvent(answer=AGENT_ERROR_ANSWER, sources=[])
            save_turn_safely(
                self._conversation_repository,
                conversation_id,
                "agent",
                question,
                AGENT_ERROR_ANSWER,
                [],
                TokenUsage(0, 0),
            )
            return

        sources = build_sources(
            accumulated_sources,
            extract_citations(complete_text),
        )
        yield QueryCompletedEvent(answer=complete_text, sources=sources)
        save_turn_safely(
            self._conversation_repository,
            conversation_id,
            "agent",
            question,
            complete_text,
            accumulated_sources,
            usage,
        )
