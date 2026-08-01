from uuid import uuid4

from app.domain.conversation import TokenUsage
from app.services.conversation_history import get_history_safely, save_turn_safely


class _FakeRepository:
    def __init__(self):
        self.saved_turns = []
        self.should_fail = False

    def save_turn(self, turn):
        if self.should_fail:
            raise RuntimeError("disk full")
        self.saved_turns.append(turn)

    def get_history(self, conversation_id, limit):
        if self.should_fail:
            raise RuntimeError("database unavailable")
        return self.saved_turns


def test_returns_empty_history_without_repository_or_conversation_id():
    assert get_history_safely(None, uuid4(), 5) == []
    assert get_history_safely(_FakeRepository(), None, 5) == []


def test_returns_empty_history_when_repository_fails():
    repository = _FakeRepository()
    repository.should_fail = True

    assert get_history_safely(repository, uuid4(), 5) == []


def test_does_not_save_without_repository_or_conversation_id():
    repository = _FakeRepository()

    save_turn_safely(None, uuid4(), "simple", "q", "a", [], TokenUsage(0, 0))
    save_turn_safely(repository, None, "simple", "q", "a", [], TokenUsage(0, 0))

    assert repository.saved_turns == []


def test_saves_conversation_turn():
    repository = _FakeRepository()
    conversation_id = uuid4()

    save_turn_safely(
        repository,
        conversation_id,
        "agent",
        "question",
        "answer",
        [],
        TokenUsage(10, 5),
    )

    assert len(repository.saved_turns) == 1
    turn = repository.saved_turns[0]
    assert turn.conversation_id == conversation_id
    assert turn.pipeline == "agent"
    assert turn.usage.prompt_tokens == 10


def test_does_not_propagate_repository_write_failure():
    repository = _FakeRepository()
    repository.should_fail = True

    save_turn_safely(
        repository,
        uuid4(),
        "simple",
        "question",
        "answer",
        [],
        TokenUsage(0, 0),
    )
