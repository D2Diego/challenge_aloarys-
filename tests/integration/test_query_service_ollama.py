"""Optional end-to-end query test against a running Ollama instance."""

import os
import uuid

import pytest

from app.adapters.e5_embeddings import E5Embeddings
from app.adapters.ollama_llm import OllamaLLM
from app.adapters.qdrant.vector_search import QdrantVectorSearch
from app.services.query_service import QueryService
from tests.conftest import insert_chunk

pytestmark = pytest.mark.integration


@pytest.fixture
def ollama_url() -> str:
    url = os.environ.get("OLLAMA_URL")
    if not url:
        pytest.skip("OLLAMA_URL is not configured")
    return url


def test_generates_answer_with_citation(qdrant_memory, ollama_url):
    document_id = uuid.uuid4()
    embeddings = E5Embeddings()
    text = "The product warranty lasts 12 months from the purchase date."
    insert_chunk(
        qdrant_memory,
        document_id=document_id,
        document_name="policy.pdf",
        text=text,
        vector=embeddings.embed_passage(text),
    )
    service = QueryService(
        QdrantVectorSearch(qdrant_memory),
        embeddings,
        OllamaLLM(
            ollama_url,
            os.environ.get("LLM_MODEL", "qwen2.5:7b-instruct"),
        ),
    )

    result = service.answer_question("What is the product warranty period?")

    assert result.sources
    assert result.sources[0].document_id == document_id
