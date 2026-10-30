"""Which requirement IDs (e.g. LOG-03) have a test case, and which don't. No LLM calls."""
import re

from langchain_core.documents import Document

from testgen.schema import TestSuite

# Matches IDs like LOG-03, REQ-120, FR-7
REQ_ID = re.compile(r"\b[A-Z]{2,6}-\d{1,4}\b")


def find_requirement_ids(text: str) -> list[str]:
    """Unique requirement IDs in order of first appearance."""
    return list(dict.fromkeys(REQ_ID.findall(text)))


def coverage_report(suite: TestSuite, sources: list[Document]) -> dict:
    """Compare the IDs in the retrieved requirements with the IDs the test cases cite.

    - covered:  in the requirements and cited by at least one test case
    - missing:  in the requirements but no test case cites it
    - unknown:  cited by a test case but not in the retrieved requirements (possibly invented)
    """
    in_docs = find_requirement_ids("\n".join(d.page_content for d in sources))
    cited = find_requirement_ids(" ".join(c.requirement for c in suite.test_cases))
    return {
        "covered": [r for r in in_docs if r in cited],
        "missing": [r for r in in_docs if r not in cited],
        "unknown": [r for r in cited if r not in in_docs],
    }
