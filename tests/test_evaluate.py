from langchain_core.documents import Document

from testgen.evaluate import load_reference, score_suite, summarise, to_markdown
from testgen.parsing import parse_suite
from tests.sample_data import VALID_REPLY

SUITE = parse_suite(VALID_REPLY, "User login")  # cites LOG-01, LOG-02, LOG-03
SOURCES = [Document(page_content="LOG-01 a. LOG-02 b. LOG-03 c.")]


def test_scores_coverage_checks_and_types():
    expected = {
        "requirements": ["LOG-01", "LOG-03", "LOG-09"],
        "checks": [
            {"req": "LOG-02", "contains": ["invalid email or password"]},   # in expected result
            {"req": "LOG-03", "contains": ["5", "15"]},                     # 5 attempts, 15 minutes
            {"req": "LOG-01", "contains": ["fingerprint"]},                 # never tested
        ],
        "expected_types": ["Positive", "Negative", "Edge"],
    }
    score = score_suite(SUITE, SOURCES, expected)
    assert score["req_coverage"] == 2 / 3
    assert score["check_rate"] == 2 / 3
    assert score["types_ok"] == 2 / 3
    assert score["invented"] == 0


def test_alternatives_with_pipe_match_any_one():
    expected = {"requirements": ["LOG-03"], "checks": [{"req": "LOG-03", "contains": ["1 hour|15 minutes"]}]}
    assert score_suite(SUITE, SOURCES, expected)["check_rate"] == 1.0


def test_invented_requirement_ids_are_counted():
    sources = [Document(page_content="LOG-01 only.")]
    expected = {"requirements": ["LOG-01"], "checks": []}
    assert score_suite(SUITE, sources, expected)["invented"] == 2  # LOG-02 and LOG-03 not in the source


def test_summary_averages_only_valid_runs_and_formats_table():
    rows = [
        {"model": "m", "ok": True, "req_coverage": 1.0, "check_rate": 0.5, "types_ok": 1.0, "invented": 0, "seconds": 4.0},
        {"model": "m", "ok": False, "error": "timeout", "seconds": 6.0},
    ]
    summary = summarise(rows)
    assert summary["m"]["success"] == "1/2" and summary["m"]["check_rate"] == 0.5
    assert summary["m"]["seconds"] == 5.0
    assert "| m | 1/2 | 100% | 50% |" in to_markdown(summary)


def test_reference_file_is_well_formed():
    for feature, entry in load_reference().items():
        assert entry["requirements"] and entry["checks"], feature
        assert all(c["req"] in entry["requirements"] for c in entry["checks"]), feature
