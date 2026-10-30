"""Turns one manual test case into a starter Playwright (pytest) automation script."""
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from testgen.parsing import extract_code
from testgen.schema import TestCase

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an SDET. Convert the manual test case into a Python test using "
            "pytest-playwright (the `page` fixture and `expect` from playwright.sync_api).\n"
            "Rules:\n"
            "- One test function named test_<short_snake_case_title>.\n"
            "- Use BASE_URL = \"http://localhost:3000\" as a constant at the top.\n"
            "- Prefer role/label/text locators (get_by_role, get_by_label, get_by_text).\n"
            "- Where the real selector is unknown, add a '# TODO: confirm selector' comment.\n"
            "- Assert the expected result with expect(...).\n"
            "- Reply with ONLY the code in one ```python block.",
        ),
        (
            "human",
            "Test case {id}: {title}\n"
            "Preconditions: {preconditions}\n"
            "Steps:\n{steps}\n"
            "Test data: {test_data}\n"
            "Expected result: {expected_result}",
        ),
    ]
)


def generate_playwright_script(case: TestCase, llm: BaseChatModel) -> str:
    chain = PROMPT | llm | StrOutputParser()
    raw = chain.invoke(
        {
            "id": case.id,
            "title": case.title,
            "preconditions": case.preconditions,
            "steps": "\n".join(f"{i}. {s}" for i, s in enumerate(case.steps, start=1)),
            "test_data": case.test_data,
            "expected_result": case.expected_result,
        }
    )
    return extract_code(raw)
