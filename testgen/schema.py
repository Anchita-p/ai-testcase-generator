"""The shape of a test case. Pydantic validates whatever the LLM returns against this."""
from pydantic import BaseModel, Field, field_validator

TEST_TYPES = ("Positive", "Negative", "Edge", "Boundary")
PRIORITIES = ("High", "Medium", "Low")


def _normalise(value: str, allowed: tuple[str, ...], default: str) -> str:
    """Accept 'negative', 'NEGATIVE ', 'Negative test' etc. and map to an allowed label."""
    text = str(value or "").strip().lower()
    for option in allowed:
        if text.startswith(option.lower()):
            return option
    return default


class TestCase(BaseModel):
    __test__ = False  # tell pytest this is not a test class

    id: str = Field(default="", description="Test case ID, e.g. TC-001")
    title: str = Field(description="Short name of what is being tested")
    requirement: str = Field(description="The requirement ID or statement this case verifies")
    type: str = Field(description="One of: Positive, Negative, Edge, Boundary")
    priority: str = Field(description="One of: High, Medium, Low")
    preconditions: str = Field(default="None", description="What must be true before starting")
    steps: list[str] = Field(description="Ordered, concrete steps a tester follows")
    test_data: str = Field(default="N/A", description="Specific input values to use")
    expected_result: str = Field(description="The observable outcome that means PASS")

    @field_validator("type", mode="before")
    @classmethod
    def _check_type(cls, v):
        return _normalise(v, TEST_TYPES, "Positive")

    @field_validator("priority", mode="before")
    @classmethod
    def _check_priority(cls, v):
        return _normalise(v, PRIORITIES, "Medium")

    @field_validator("steps", mode="before")
    @classmethod
    def _check_steps(cls, v):
        if isinstance(v, str):  # LLM sometimes returns steps as one string
            v = [line.strip(" -•\t") for line in v.splitlines()]
        steps = [str(s).strip() for s in v if str(s).strip()]
        if not steps:
            raise ValueError("a test case needs at least one step")
        return steps

    @field_validator("title", "requirement", "expected_result")
    @classmethod
    def _not_blank(cls, v):
        if not str(v).strip():
            raise ValueError("must not be empty")
        return str(v).strip()


class TestSuite(BaseModel):
    __test__ = False

    feature: str = Field(description="The feature or module these tests cover")
    test_cases: list[TestCase]

    def summary(self) -> dict:
        """Counts by type and priority, used for the coverage view."""
        return {
            "total": len(self.test_cases),
            "by_type": {t: sum(c.type == t for c in self.test_cases) for t in TEST_TYPES},
            "by_priority": {p: sum(c.priority == p for c in self.test_cases) for p in PRIORITIES},
        }
