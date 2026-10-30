"""Measure how good the generated test cases are against a hand-written reference.

Run:  python -m testgen.evaluate --models gemini-3.5-flash-lite,gemini-3.1-flash-lite
Scoring (score_suite) makes no LLM calls, so it is unit tested; only run_evaluation uses the API.
"""
import argparse
import json
import time
from pathlib import Path
from statistics import mean

from testgen.coverage import coverage_report, find_requirement_ids
from testgen.generator import generate_test_cases
from testgen.ingest import load_document, split_documents
from testgen.models import get_embeddings, get_llm
from testgen.schema import TestSuite
from testgen.vectorstore import build_vectorstore, get_retriever

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REFERENCE = ROOT / "evaluation" / "reference.json"
DEFAULT_DOC = ROOT / "sample_docs" / "foodies_paradise_srs.pdf"


def load_reference(path=DEFAULT_REFERENCE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _case_text(case) -> str:
    return " ".join([case.title, case.preconditions, *case.steps, case.test_data, case.expected_result]).lower()


def _has_all(text: str, needles: list[str]) -> bool:
    """Every needle must appear; a needle like 'jpg|jpeg' is satisfied by any one alternative."""
    return all(any(alt in text for alt in n.lower().split("|")) for n in needles)


def score_suite(suite: TestSuite, sources, expected: dict) -> dict:
    """Score one generated suite against the reference entry for its feature.

    - req_coverage: share of the expected requirement IDs cited by at least one test case
    - check_rate:   share of key checks passed (e.g. LOG-03 must mention both 5 attempts and 15 minutes)
    - types_ok:     share of expected test types present
    - invented:     requirement IDs cited by cases but absent from the retrieved text
    """
    cited = {r for c in suite.test_cases for r in find_requirement_ids(c.requirement)}
    expected_reqs = expected["requirements"]
    req_coverage = sum(r in cited for r in expected_reqs) / len(expected_reqs)

    passed = []
    for check in expected["checks"]:
        text = " ".join(
            _case_text(c) for c in suite.test_cases if check["req"] in find_requirement_ids(c.requirement)
        )
        passed.append(_has_all(text, check["contains"]))
    check_rate = mean(passed) if passed else 1.0

    present = {c.type for c in suite.test_cases}
    wanted = expected.get("expected_types", [])
    types_ok = sum(t in present for t in wanted) / len(wanted) if wanted else 1.0

    return {
        "cases": len(suite.test_cases),
        "req_coverage": req_coverage,
        "check_rate": check_rate,
        "types_ok": types_ok,
        "invented": len(coverage_report(suite, sources)["unknown"]),
    }


def run_evaluation(models, reference, retriever, num_cases=10) -> list[dict]:
    """Generate for every feature with every model (no fallback, so each model is judged alone)."""
    rows = []
    for model in models:
        llm = get_llm(model=model, use_fallback=False)
        for feature, expected in reference.items():
            row = {"model": model, "feature": feature}
            start = time.time()
            try:
                suite, sources = generate_test_cases(feature, retriever, llm, num_cases)
                row.update(ok=True, **score_suite(suite, sources, expected))
            except Exception as e:  # a failed generation is a result, not a crash
                row.update(ok=False, error=str(e)[:80])
            row["seconds"] = round(time.time() - start, 1)
            rows.append(row)
            print(row, flush=True)
    return rows


def summarise(rows: list[dict]) -> dict[str, dict]:
    """Average per model. Quality averages only count runs that produced valid test cases."""
    out = {}
    for model in dict.fromkeys(r["model"] for r in rows):
        mine = [r for r in rows if r["model"] == model]
        good = [r for r in mine if r["ok"]]
        avg = lambda key: round(mean(r[key] for r in good), 2) if good else 0.0
        out[model] = {
            "success": f"{len(good)}/{len(mine)}",
            "req_coverage": avg("req_coverage"),
            "check_rate": avg("check_rate"),
            "types_ok": avg("types_ok"),
            "invented": avg("invented"),
            "seconds": round(mean(r["seconds"] for r in mine), 1),
        }
    return out


def to_markdown(summary: dict[str, dict]) -> str:
    lines = [
        "| Model | Valid runs | Req. coverage | Key checks passed | Types present | Invented IDs | Avg seconds |",
        "|---|---|---|---|---|---|---|",
    ]
    for model, s in summary.items():
        lines.append(
            f"| {model} | {s['success']} | {s['req_coverage']:.0%} | {s['check_rate']:.0%} | "
            f"{s['types_ok']:.0%} | {s['invented']} | {s['seconds']} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate test case generation quality.")
    parser.add_argument("--models", required=True, help="comma-separated Gemini model names")
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--cases", type=int, default=10)
    parser.add_argument("--out", default=str(ROOT / "evaluation" / "results.md"))
    args = parser.parse_args()

    chunks = split_documents(load_document(args.doc))
    retriever = get_retriever(build_vectorstore(chunks, get_embeddings()))
    rows = run_evaluation(args.models.split(","), load_reference(args.reference), retriever, args.cases)
    table = to_markdown(summarise(rows))
    Path(args.out).write_text(table + "\n", encoding="utf-8")
    print("\n" + table)


if __name__ == "__main__":
    main()
