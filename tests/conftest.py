"""Shared fixtures. All tests run offline: no API key, no internet."""
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from tests.sample_data import SCRIPT_REPLY, VALID_REPLY


def make_pdf(path, pages: list[str]) -> None:
    """Write a minimal, valid text PDF (one line of text per page) without extra libraries."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", None]  # pages object filled in later
    font_id = 3
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    for text in pages:
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        content_id = len(objects)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(len(objects))
    kids = " ".join(f"{i} 0 R" for i in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"

    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as f:
        f.write(out)


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "srs.pdf"
    make_pdf(
        path,
        [
            "LOG-01 A registered user shall log in with email and password.",
            "LOG-03 After 5 failed attempts the account is locked for 15 minutes.",
            "SRC-01 Users shall search recipes by name using a search bar.",
        ],
    )
    return str(path)


@pytest.fixture
def blank_pdf(tmp_path):
    path = tmp_path / "blank.pdf"
    make_pdf(path, [""])
    return str(path)


@pytest.fixture
def fake_embeddings():
    """Returns the same vector for the same text, so results are repeatable."""
    return DeterministicFakeEmbedding(size=64)


@pytest.fixture
def fake_llm():
    """A pretend LLM that replies with a valid JSON test suite."""
    return FakeListChatModel(responses=[VALID_REPLY])


@pytest.fixture
def fake_script_llm():
    """A pretend LLM that replies with a Playwright script in a code block."""
    return FakeListChatModel(responses=[SCRIPT_REPLY])
