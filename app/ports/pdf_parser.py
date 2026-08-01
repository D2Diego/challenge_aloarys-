from typing import Protocol


class PDFParserPort(Protocol):
    def extract_pages(self, content: bytes) -> list[str]:
        """Return extracted text for each page in document order."""
        ...
