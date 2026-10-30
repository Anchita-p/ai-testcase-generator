import pytest
from langchain_core.documents import Document

from testgen.vectorstore import build_vectorstore, get_retriever


def _chunks():
    texts = ["login with email", "search recipes", "upload profile photo", "save favourites"]
    return [Document(page_content=t, metadata={"page": i}) for i, t in enumerate(texts)]


def test_all_chunks_are_indexed(fake_embeddings):
    assert build_vectorstore(_chunks(), fake_embeddings).index.ntotal == 4


def test_empty_chunk_list_is_rejected(fake_embeddings):
    with pytest.raises(ValueError):
        build_vectorstore([], fake_embeddings)


def test_retriever_returns_top_k(fake_embeddings):
    store = build_vectorstore(_chunks(), fake_embeddings)
    assert len(get_retriever(store, k=2).invoke("login")) == 2


def test_identical_text_ranks_first(fake_embeddings):
    store = build_vectorstore(_chunks(), fake_embeddings)
    assert get_retriever(store, k=1).invoke("search recipes")[0].page_content == "search recipes"
