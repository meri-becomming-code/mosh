"""Tests for DOCX → HTML conversion using mammoth.

The heavy test requires a real .docx fixture file. If the file is not present
the test is automatically skipped so CI can still pass without the binary asset.
"""
import mammoth
from pathlib import Path
import os
import pytest

# ---------------------------------------------------------------------------
# Optional fixture file – skipped when absent
# ---------------------------------------------------------------------------
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_DOCX_FIXTURE = os.path.join(_TESTS_DIR, "Chapter 3 Note Packet (Key) (4).docx")


def convert_docx_to_html_with_images(doc_file_path: str) -> str:
    """Convert a DOCX file to HTML, saving embedded images next to the source."""
    output_dir = Path(doc_file_path).parent
    img_counter = [1]

    def handle_image(image):
        with image.open() as image_bytes:
            ext = image.content_type.split("/")[1]
            img_filename = f"{Path(doc_file_path).stem}_img{img_counter[0]}.{ext}"
            img_path = output_dir / img_filename
            with open(img_path, "wb") as f:
                f.write(image_bytes.read())
            img_counter[0] += 1
            return {"src": img_filename}

    with open(doc_file_path, "rb") as docx_file:
        result = mammoth.convert_to_html(
            docx_file,
            convert_image=mammoth.images.img_element(handle_image),
        )
    return result.value


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_mammoth_import():
    """mammoth package must be importable and expose convert_to_html."""
    assert hasattr(mammoth, "convert_to_html"), "mammoth.convert_to_html not found"


@pytest.mark.skipif(
    not os.path.exists(_DOCX_FIXTURE),
    reason=(
        f"Fixture file not present: {_DOCX_FIXTURE}. "
        "Place 'Chapter 3 Note Packet (Key) (4).docx' in tests/ to enable this test."
    ),
)
def test_docx_conversion_produces_html():
    """Converting the fixture DOCX produces non-empty HTML."""
    html = convert_docx_to_html_with_images(_DOCX_FIXTURE)
    assert isinstance(html, str), "Result should be a string"
    assert len(html) > 0, "HTML output should not be empty"
    assert "<" in html, "HTML output should contain HTML tags"
