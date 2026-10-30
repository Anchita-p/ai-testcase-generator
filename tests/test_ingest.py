import pytest
from langchain_core.documents import Document

from testgen.ingest import load_document, load_text, split_documents


def test_pdf_loads_one_document_per_page(sample_pdf):
    pages = load_document(sample_pdf)
    assert len(pages) == 3
    assert "LOG-01" in pages[0].page_content
    assert pages[2].metadata["page"] == 2  # page numbers start at 0


def test_text_file_loads_as_one_document(tmp_path):
    path = tmp_path / "stories.md"
    path.write_text("# Login\nAs a user I want to log in.", encoding="utf-8")
    docs = load_document(str(path))
    assert len(docs) == 1
    assert "log in" in docs[0].page_content


def test_blank_pdf_raises_clear_error(blank_pdf):
    with pytest.raises(ValueError, match="No text found"):
        load_document(blank_pdf)


@pytest.mark.parametrize("name", ["sheet.xlsx", "image.png", "noext"])
def test_unsupported_file_types_are_rejected(tmp_path, name):
    path = tmp_path / name
    path.write_text("x")
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_document(str(path))


def test_split_respects_chunk_size():
    doc = Document(page_content="requirement " * 300, metadata={"page": 0})
    chunks = split_documents([doc], chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 200 for c in chunks)


def test_split_keeps_page_metadata():
    doc = Document(page_content="The system shall. " * 50, metadata={"page": 4})
    assert all(c.metadata["page"] == 4 for c in split_documents([doc], 100, 10))


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        split_documents([Document(page_content="x")], chunk_size=100, chunk_overlap=100)


def test_docx_loads_paragraphs_and_tables(tmp_path):
    from docx import Document as W
    word = W()
    word.add_paragraph("LOG-01 A user shall log in.")
    table = word.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "LOG-03", "Lock after 5 attempts"
    path = tmp_path / "srs.docx"
    word.save(path)
    text = load_document(str(path))[0].page_content
    assert "LOG-01" in text and "LOG-03 | Lock after 5 attempts" in text


def test_pasted_text_becomes_one_document():
    assert load_text("LOG-01 login")[0].page_content == "LOG-01 login"


def test_empty_pasted_text_is_rejected():
    with pytest.raises(ValueError, match="No text found"):
        load_text("   ")
