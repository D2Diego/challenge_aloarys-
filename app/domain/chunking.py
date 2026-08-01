"""Semantic document chunking based on embedding distance."""

import re
from typing import Callable

MIN_CHUNK_TOKENS = 100
MAX_CHUNK_TOKENS = 450
BREAKPOINT_PERCENTILE = 95

_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú0-9])")

Embedder = Callable[[list[str]], list[list[float]]]
TokenCounter = Callable[[str], int]


def semantic_chunk(
    text: str,
    embedder: Embedder,
    token_counter: TokenCounter,
) -> list[str]:
    """Split text at semantic breakpoints and enforce chunk size limits."""
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return sentences

    embeddings = embedder(sentences)
    distances = _cosine_distances(embeddings)
    threshold = _percentile(distances, BREAKPOINT_PERCENTILE)

    groups: list[list[str]] = [[sentences[0]]]
    for sentence, distance in zip(sentences[1:], distances):
        if distance >= threshold:
            groups.append([sentence])
        else:
            groups[-1].append(sentence)

    chunks = [" ".join(group) for group in groups]
    return _apply_size_limits(chunks, token_counter)


def _split_sentences(text: str) -> list[str]:
    sentences = _SENTENCE_BOUNDARY_RE.split(text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _cosine_distances(embeddings: list[list[float]]) -> list[float]:
    distances = []
    for a, b in zip(embeddings, embeddings[1:]):
        dot = sum(x * y for x, y in zip(a, b))
        distances.append(1 - dot)
    return distances


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered_values = sorted(values)
    index = min(
        int(len(ordered_values) * percentile / 100),
        len(ordered_values) - 1,
    )
    return ordered_values[index]


def _apply_size_limits(chunks: list[str], token_counter: TokenCounter) -> list[str]:
    merged_chunks: list[str] = []
    for chunk in chunks:
        if merged_chunks and token_counter(merged_chunks[-1]) < MIN_CHUNK_TOKENS:
            merged_chunks[-1] = f"{merged_chunks[-1]} {chunk}"
        else:
            merged_chunks.append(chunk)

    result: list[str] = []
    for chunk in merged_chunks:
        result.extend(_split_oversized_chunk(chunk, token_counter))
    return result


def _split_oversized_chunk(chunk: str, token_counter: TokenCounter) -> list[str]:
    if token_counter(chunk) <= MAX_CHUNK_TOKENS:
        return [chunk]

    sentences = _split_sentences(chunk)
    parts: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and token_counter(candidate) > MAX_CHUNK_TOKENS:
            parts.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts
