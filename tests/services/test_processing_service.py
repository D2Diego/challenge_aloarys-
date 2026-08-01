from uuid import uuid4

from app.domain.entities import DocumentStatus
from app.services.processing_service import ProcessingService


class _FakeRepository:
    def __init__(self):
        self.updated_status = None
        self.saved_chunks = None

    def update_status(
        self,
        document_id,
        *,
        status,
        total_chunks=None,
        error=None,
    ):
        self.updated_status = {
            "document_id": document_id,
            "status": status,
            "total_chunks": total_chunks,
            "error": error,
        }

    def save_chunks(self, *, document_id, document_name, chunks):
        self.saved_chunks = chunks
        return len(chunks)


class _FakeEmbeddings:
    def embed_passage(self, text):
        return [0.1] * 8

    def embed_sentences(self, sentences):
        return [[1.0, 0.0, 0.0] for _ in sentences]

    def count_tokens(self, text):
        return len(text.split())


class _FakePDFParser:
    def __init__(self, pages):
        self.pages = pages

    def extract_pages(self, content):
        return self.pages


def test_process_text_saves_chunks_and_marks_document_ready():
    repository = _FakeRepository()
    service = ProcessingService(repository, _FakeEmbeddings(), _FakePDFParser([]))

    service.process_text(
        str(uuid4()),
        "A single sentence with no semantic break.",
        "document.txt",
    )

    assert repository.updated_status["status"] == DocumentStatus.READY
    assert repository.updated_status["total_chunks"] == len(repository.saved_chunks)
    assert all(chunk.page is None for chunk in repository.saved_chunks)


def test_process_text_marks_document_failed_when_embedding_fails():
    repository = _FakeRepository()

    class _FailingEmbeddings(_FakeEmbeddings):
        def embed_passage(self, text):
            raise RuntimeError("simulated failure")

    service = ProcessingService(repository, _FailingEmbeddings(), _FakePDFParser([]))
    service.process_text(str(uuid4()), "any text", "document.txt")

    assert repository.updated_status["status"] == DocumentStatus.FAILED
    assert "simulated failure" in repository.updated_status["error"]


def test_process_pdf_assigns_page_to_chunks_and_skips_empty_pages():
    repository = _FakeRepository()
    parser = _FakePDFParser(
        ["Text from page one.", "", "Text from page three."],
    )
    service = ProcessingService(repository, _FakeEmbeddings(), parser)

    service.process_pdf(str(uuid4()), b"pdf-content", "document.pdf")

    assert repository.updated_status["status"] == DocumentStatus.READY
    assert {chunk.page for chunk in repository.saved_chunks} == {1, 3}


def test_process_pdf_marks_document_failed_when_no_text_is_extracted():
    repository = _FakeRepository()
    service = ProcessingService(
        repository,
        _FakeEmbeddings(),
        _FakePDFParser(["", ""]),
    )

    service.process_pdf(str(uuid4()), b"empty-pdf-content", "document.pdf")

    assert repository.updated_status["status"] == DocumentStatus.FAILED
