import ast
import json

import pytest

from testgen.parsing import GenerationError, extract_code, extract_json, parse_suite
from tests.sample_data import FENCED_REPLY, SCRIPT_REPLY, VALID_REPLY, VALID_SUITE


def test_extract_plain_json():
    assert extract_json(VALID_REPLY)["feature"] == "User login"


def test_extract_json_inside_fences_and_chatter():
    assert len(extract_json(FENCED_REPLY)["test_cases"]) == 4


def test_no_json_raises_friendly_error():
    with pytest.raises(GenerationError, match="did not return JSON"):
        extract_json("Sorry, I can't help with that.")


def test_broken_json_raises_friendly_error():
    with pytest.raises(GenerationError, match="invalid JSON"):
        extract_json('{"feature": "Login", "test_cases": [ }')


def test_parse_suite_numbers_cases_in_order():
    suite = parse_suite(VALID_REPLY, "User login")
    assert [c.id for c in suite.test_cases] == ["TC-001", "TC-002", "TC-003"]


def test_parse_suite_removes_duplicate_titles():
    suite = parse_suite(VALID_REPLY, "User login")
    titles = [c.title.lower() for c in suite.test_cases]
    assert len(titles) == len(set(titles)) == 3


def test_parse_suite_normalises_llm_quirks():
    case = parse_suite(VALID_REPLY, "User login").test_cases[1]
    assert case.type == "Negative"
    assert case.priority == "High"
    assert case.steps[0] == "1. Open the login page"


def test_missing_feature_falls_back_to_user_input():
    data = {k: v for k, v in VALID_SUITE.items() if k != "feature"}
    assert parse_suite(json.dumps(data), "My feature").feature == "My feature"


def test_incomplete_case_raises_generation_error():
    bad = {"feature": "x", "test_cases": [{"title": "only a title"}]}
    with pytest.raises(GenerationError, match="incomplete"):
        parse_suite(json.dumps(bad), "x")


def test_empty_case_list_raises():
    with pytest.raises(GenerationError, match="No test cases"):
        parse_suite('{"feature": "x", "test_cases": []}', "x")


def test_extract_code_from_fenced_block_is_valid_python():
    code = extract_code(SCRIPT_REPLY)
    assert code.startswith("from playwright.sync_api")
    ast.parse(code)  # raises SyntaxError if the code is broken


def test_extract_code_without_fences_returns_text():
    assert extract_code("print('hi')") == "print('hi')\n"
