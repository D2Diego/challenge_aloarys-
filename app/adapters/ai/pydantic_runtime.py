"""Pydantic AI orchestration runtime with document search tooling."""

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.usage import UsageLimits

from app.domain.conversation import ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk
from app.ports.agent_runtime import (
    AgentCompletedChunk,
    AgentRunResult,
    AgentStreamEvent,
    AgentTextChunk,
)
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger("app")

AGENT_INSTRUCTIONS = """Answer questions exclusively from the excerpts supplied as initial context or returned by the search_documents tool. Never use prior or external knowledge.

Requirements:
1. Use only information present in the numbered [Source N] excerpts.
2. Cite every claim using the exact format "[Source N]".
3. If the initial context is insufficient, call search_documents with a reformulated question before giving up.
4. If the search still finds nothing relevant, state that the information was not found in the documents. Do not invent an answer.
5. Respond directly and concisely in English."""


class SearchDocumentsArgs(BaseModel):
    question: str
    document_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class _SourceAccumulator:
    """Maintain stable source numbering across all tool calls in one run."""

    def __init__(self, initial_chunks: list[FoundChunk]):
        self._chunks: list[FoundChunk] = []
        self._indexes: dict[tuple[UUID, int], int] = {}
        for chunk in initial_chunks:
            self._add(chunk)

    def _add(self, chunk: FoundChunk) -> int:
        key = (chunk.document_id, chunk.chunk_index)
        if key in self._indexes:
            return self._indexes[key]
        self._chunks.append(chunk)
        index = len(self._chunks)
        self._indexes[key] = index
        return index

    def add_and_label(
        self,
        chunks: list[FoundChunk],
    ) -> list[tuple[int, FoundChunk]]:
        return [(self._add(chunk), chunk) for chunk in chunks]

    @property
    def chunks(self) -> list[FoundChunk]:
        return list(self._chunks)


@dataclass
class _AgentDependencies:
    retrieval: RetrievalService
    authorized_document_ids: list[str] | None
    min_score: float
    accumulator: _SourceAccumulator


def _intersect_document_ids(
    authorized: list[str] | None,
    requested: list[str] | None,
) -> list[str] | None:
    if authorized is None:
        return requested
    if requested is None:
        return authorized
    return list(set(authorized) & set(requested))


def _format_tool_result(labeled: list[tuple[int, FoundChunk]]) -> str:
    if not labeled:
        return "No excerpts were found for this search."
    return "\n\n".join(
        f"[Source {index}]\n{chunk.text}" for index, chunk in labeled
    )


def _build_initial_prompt(
    question: str,
    initial_chunks: list[FoundChunk],
    history: list[ConversationTurn] | None = None,
) -> str:
    if initial_chunks:
        context = "\n\n".join(
            f"[Source {index}]\n{chunk.text}"
            for index, chunk in enumerate(initial_chunks, start=1)
        )
    else:
        context = "No excerpts are available in the initial context."

    history_section = ""
    if history:
        history_text = "\n\n".join(
            f"Previous question: {turn.question}\nPrevious answer: {turn.answer}"
            for turn in history
        )
        history_section = (
            "Conversation history, ordered from oldest to newest:\n"
            f"{history_text}\n\n"
        )

    return (
        f"{history_section}Initial context:\n{context}\n\n"
        f"Question: {question}"
    )


class PydanticAgentRuntime:
    def __init__(
        self,
        agent: Agent,
        retrieval: RetrievalService,
        min_score: float,
        max_tool_calls: int = 3,
    ):
        self._agent = agent
        self._retrieval = retrieval
        self._min_score = min_score
        self._max_tool_calls = max_tool_calls
        self._agent.tool(self._search_documents, name="search_documents")

    @classmethod
    def for_ollama(
        cls,
        retrieval: RetrievalService,
        ollama_url: str,
        model: str,
        min_score: float,
        http_client: httpx.AsyncClient,
        max_tool_calls: int = 3,
    ) -> "PydanticAgentRuntime":
        provider = OllamaProvider(
            base_url=f"{ollama_url.rstrip('/')}/v1",
            http_client=http_client,
        )
        ollama_model = OllamaModel(model, provider=provider)
        agent = Agent(
            ollama_model,
            deps_type=_AgentDependencies,
            instructions=AGENT_INSTRUCTIONS,
        )
        return cls(agent, retrieval, min_score, max_tool_calls)

    async def _search_documents(
        self,
        context: RunContext[_AgentDependencies],
        args: SearchDocumentsArgs,
    ) -> str:
        started_at = time.monotonic()
        document_ids = _intersect_document_ids(
            context.deps.authorized_document_ids,
            args.document_ids,
        )
        chunks = context.deps.retrieval.retrieve(
            args.question,
            document_ids,
            args.top_k,
            context.deps.min_score,
        )
        labeled = context.deps.accumulator.add_and_label(chunks)
        logger.info(
            "agent_tool_called",
            extra={
                "tool": "search_documents",
                "question_length": len(args.question),
                "top_k": args.top_k,
                "duration_ms": round((time.monotonic() - started_at) * 1000, 2),
                "result_count": len(chunks),
            },
        )
        return _format_tool_result(labeled)

    def _build_dependencies(
        self,
        initial_context: list[FoundChunk],
        document_ids: list[str] | None,
    ) -> tuple[_AgentDependencies, _SourceAccumulator]:
        accumulator = _SourceAccumulator(initial_context)
        dependencies = _AgentDependencies(
            retrieval=self._retrieval,
            authorized_document_ids=document_ids,
            min_score=self._min_score,
            accumulator=accumulator,
        )
        return dependencies, accumulator

    def run(
        self,
        question: str,
        initial_context: list[FoundChunk],
        document_ids: list[str] | None,
        history: list[ConversationTurn] | None = None,
    ) -> AgentRunResult:
        dependencies, accumulator = self._build_dependencies(
            initial_context,
            document_ids,
        )
        prompt = _build_initial_prompt(question, accumulator.chunks, history)
        result = self._agent.run_sync(
            prompt,
            deps=dependencies,
            usage_limits=UsageLimits(tool_calls_limit=self._max_tool_calls),
        )
        usage = TokenUsage(
            prompt_tokens=result.usage.input_tokens,
            completion_tokens=result.usage.output_tokens,
        )
        return AgentRunResult(
            answer=result.output,
            sources=accumulator.chunks,
            usage=usage,
        )

    async def run_stream(
        self,
        question: str,
        initial_context: list[FoundChunk],
        document_ids: list[str] | None,
        history: list[ConversationTurn] | None = None,
    ) -> AsyncIterator[AgentStreamEvent]:
        dependencies, accumulator = self._build_dependencies(
            initial_context,
            document_ids,
        )
        prompt = _build_initial_prompt(question, accumulator.chunks, history)
        complete_text = ""
        async with self._agent.run_stream(
            prompt,
            deps=dependencies,
            usage_limits=UsageLimits(tool_calls_limit=self._max_tool_calls),
        ) as result:
            async for text in result.stream_text(delta=True):
                complete_text += text
                yield AgentTextChunk(text=text)
            usage = TokenUsage(
                prompt_tokens=result.usage.input_tokens,
                completion_tokens=result.usage.output_tokens,
            )
        yield AgentCompletedChunk(
            answer=complete_text,
            sources=accumulator.chunks,
            usage=usage,
        )
