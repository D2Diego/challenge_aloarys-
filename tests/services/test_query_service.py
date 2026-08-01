from datetime import datetime, timezone
from uuid import uuid4

from app.domain.conversation import ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk
from app.ports.llm import LLMResponse, LLMTextChunk, LLMUsageChunk
from app.services.query_service import QueryService


class _FakeSearch:
    def __init__(self, results):
        self.results = results
        self.last_call = None

    def search_chunks(
        self,
        question_embedding,
        *,
        top_k,
        min_score,
        document_ids,
    ):
        self.last_call = (question_embedding, top_k, min_score, document_ids)
        return self.results


class _FakeEmbeddings:
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


class _FakeLLM:
    def __init__(self, answer):
        self.answer = answer
        self.last_prompt = None

    def generate_response(self, prompt):
        self.last_prompt = prompt
        return LLMResponse(
            text=self.answer,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
        )

    async def generate_response_stream(self, prompt):
        raise NotImplementedError
        yield


class _FakeConversationRepository:
    def __init__(self):
        self.saved_turns = []
        self.last_limit = None

    def save_turn(self, turn):
        self.saved_turns.append(turn)

    def get_history(self, conversation_id, limit):
        self.last_limit = limit
        return self.saved_turns


def _chunk(document_id, text, score):
    return FoundChunk(
        document_id=document_id,
        document_name="document.pdf",
        page=1,
        chunk_index=0,
        text=text,
        score=score,
    )


def test_returns_no_context_answer_without_calling_llm():
    llm = _FakeLLM("should not be called")

    result = QueryService(_FakeSearch([]), _FakeEmbeddings(), llm).answer_question(
        "Any question"
    )

    assert result.sources == []
    assert llm.last_prompt is None
    assert "could not find" in result.answer.lower()


def test_builds_sources_from_cited_chunks():
    document_id = uuid4()
    llm = _FakeLLM("The warranty lasts 12 months [Source 1].")

    result = QueryService(
        _FakeSearch([_chunk(document_id, "12-month warranty.", 0.9)]),
        _FakeEmbeddings(),
        llm,
    ).answer_question("What is the warranty period?", top_k=3, min_score=0.4)

    assert result.answer == "The warranty lasts 12 months [Source 1]."
    assert result.sources[0].document_id == document_id
    assert result.sources[0].score == 0.9
    assert "12-month warranty." in llm.last_prompt


def test_filters_uncited_sources():
    document_a, document_b = uuid4(), uuid4()

    result = QueryService(
        _FakeSearch(
            [
                _chunk(document_a, "Chunk A.", 0.9),
                _chunk(document_b, "Chunk B.", 0.8),
            ]
        ),
        _FakeEmbeddings(),
        _FakeLLM("Only chunk A is used [Source 1]."),
    ).answer_question("Question")

    assert [source.document_id for source in result.sources] == [document_a]


async def test_streams_tokens_and_completed_event():
    document_id = uuid4()

    class _StreamingLLM(_FakeLLM):
        async def generate_response_stream(self, prompt):
            self.last_prompt = prompt
            for text in ["The warranty ", "lasts 12 months ", "[Source 1]."]:
                yield LLMTextChunk(text=text)
            yield LLMUsageChunk(
                usage=TokenUsage(prompt_tokens=20, completion_tokens=10)
            )

    service = QueryService(
        _FakeSearch([_chunk(document_id, "12-month warranty.", 0.9)]),
        _FakeEmbeddings(),
        _StreamingLLM(""),
    )

    events = [event async for event in service.stream_answer("Warranty period?")]

    assert len([event for event in events if event.type == "token"]) == 3
    completed = next(event for event in events if event.type == "complete")
    assert completed.answer == "The warranty lasts 12 months [Source 1]."
    assert len(completed.sources) == 1


def test_does_not_save_turn_without_conversation_id():
    conversations = _FakeConversationRepository()
    document_id = uuid4()

    QueryService(
        _FakeSearch([_chunk(document_id, "text", 0.9)]),
        _FakeEmbeddings(),
        _FakeLLM("answer [Source 1]."),
        conversation_repository=conversations,
    ).answer_question("question")

    assert conversations.saved_turns == []


