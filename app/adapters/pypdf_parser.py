"""PDF page extraction adapter using pypdf."""

import io

from pypdf import PdfReader


class PyPDFParser:
    def extract_pages(self, content: bytes) -> list[str]:
        reader = PdfReader(io.BytesIO(content))
        return [page.extract_text() or "" for page in reader.pages]
