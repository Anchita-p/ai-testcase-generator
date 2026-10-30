import ast

from testgen.parsing import parse_suite
from testgen.scriptgen import PROMPT, generate_playwright_script
from tests.sample_data import VALID_REPLY


def _first_case():
    return parse_suite(VALID_REPLY, "User login").test_cases[0]


def test_script_is_extracted_and_is_valid_python(fake_script_llm):
    code = generate_playwright_script(_first_case(), fake_script_llm)
    ast.parse(code)
    assert "def test_" in code
    assert "expect(" in code


def test_prompt_includes_numbered_steps_and_expected_result():
    case = _first_case()
    messages = PROMPT.format_messages(
        id=case.id, title=case.title, preconditions=case.preconditions,
        steps="1. Open the login page", test_data=case.test_data,
        expected_result=case.expected_result,
    )
    assert "pytest-playwright" in messages[0].content
    assert "TODO: confirm selector" in messages[0].content
    assert "1. Open the login page" in messages[1].content
    assert case.expected_result in messages[1].content
