import json
import logging
import os
import sys
from typing import Any

# Ensure project root in pythonpath
sys.path.append(os.getcwd())

from app.memory.rag_v2 import search_documents_v2

# Setup logger to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EvalHarness")

CASES_PATH = os.path.join("tests", "eval_harness", "cases.json")
RESULTS_PATH = os.path.join("data", "eval_results.json")


def check_hit(candidate: dict[str, Any], expected: dict[str, Any]) -> bool:
    # 1. Filename Check
    must_filename = expected.get("must_contain_filename")
    if must_filename and must_filename not in candidate.get("filename", ""):
        return False

    # 2. Page Check
    must_page = expected.get("must_contain_page")
    if must_page is not None:
        if candidate.get("page_number") != must_page:
            return False

    # 3. Text Check
    must_text = expected.get("must_contain_text")
    if must_text:
        if must_text not in candidate.get("text", ""):
            return False

    return True


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    query = case.get("query")
    owner = case.get("owner", "test_user")
    scope = case.get("scope", "user")
    expected = case.get("expected", {})
    case.get("expected_behavior")

    # Run Fast
    fast_results = search_documents_v2(query, owner, scope, top_k=60, mode="fast")
    # Run Deep
    deep_results = search_documents_v2(query, owner, scope, top_k=60, mode="deep")

    metrics = {
        "hit_at_1_fast": False,
        "hit_at_10_fast": False,
        "recall_fast": False,
        "hit_at_1_deep": False,
        "hit_at_10_deep": False,
        "recall_deep": False,
    }

    # If expected behavior is 'no_evidence', we check if results are empty or low score?
    # Actually retrieval layer always returns candidates if vector space matches.
    # So for 'no_evidence' we might just skip 'hit' checks or check scores.
    # But user asked to measure hit/recall.

    if expected:
        # Check Fast
        for i, cand in enumerate(fast_results):
            if check_hit(cand, expected):
                metrics["recall_fast"] = True
                if i < 10:
                    metrics["hit_at_10_fast"] = True
                if i < 1:
                    metrics["hit_at_1_fast"] = True

        # Check Deep
        for i, cand in enumerate(deep_results):
            if check_hit(cand, expected):
                metrics["recall_deep"] = True
                if i < 10:
                    metrics["hit_at_10_deep"] = True
                if i < 1:
                    metrics["hit_at_1_deep"] = True

    return {"id": case["id"], "metrics": metrics, "fast_count": len(fast_results), "deep_count": len(deep_results)}


def main():
    if not os.path.exists(CASES_PATH):
        logger.error(f"Cases file not found: {CASES_PATH}")
        return

    with open(CASES_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    results = []

    for case in cases:
        logger.info(f"Running case: {case['id']}")
        try:
            res = evaluate_case(case)
            results.append(res)
        except Exception as e:
            logger.error(f"Error in case {case['id']}: {e}")
            results.append({"id": case["id"], "error": str(e)})

    # Calculate Aggregates
    summary = {
        "total": len(cases),
        "avg_recall_fast": sum(1 for r in results if r.get("metrics", {}).get("recall_fast")) / len(cases)
        if cases
        else 0,
        "avg_recall_deep": sum(1 for r in results if r.get("metrics", {}).get("recall_deep")) / len(cases)
        if cases
        else 0,
    }

    logger.info(f"Summary: {summary}")

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": results}, f, indent=2)


if __name__ == "__main__":
    main()
