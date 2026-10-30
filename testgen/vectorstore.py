"""Step 2 of RAG: turn chunks into vectors (embeddings) and store them for similarity search."""
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from testgen import config


def build_vectorstore(chunks: list[Document], embeddings: Embeddings) -> FAISS:
    """Embed every chunk and index it in an in-memory FAISS store."""
    if not chunks:
        raise ValueError("No chunks to index.")
    return FAISS.from_documents(chunks, embeddings)


def get_retriever(store: FAISS, k: int = config.TOP_K):
    """A retriever returns the k chunks most similar to a question."""
    return store.as_retriever(search_kwargs={"k": k})
