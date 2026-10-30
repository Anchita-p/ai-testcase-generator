import pytest
from pydantic import ValidationError

from testgen.schema import TestCase, TestSuite


def _case(**overrides):
    data = {
        "title": "Valid login",
        "requirement": "LOG-01",
        "type": "Positive",
        "priority": "High",
        "steps": ["Open page", "Click Login"],
        "expected_result": "Home page shown",
    }
    data.update(overrides)
    return TestCase.model_validate(data)


@pytest.mark.parametrize(
    "raw, expected",
    [("negative", "Negative"), (" EDGE ", "Edge"), ("Boundary value", "Boundary"), ("weird", "Positive")],
)
def test_type_is_normalised(raw, expected):
    assert _case(type=raw).type == expected


@pytest.mark.parametrize("raw, expected", [("high", "High"), ("LOW", "Low"), ("urgent", "Medium")])
def test_priority_is_normalised(raw, expected):
    assert _case(priority=raw).priority == expected


def test_steps_given_as_text_become_a_list():
    case = _case(steps="- Open page\n- Enter email\n\n- Click Login")
    assert case.steps == ["Open page", "Enter email", "Click Login"]


def test_case_without_steps_is_rejected():
    with pytest.raises(ValidationError):
        _case(steps=[])


@pytest.mark.parametrize("field", ["title", "requirement", "expected_result"])
def test_blank_required_text_is_rejected(field):
    with pytest.raises(ValidationError):
        _case(**{field: "   "})


def test_optional_fields_get_defaults():
    case = _case()
    assert case.preconditions == "None"
    assert case.test_data == "N/A"


def test_summary_counts_types_and_priorities():
    suite = TestSuite(
        feature="Login",
        test_cases=[_case(), _case(type="Negative"), _case(type="Negative", priority="Low")],
    )
    s = suite.summary()
    assert s["total"] == 3
    assert s["by_type"] == {"Positive": 1, "Negative": 2, "Edge": 0, "Boundary": 0}
    assert s["by_priority"] == {"High": 2, "Medium": 0, "Low": 1}
