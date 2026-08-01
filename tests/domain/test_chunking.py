"""Tests for semantic chunking and chunk size limits."""

import app.domain.chunking as chunking_module
from app.domain.chunking import (
    MAX_CHUNK_TOKENS,
    MIN_CHUNK_TOKENS,
    _apply_size_limits,
    _split_oversized_chunk,
    semantic_chunk,
)

_VECTOR_BY_TOPIC = {
    "cat": [1.0, 0.0, 0.0],
    "dog": [0.98, 0.2, 0.0],
    "car": [0.0, 0.0, 1.0],
    "engine": [0.05, 0.0, 0.99],
}


def _fake_topic_embedder(sentences: list[str]) -> list[list[float]]:
    return [_VECTOR_BY_TOPIC[_topic(sentence)] for sentence in sentences]


def _topic(sentence: str) -> str:
    for word in _VECTOR_BY_TOPIC:
        if word in sentence:
            return word
    raise ValueError(f"test sentence has no known topic: {sentence!r}")


def _fake_token_counter(text: str) -> int:
    return len(text.split())


def test_splits_at_breakpoint_between_different_topics(monkeypatch):
    monkeypatch.setattr(chunking_module, "MIN_CHUNK_TOKENS", 1)

    text = (
        "The cat slept all day. The dog barked at the mail carrier. "
        "The car would not start this morning. The engine made a strange noise."
    )

    chunks = semantic_chunk(
        text,
        embedder=_fake_topic_embedder,
        token_counter=_fake_token_counter,
    )

    assert len(chunks) == 2
    assert "cat" in chunks[0] and "dog" in chunks[0]
    assert "car" in chunks[1] and "engine" in chunks[1]


def test_single_sentence_becomes_single_chunk():
    chunks = semantic_chunk(
        "There is only one sentence here.",
        embedder=_fake_topic_embedder,
        token_counter=_fake_token_counter,
    )
    assert chunks == ["There is only one sentence here."]


def test_merges_chunks_below_minimum_size_with_neighbor():
    short_chunk_1 = "Okay."
    short_chunk_2 = "Yes."
    long_chunk = "word " * 150

    result = _apply_size_limits(
        [short_chunk_1, short_chunk_2, long_chunk],
        _fake_token_counter,
    )

    assert len(result) == 1
    assert _fake_token_counter(result[0]) >= MIN_CHUNK_TOKENS


def test_splits_chunk_above_maximum_size():
    sentence = "The quick brown fox jumps over the lazy dog."
    oversized_chunk = " ".join([sentence] * 60)

    parts = _split_oversized_chunk(oversized_chunk, _fake_token_counter)

    assert len(parts) > 1
    assert all(_fake_token_counter(part) <= MAX_CHUNK_TOKENS for part in parts)
    assert sum(_fake_token_counter(part) for part in parts) == _fake_token_counter(
        oversized_chunk
    )
