"""Optional Pydantic AI integration test against a running Ollama instance."""

import asyncio
import os
from uuid import uuid4

import httpx
import pytest

from app.adapters.ai.pydantic_runtime import PydanticAgentRuntime
from app.domain.entities import FoundChunk
from app.services.retrieval_service import RetrievalService

pytestmark = pytest.mark.integration


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
        return [0.1] * 768


@pytest.mark.skipif(not os.environ.get("OLLAMA_URL"), reason="requires OLLAMA_URL")
def test_generates_cited_answer_with_real_ollama():
    chunk = FoundChunk(
        document_id=uuid4(),
        document_name="contract.pdf",
        page=2,
        chunk_index=0,
        text="The product warranty lasts 12 months.",
        score=0.9,
    )
    retrieval = RetrievalService(_FakeSearch([chunk]), _FakeEmbeddings())
    http_client = httpx.AsyncClient(timeout=120.0)
    runtime = PydanticAgentRuntime.for_ollama(
        retrieval,
        ollama_url=os.environ["OLLAMA_URL"],
        model=os.environ.get("LLM_MODEL", "qwen2.5:7b-instruct"),
        min_score=0.5,
        http_client=http_client,
    )
    try:
        result = runtime.run(
            "What is the product warranty?",
            initial_context=[chunk],
            document_ids=None,
        )
    finally:
        asyncio.run(http_client.aclose())

    assert "[Source 1]" in result.answer
    assert len(result.sources) == 1
