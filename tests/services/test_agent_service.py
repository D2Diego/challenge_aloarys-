from datetime import datetime, timezone
from uuid import uuid4

from app.domain.conversation import ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk
from app.ports.agent_runtime import (
    AgentCompletedChunk,
    AgentRunResult,
    AgentTextChunk,
)
from app.services.agent_service import AGENT_ERROR_ANSWER, AgentQueryService
from app.services.moderation_service import ModerationService
from app.services.retrieval_service import RetrievalService


class _FakeSearch:
    def __init__(self, results):
        self.results = results

    def search_chunks(
        self,
        question_embedding,
        *,
        top_k,
        min_score,
        document_ids,
    ):
        return self.results


class _FakeEmbeddings:
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


class _FakeRuntime:
    def __init__(self, result):
        self.result = result
        self.last_call = None

    def run(self, question, initial_context, document_ids, history=None):
        self.last_call = (question, initial_context, document_ids, history)
        return self.result

    async def run_stream(
        self,
        question,
        initial_context,
        document_ids,
        history=None,
    ):
        raise NotImplementedError
        yield


class _RecordingStreamRuntime(_FakeRuntime):
    async def run_stream(
        self,
        question,
        initial_context,
        document_ids,
        history=None,
    ):
        self.last_call = (question, initial_context, document_ids, history)
        yield AgentCompletedChunk(
            answer=self.result.answer,
            sources=self.result.sources,
            usage=self.result.usage,
        )


class _FakeConversationRepository:
    def __init__(self):
        self.saved_turns = []
        self.last_limit = None

    def save_turn(self, turn):
        self.saved_turns.append(turn)

    def get_history(self, conversation_id, limit):
        self.last_limit = limit
        return list(self.saved_turns)


def _chunk(text="excerpt"):
    return FoundChunk(
        document_id=uuid4(),
        document_name="document.pdf",
        page=1,
        chunk_index=0,
        text=text,
        score=0.9,
    )


def _moderation(results):
    retrieval = RetrievalService(_FakeSearch(results), _FakeEmbeddings())
    return ModerationService(retrieval)


def _service(search_results, runtime_result):
    runtime = _FakeRuntime(runtime_result)
    return AgentQueryService(_moderation(search_results), runtime), runtime


def test_rejected_question_does_not_call_runtime():
    service, runtime = _service(
        [],
        AgentRunResult("never", [], TokenUsage(10, 5)),
    )

    result = service.answer_question("Any question")

    assert runtime.last_call is None
    assert result.sources == []
    assert "could not find" in result.answer.lower()


def test_approved_question_calls_runtime_with_initial_context():
    chunk = _chunk()
    runtime_result = AgentRunResult(
        answer="Answer with [Source 1].",
        sources=[chunk],
        usage=TokenUsage(10, 5),
    )
    service, runtime = _service([chunk], runtime_result)

    result = service.answer_question("question", top_k=3, min_score=0.5)

    assert runtime.last_call[0] == "question"
    assert runtime.last_call[1] == [chunk]
    assert result.answer == "Answer with [Source 1]."
    assert len(result.sources) == 1


def test_discards_citation_without_matching_source():
    chunk = _chunk()
    runtime_result = AgentRunResult(
        answer="Answer with [Source 2].",
        sources=[chunk],
        usage=TokenUsage(10, 5),
    )
    service, _ = _service([chunk], runtime_result)

    result = service.answer_question("question")

    assert result.sources == []


def test_returns_safe_answer_when_runtime_fails():
    class _FailingRuntime(_FakeRuntime):
        def run(self, question, initial_context, document_ids, history=None):
            raise RuntimeError("internal Ollama timeout")

    service = AgentQueryService(_moderation([_chunk()]), _FailingRuntime(None))

    result = service.answer_question("question")

    assert result.answer == AGENT_ERROR_ANSWER
    assert "timeout" not in result.answer.lower()
    assert result.sources == []


async def test_streams_tokens_and_completed_event():
    chunk = _chunk()

    class _StreamingRuntime(_FakeRuntime):
        async def run_stream(
            self,
            question,
            initial_context,
            document_ids,
            history=None,
        ):
            for text in ["Answer ", "with [Source 1]."]:
                yield AgentTextChunk(text=text)
            yield AgentCompletedChunk(
                answer="Answer with [Source 1].",
                sources=[chunk],
                usage=TokenUsage(10, 5),
            )

    service = AgentQueryService(
        _moderation([chunk]),
        _StreamingRuntime(None),
    )

    events = [event async for event in service.stream_answer("question")]

    assert len([event for event in events if event.type == "token"]) == 2
    completed = next(event for event in events if event.type == "complete")
    assert completed.answer == "Answer with [Source 1]."
    assert len(completed.sources) == 1


