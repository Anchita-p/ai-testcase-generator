from langchain_core.documents import Document

from testgen.coverage import coverage_report, find_requirement_ids
from testgen.parsing import parse_suite
from tests.sample_data import VALID_REPLY


def test_finds_unique_ids_in_order():
    assert find_requirement_ids("LOG-02 x LOG-01 y LOG-02 z lower-01 A-1") == ["LOG-02", "LOG-01"]


def test_report_splits_covered_missing_and_unknown():
    suite = parse_suite(VALID_REPLY, "User login")  # cites LOG-01, LOG-02, LOG-03
    docs = [Document(page_content="LOG-01 a. LOG-03 b. LOG-04 c.")]
    report = coverage_report(suite, docs)
    assert report == {"covered": ["LOG-01", "LOG-03"], "missing": ["LOG-04"], "unknown": ["LOG-02"]}
