"""Turns raw LLM text into clean, validated data. No LLM calls here, so it's easy to unit test."""
import json
import re

from pydantic import ValidationError

from testgen.schema import TestSuite


class GenerationError(RuntimeError):
    """Raised when the LLM reply can't be turned into valid test cases."""


_FENCE = re.compile(r"```(?:[a-zA-Z]+)?\s*\n?(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict:
    """Find the JSON object in an LLM reply, even if wrapped in ```json fences or extra text."""
    fenced = _FENCE.search(text)
    candidate = fenced.group(1) if fenced else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start == -1 or end <= start:
        raise GenerationError("The model did not return JSON. Please try again.")
    try:
        return json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as e:
        raise GenerationError(f"The model returned invalid JSON ({e.msg}). Please try again.")


def parse_suite(text: str, feature: str) -> TestSuite:
    """Validate the reply against the schema, drop duplicates and number cases TC-001, TC-002..."""
    data = extract_json(text)
    data.setdefault("feature", feature)
    try:
        suite = TestSuite.model_validate(data)
    except ValidationError as e:
        raise GenerationError(f"The model's test cases were incomplete: {e.errors()[0]['msg']}")

    unique, seen = [], set()
    for case in suite.test_cases:
        key = case.title.lower()
        if key not in seen:
            seen.add(key)
            unique.append(case)
    if not unique:
        raise GenerationError("No test cases were generated. Try a different feature name.")

    for i, case in enumerate(unique, start=1):
        case.id = f"TC-{i:03d}"
    suite.test_cases = unique
    return suite


def extract_code(text: str) -> str:
    """Return the code inside the first ``` block, or the whole text if there is no block."""
    fenced = _FENCE.search(text)
    return (fenced.group(1) if fenced else text).strip() + "\n"
