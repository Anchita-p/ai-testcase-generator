"""Step 1 of RAG: load the requirements document and split it into overlapping chunks."""
from pathlib import Path

from docx import Document as WordDocument
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from testgen import config

SUPPORTED_TYPES = (".pdf", ".docx", ".txt", ".md")


def _read_docx(path: str) -> str:
    """Text of a Word file: paragraphs first, then table rows (cells joined with ' | ')."""
    word = WordDocument(path)
    lines = [p.text for p in word.paragraphs]
    for table in word.tables:
        lines += [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
    return "\n".join(lines)


def load_text(text: str, name: str = "pasted text") -> list[Document]:
    """Wrap pasted notes / user stories as a single Document."""
    if not text.strip():
        raise ValueError("No text found. Paste some requirements first.")
    return [Document(page_content=text, metadata={"page": 0, "source": name})]


def load_document(path: str) -> list[Document]:
    """Load a PDF (one Document per page) or a Word/text/markdown file (one Document)."""
    suffix = Path(path).suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported file type '{suffix}'. Use PDF, DOCX, TXT or MD.")

    if suffix == ".pdf":
        docs = PyPDFLoader(path).load()
    elif suffix == ".docx":
        docs = [Document(page_content=_read_docx(path), metadata={"page": 0, "source": path})]
    else:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        docs = [Document(page_content=text, metadata={"page": 0, "source": path})]

    docs = [d for d in docs if d.page_content.strip()]
    if not docs:
        raise ValueError(
            "No text found in this document. If it's a scanned PDF, use a text-based file."
        )
    return docs


def split_documents(
    docs: list[Document],
    chunk_size: int = config.CHUNK_SIZE,
    chunk_overlap: int = config.CHUNK_OVERLAP,
) -> list[Document]:
    """Cut pages into chunks. Overlap keeps requirements that cross a boundary intact."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(docs)
