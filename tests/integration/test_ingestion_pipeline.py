from app.adapters.qdrant.document_repository import QdrantDocumentRepository
from app.adapters.qdrant.schema import EMBEDDING_DIM
from app.adapters.qdrant.vector_search import QdrantVectorSearch
from app.domain.entities import DocumentType
from app.services.processing_service import ProcessingService


def _vector() -> list[float]:
    return [1.0] + [0.0] * (EMBEDDING_DIM - 1)


class _DeterministicEmbeddings:
    def embed_query(self, text):
        return _vector()

    def embed_passage(self, text):
        return _vector()

    def embed_sentences(self, sentences):
        return [_vector() for _ in sentences]

    def count_tokens(self, text):
        return len(text.split())


class _UnusedPDFParser:
    def extract_pages(self, content):
        raise AssertionError("PDF parser should not be used for text ingestion")


def test_processed_document_becomes_searchable(qdrant_memory):
    repository = QdrantDocumentRepository(qdrant_memory)
    embeddings = _DeterministicEmbeddings()
    service = ProcessingService(repository, embeddings, _UnusedPDFParser())
    document = repository.create(
        name="contract.txt",
        document_type=DocumentType.TEXT,
    )

    service.process_text(
        str(document.id),
        "This contract may be cancelled at any time with 30 days notice.",
        "contract.txt",
    )
    results = QdrantVectorSearch(qdrant_memory).search_chunks(
        embeddings.embed_query("Can the contract be cancelled?"),
        top_k=1,
        min_score=0.5,
        document_ids=None,
    )

    assert len(results) == 1
    assert results[0].document_id == document.id
