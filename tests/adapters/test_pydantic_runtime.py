"""Tests for Pydantic AI tool wiring and source accumulation."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from app.adapters.ai.pydantic_runtime import (
    PydanticAgentRuntime,
    _AgentDependencies,
    _intersect_document_ids,
)
from app.domain.conversation import ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk
from app.ports.agent_runtime import AgentCompletedChunk, AgentTextChunk
from app.services.retrieval_service import RetrievalService


class _FakeSearch:
    def __init__(self, results):
        self.results = results
        self.calls = 0

    def search_chunks(
        self,
        question_embedding,
        *,
        top_k,
        min_score,
        document_ids,
    ):
        self.calls += 1
        return self.results


class _FakeEmbeddings:
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


def _chunk(text):
    return FoundChunk(
        document_id=uuid4(),
        document_name="document.pdf",
        page=1,
        chunk_index=0,
        text=text,
        score=0.9,
    )


def _test_runtime(search_results):
    search = _FakeSearch(search_results)
    retrieval = RetrievalService(search, _FakeEmbeddings())
    agent = Agent(
        TestModel(call_tools=["search_documents"]),
        deps_type=_AgentDependencies,
    )
    runtime = PydanticAgentRuntime(
        agent,
        retrieval,
        min_score=0.5,
        max_tool_calls=3,
    )
    return runtime, search


def test_run_calls_tool_and_accumulates_new_sources():
    runtime, search = _test_runtime([_chunk("new excerpt")])

    result = runtime.run("question", initial_context=[], document_ids=None)

    assert search.calls == 1
    assert len(result.sources) == 1
    assert result.sources[0].text == "new excerpt"


def test_run_deduplicates_initial_context_source():
    initial_chunk = _chunk("existing excerpt")
    runtime, _ = _test_runtime([initial_chunk])

    result = runtime.run(
        "question",
        initial_context=[initial_chunk],
        document_ids=None,
    )

    assert len(result.sources) == 1


async def test_streams_text_and_completed_event_with_sources():
    runtime, search = _test_runtime([_chunk("streamed excerpt")])

    events = [
        event
        async for event in runtime.run_stream(
            "question",
            initial_context=[],
            document_ids=None,
        )
    ]

    assert search.calls == 1
    assert any(isinstance(event, AgentTextChunk) for event in events)
    assert isinstance(events[-1], AgentCompletedChunk)
    assert len(events[-1].sources) == 1
    assert events[-1].sources[0].text == "streamed excerpt"


class _SequentialSearch:
    def __init__(self, batches: list[list[FoundChunk]]):
        self._batches = batches
        self.calls = 0

    def search_chunks(
        self,
        question_embedding,
        *,
        top_k,
        min_score,
        document_ids,
    ):
        result = self._batches[self.calls]
        self.calls += 1
        return result


def _count_tool_returns(messages: list[ModelMessage]) -> int:
    total = 0
    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if (
                    isinstance(part, ToolReturnPart)
                    and part.tool_name == "search_documents"
                ):
                    total += 1
    return total


def test_run_accumulates_sources_from_multiple_tool_calls():
    first_chunk = _chunk("first batch")
    second_chunk = FoundChunk(
        document_id=uuid4(),
        document_name="other.pdf",
        page=2,
        chunk_index=1,
        text="second batch",
        score=0.8,
    )
    search = _SequentialSearch([[first_chunk], [second_chunk]])
    retrieval = RetrievalService(search, _FakeEmbeddings())

    async def model_function(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> ModelResponse:
        completed_calls = _count_tool_returns(messages)
        if completed_calls == 0:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="search_documents",
                        args={"question": "search 1"},
                    )
                ]
            )
        if completed_calls == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="search_documents",
                        args={"question": "search 2"},
                    )
                ]
            )
        return ModelResponse(
            parts=[TextPart(content="final answer [Source 1] [Source 2]")]
        )

    agent = Agent(FunctionModel(model_function), deps_type=_AgentDependencies)
    runtime = PydanticAgentRuntime(
        agent,
        retrieval,
        min_score=0.5,
        max_tool_calls=3,
    )

    result = runtime.run("question", initial_context=[], document_ids=None)

    assert search.calls == 2
    assert [source.text for source in result.sources] == [
        "first batch",
        "second batch",
    ]


def _turn(question: str, answer: str) -> ConversationTurn:
    return ConversationTurn(
        conversation_id=uuid4(),
        pipeline="agent",
        question=question,
        answer=answer,
        sources=[],
        usage=TokenUsage(prompt_tokens=0, completion_tokens=0),
        created_at=datetime.now(timezone.utc),
    )


def test_run_includes_history_in_initial_prompt():
    captured_prompt = {}

    async def model_function(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> ModelResponse:
        captured_prompt["text"] = messages[0].parts[0].content
        return ModelResponse(parts=[TextPart(content="answer")])

    retrieval = RetrievalService(_FakeSearch([]), _FakeEmbeddings())
    agent = Agent(FunctionModel(model_function), deps_type=_AgentDependencies)
    runtime = PydanticAgentRuntime(agent, retrieval, min_score=0.5)

    runtime.run(
        "Current question",
        initial_context=[],
        document_ids=None,
        history=[_turn("Previous question", "Previous answer")],
    )

    assert "Conversation history" in captured_prompt["text"]
    assert "Previous question" in captured_prompt["text"]
    assert "Previous answer" in captured_prompt["text"]


def test_run_omits_history_section_without_history():
    captured_prompt = {}

    async def model_function(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> ModelResponse:
        captured_prompt["text"] = messages[0].parts[0].content
        return ModelResponse(parts=[TextPart(content="answer")])

    retrieval = RetrievalService(_FakeSearch([]), _FakeEmbeddings())
    agent = Agent(FunctionModel(model_function), deps_type=_AgentDependencies)
    runtime = PydanticAgentRuntime(agent, retrieval, min_score=0.5)

    runtime.run("Current question", initial_context=[], document_ids=None)

    assert "Conversation history" not in captured_prompt["text"]


@pytest.mark.parametrize(
    ("authorized", "requested", "expected"),
    [
        (None, None, None),
        (None, ["A"], ["A"]),
        (["A", "B"], None, ["A", "B"]),
        (["A", "B"], ["B", "C"], ["B"]),
        (["A"], ["B"], []),
    ],
)
def test_intersects_document_ids(authorized, requested, expected):
    result = _intersect_document_ids(authorized, requested)

    if expected is None:
        assert result is None
    else:
        assert set(result) == set(expected)