def test_saves_turn_with_conversation_id():
    conversations = _FakeConversationRepository()
    conversation_id = uuid4()
    document_id = uuid4()

    QueryService(
        _FakeSearch([_chunk(document_id, "text", 0.9)]),
        _FakeEmbeddings(),
        _FakeLLM("answer [Source 1]."),
        conversation_repository=conversations,
    ).answer_question("question", conversation_id=conversation_id)

    assert len(conversations.saved_turns) == 1
    turn = conversations.saved_turns[0]
    assert turn.pipeline == "simple"
    assert turn.question == "question"
    assert turn.sources[0].chunk_index == 0


def test_saves_zero_usage_when_no_relevant_chunk_exists():
    conversations = _FakeConversationRepository()

    QueryService(
        _FakeSearch([]),
        _FakeEmbeddings(),
        _FakeLLM("never called"),
        conversation_repository=conversations,
    ).answer_question("question", conversation_id=uuid4())

    assert len(conversations.saved_turns) == 1
    assert conversations.saved_turns[0].usage.prompt_tokens == 0


async def test_saves_streamed_turn_with_usage():
    conversations = _FakeConversationRepository()
    conversation_id = uuid4()
    document_id = uuid4()

    class _StreamingLLM(_FakeLLM):
        async def generate_response_stream(self, prompt):
            yield LLMTextChunk(text="answer ")
            yield LLMTextChunk(text="[Source 1].")
            yield LLMUsageChunk(
                usage=TokenUsage(prompt_tokens=7, completion_tokens=3)
            )

    service = QueryService(
        _FakeSearch([_chunk(document_id, "text", 0.9)]),
        _FakeEmbeddings(),
        _StreamingLLM(""),
        conversation_repository=conversations,
    )

    events = [
        event
        async for event in service.stream_answer(
            "question",
            conversation_id=conversation_id,
        )
    ]

    assert len(conversations.saved_turns) == 1
    assert conversations.saved_turns[0].usage.prompt_tokens == 7
    assert events[-1].type == "complete"


def test_includes_previous_history_in_prompt():
    conversations = _FakeConversationRepository()
    conversation_id = uuid4()
    conversations.saved_turns.append(
        ConversationTurn(
            conversation_id=conversation_id,
            pipeline="simple",
            question="Previous question",
            answer="Previous answer",
            sources=[],
            usage=TokenUsage(0, 0),
            created_at=datetime.now(timezone.utc),
        )
    )
    llm = _FakeLLM("answer [Source 1].")

    QueryService(
        _FakeSearch([_chunk(uuid4(), "text", 0.9)]),
        _FakeEmbeddings(),
        llm,
        conversation_repository=conversations,
        max_history_turns=3,
    ).answer_question("Current question", conversation_id=conversation_id)

    assert "Conversation history" in llm.last_prompt
    assert "Previous question" in llm.last_prompt
    assert "Previous answer" in llm.last_prompt
    assert conversations.last_limit == 3


async def test_includes_previous_history_in_streaming_prompt():
    conversations = _FakeConversationRepository()
    conversation_id = uuid4()
    conversations.saved_turns.append(
        ConversationTurn(
            conversation_id=conversation_id,
            pipeline="simple",
            question="Previous streaming question",
            answer="Previous streaming answer",
            sources=[],
            usage=TokenUsage(0, 0),
            created_at=datetime.now(timezone.utc),
        )
    )

    class _StreamingLLM(_FakeLLM):
        async def generate_response_stream(self, prompt):
            self.last_prompt = prompt
            yield LLMTextChunk(text="answer [Source 1].")
            yield LLMUsageChunk(
                usage=TokenUsage(prompt_tokens=1, completion_tokens=1)
            )

    llm = _StreamingLLM("")
    service = QueryService(
        _FakeSearch([_chunk(uuid4(), "text", 0.9)]),
        _FakeEmbeddings(),
        llm,
        conversation_repository=conversations,
    )

    _ = [
        event
        async for event in service.stream_answer(
            "Current question",
            conversation_id=conversation_id,
        )
    ]

    assert "Conversation history" in llm.last_prompt
    assert "Previous streaming question" in llm.last_prompt
    assert "Previous streaming answer" in llm.last_prompt
