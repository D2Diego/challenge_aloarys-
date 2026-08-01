"""Multilingual E5 embedding adapter."""

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_MODEL_NAME = "intfloat/multilingual-e5-base"


@lru_cache(maxsize=1)
def _get_model() -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


class E5Embeddings:
    def embed_query(self, text: str) -> list[float]:
        return _get_model().encode(
            f"query: {text}",
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    def embed_passage(self, text: str) -> list[float]:
        return _get_model().encode(
            f"passage: {text}",
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    def embed_sentences(self, sentences: list[str]) -> list[list[float]]:
        return _get_model().encode(
            sentences,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    def count_tokens(self, text: str) -> int:
        return len(_get_model().tokenizer.encode(text, add_special_tokens=True))
