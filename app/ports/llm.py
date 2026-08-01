from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from app.domain.conversation import TokenUsage


@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: TokenUsage


@dataclass(frozen=True)
class LLMTextChunk:
    text: str


@dataclass(frozen=True)
class LLMUsageChunk:
    usage: TokenUsage


LLMStreamChunk = LLMTextChunk | LLMUsageChunk


class LLMPort(Protocol):
    def generate_response(self, prompt: str) -> LLMResponse: ...

    def generate_response_stream(self, prompt: str) -> AsyncIterator[LLMStreamChunk]: ...
