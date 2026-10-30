"""The core: retrieve the requirements for a feature (RAG) and ask the LLM for structured test cases."""
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from testgen import config
from testgen.parsing import parse_suite
from testgen.schema import TestSuite

JSON_SHAPE = """{{
  "feature": "<feature name>",
  "test_cases": [
    {{
      "title": "<short name>",
      "requirement": "<requirement ID or short quote it verifies>",
      "type": "Positive | Negative | Edge | Boundary",
      "priority": "High | Medium | Low",
      "preconditions": "<state before the test>",
      "steps": ["<step 1>", "<step 2>"],
      "test_data": "<exact input values>",
      "expected_result": "<observable outcome that means PASS>"
    }}
  ]
}}"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior QA engineer. Write clear, executable manual test cases "
            "based ONLY on the requirements provided. Do not invent features that are not "
            "described. Every test case must trace back to a specific requirement.\n\n"
            "Rules:\n"
            "- Include these test types where they make sense: {test_types}.\n"
            "- Negative tests cover invalid input and error handling; boundary tests cover "
            "min/max limits; edge tests cover unusual but valid situations.\n"
            "- Steps must be concrete actions (what to click or enter), not vague goals.\n"
            "- Use realistic test data with exact values.\n"
            "- High priority = core functionality or security; Low = cosmetic.\n\n"
            "Reply with ONLY a JSON object in exactly this shape, no other text:\n"
            + JSON_SHAPE,
        ),
        (
            "human",
            "Feature to test: {feature}\n"
            "Number of test cases: {num_cases}\n\n"
            "Requirements:\n{context}",
        ),
    ]
)


def format_requirements(docs: list[Document]) -> str:
    """Join retrieved chunks, labelled with page numbers for traceability."""
    parts = []
    for doc in docs:
        page = doc.metadata.get("page")
        label = f"[Page {page + 1}]" if isinstance(page, int) else "[Page ?]"
        parts.append(f"{label}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def generate_test_cases(
    feature: str,
    retriever,
    llm: BaseChatModel,
    num_cases: int = 8,
    test_types: tuple[str, ...] = ("Positive", "Negative", "Edge", "Boundary"),
) -> tuple[TestSuite, list[Document]]:
    """RAG: retrieve the relevant requirements, then generate and validate test cases.

    Returns the test suite and the requirement chunks it was based on.
    """
    feature = feature.strip()
    if not feature:
        raise ValueError("Please enter a feature or module to test.")
    if not config.MIN_CASES <= num_cases <= config.MAX_CASES:
        raise ValueError(f"Number of test cases must be {config.MIN_CASES}–{config.MAX_CASES}.")
    if not test_types:
        raise ValueError("Select at least one test type.")

    docs = retriever.invoke(feature)                       # 1. Retrieve
    context = format_requirements(docs)                    # 2. Augment
    chain = PROMPT | llm | StrOutputParser()               # 3. Generate
    raw = chain.invoke(
        {
            "feature": feature,
            "num_cases": num_cases,
            "test_types": ", ".join(test_types),
            "context": context,
        }
    )
    return parse_suite(raw, feature), docs                 # 4. Validate
