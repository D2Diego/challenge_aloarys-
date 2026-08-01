from uuid import uuid4

from app.domain.entities import FoundChunk
from app.services.retrieval_service import RetrievalService


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
    def __init__(self):
        self.last_question = None

    def embed_query(self, text):
        self.last_question = text
        return [0.1, 0.2, 0.3]


def test_embeds_question_and_forwards_search_parameters():
    search = _FakeSearch(
        [
            FoundChunk(
                document_id=uuid4(),
                document_name="document.pdf",
                page=1,
                chunk_index=0,
                text="excerpt",
                score=0.9,
            )
        ]
    )
    embeddings = _FakeEmbeddings()

    result = RetrievalService(search, embeddings).retrieve(
        "What is the warranty period?",
        document_ids=["abc"],
        top_k=3,
        min_score=0.6,
    )

    assert embeddings.last_question == "What is the warranty period?"
    assert search.last_call == ([0.1, 0.2, 0.3], 3, 0.6, ["abc"])
    assert result == search.results
