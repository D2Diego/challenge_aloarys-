from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from app.domain.conversation import ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk


@dataclass(frozen=True)
class AgentRunResult:
    answer: str
    sources: list[FoundChunk]
    usage: TokenUsage


@dataclass(frozen=True)
class AgentTextChunk:
    text: str


@dataclass(frozen=True)
class AgentCompletedChunk:
    answer: str
    sources: list[FoundChunk]
    usage: TokenUsage


AgentStreamEvent = AgentTextChunk | AgentCompletedChunk


class AgentRuntimePort(Protocol):
    def run(
        self,
        question: str,
        initial_context: list[FoundChunk],
        document_ids: list[str] | None,
        history: list[ConversationTurn] | None = None,
    ) -> AgentRunResult: ...

    def run_stream(
        self,
        question: str,
        initial_context: list[FoundChunk],
        document_ids: list[str] | None,
        history: list[ConversationTurn] | None = None,
    ) -> AsyncIterator[AgentStreamEvent]: ...