async def test_rejected_stream_does_not_call_runtime():
    service, runtime = _service([], None)

    events = [event async for event in service.stream_answer("question")]

    assert runtime.last_call is None
    assert len(events) == 1
    assert events[0].type == "complete"
    assert "could not find" in events[0].answer.lower()


async def test_returns_safe_stream_event_when_runtime_fails():
    class _FailingStreamRuntime(_FakeRuntime):
        async def run_stream(
            self,
            question,
            initial_context,
            document_ids,
            history=None,
        ):
            raise RuntimeError("internal Ollama timeout")
            yield

    service = AgentQueryService(
        _moderation([_chunk()]),
        _FailingStreamRuntime(None),
    )

    events = [event async for event in service.stream_answer("question")]

    assert len(events) == 1
    assert events[0].answer == AGENT_ERROR_ANSWER


def test_passes_empty_history_and_saves_first_conversation_turn():
    conversations = _FakeConversationRepository()
    conversation_id = uuid4()
    chunk = _chunk()
    runtime_result = AgentRunResult(
        answer="Answer [Source 1].",
        sources=[chunk],
        usage=TokenUsage(10, 5),
    )
    runtime = _FakeRuntime(runtime_result)
    service = AgentQueryService(
        _moderation([chunk]),
        runtime,
        conversation_repository=conversations,
    )

    service.answer_question("question", conversation_id=conversation_id)

    assert runtime.last_call[3] == []
    assert len(conversations.saved_turns) == 1
    assert conversations.saved_turns[0].pipeline == "agent"
    assert conversations.saved_turns[0].usage.prompt_tokens == 10
    assert conversations.saved_turns[0].sources[0].chunk_index == chunk.chunk_index


def test_passes_previous_history_to_runtime():
    conversations = _FakeConversationRepository()
    conversation_id = uuid4()
    conversations.saved_turns.append(
        ConversationTurn(
            conversation_id=conversation_id,
            pipeline="agent",
            question="Previous question",
            answer="Previous answer",
            sources=[],
            usage=TokenUsage(0, 0),
            created_at=datetime.now(timezone.utc),
        )
    )
    chunk = _chunk()
    runtime = _FakeRuntime(
        AgentRunResult(
            answer="Answer [Source 1].",
            sources=[chunk],
            usage=TokenUsage(10, 5),
        )
    )
    service = AgentQueryService(
        _moderation([chunk]),
        runtime,
        conversation_repository=conversations,
        max_history_turns=3,
    )

    service.answer_question("Current question", conversation_id=conversation_id)

    assert len(runtime.last_call[3]) == 1
    assert runtime.last_call[3][0].question == "Previous question"
    assert runtime.last_call[3][0].answer == "Previous answer"
    assert conversations.last_limit == 3


async def test_passes_previous_history_to_streaming_runtime():
    conversations = _FakeConversationRepository()
    conversation_id = uuid4()
    conversations.saved_turns.append(
        ConversationTurn(
            conversation_id=conversation_id,
            pipeline="agent",
            question="Previous streaming question",
            answer="Previous streaming answer",
            sources=[],
            usage=TokenUsage(0, 0),
            created_at=datetime.now(timezone.utc),
        )
    )
    chunk = _chunk()
    runtime = _RecordingStreamRuntime(
        AgentRunResult(
            answer="Answer [Source 1].",
            sources=[chunk],
            usage=TokenUsage(10, 5),
        )
    )
    service = AgentQueryService(
        _moderation([chunk]),
        runtime,
        conversation_repository=conversations,
        max_history_turns=3,
    )

    events = [
        event
        async for event in service.stream_answer(
            "Current question",
            conversation_id=conversation_id,
        )
    ]

    assert len(runtime.last_call[3]) == 1
    assert runtime.last_call[3][0].question == "Previous streaming question"
    assert runtime.last_call[3][0].answer == "Previous streaming answer"
    assert events[-1].type == "complete"
    assert conversations.last_limit == 3
