import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from testgen import config, models
from testgen.generator import PROMPT, format_requirements, generate_test_cases
from testgen.ingest import load_document, split_documents
from testgen.parsing import GenerationError
from testgen.vectorstore import build_vectorstore, get_retriever


@pytest.fixture
def retriever(sample_pdf, fake_embeddings):
    chunks = split_documents(load_document(sample_pdf), chunk_size=200, chunk_overlap=20)
    return get_retriever(build_vectorstore(chunks, fake_embeddings), k=2)


def test_end_to_end_generation_with_fakes(retriever, fake_llm):
    suite, sources = generate_test_cases("User login", retriever, fake_llm, num_cases=5)
    assert suite.feature == "User login"
    assert [c.id for c in suite.test_cases] == ["TC-001", "TC-002", "TC-003"]
    assert len(sources) == 2  # the retrieved requirement chunks are returned for traceability


def test_prompt_contains_rules_feature_count_and_requirements():
    messages = PROMPT.format_messages(
        feature="Login", num_cases=7, test_types="Negative, Edge", context="LOG-01 text"
    )
    system, human = messages[0].content, messages[1].content
    assert "ONLY on the requirements" in system
    assert "Negative, Edge" in system
    assert '"test_cases"' in system  # JSON shape is shown to the model
    assert "Feature to test: Login" in human
    assert "Number of test cases: 7" in human
    assert "LOG-01 text" in human


def test_requirements_are_labelled_with_page_numbers():
    text = format_requirements([Document(page_content="REG-01", metadata={"page": 0})])
    assert text.startswith("[Page 1]\nREG-01")


@pytest.mark.parametrize("feature", ["", "   "])
def test_empty_feature_is_rejected(retriever, fake_llm, feature):
    with pytest.raises(ValueError, match="feature"):
        generate_test_cases(feature, retriever, fake_llm)


@pytest.mark.parametrize("n", [config.MIN_CASES - 1, config.MAX_CASES + 1])
def test_case_count_outside_limits_is_rejected(retriever, fake_llm, n):
    with pytest.raises(ValueError, match="Number of test cases"):
        generate_test_cases("Login", retriever, fake_llm, num_cases=n)


@pytest.mark.parametrize("n", [config.MIN_CASES, config.MAX_CASES])
def test_case_count_at_limits_is_accepted(retriever, fake_llm, n):
    suite, _ = generate_test_cases("Login", retriever, fake_llm, num_cases=n)
    assert suite.test_cases


def test_no_test_types_is_rejected(retriever, fake_llm):
    with pytest.raises(ValueError, match="test type"):
        generate_test_cases("Login", retriever, fake_llm, test_types=())


def test_non_json_reply_raises_generation_error(retriever):
    llm = FakeListChatModel(responses=["I cannot do that."])
    with pytest.raises(GenerationError):
        generate_test_cases("Login", retriever, llm)


def test_missing_api_key_gives_helpful_error(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "")
    with pytest.raises(models.MissingAPIKeyError, match="aistudio.google.com"):
        models.get_llm()
