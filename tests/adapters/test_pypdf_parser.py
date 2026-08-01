import io

from pypdf import PdfWriter

from app.adapters.pypdf_parser import PyPDFParser


def _blank_pdf(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_extracts_one_string_per_page_in_order():
    assert PyPDFParser().extract_pages(_blank_pdf(2)) == ["", ""]
