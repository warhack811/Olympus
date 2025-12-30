from unittest.mock import patch

from tests.eval_harness.run_eval import evaluate_case


def test_evaluate_case_smoke():
    """Smoke test for evaluate_case with mocked search_documents_v2."""

    case = {
        "id": "smoke_test",
        "query": "test",
        "owner": "u",
        "scope": "s",
        "expected": {"must_contain_filename": "correct.pdf"},
        "expected_behavior": "hit",
    }

    # Mock search results
    # Fast: No match
    fast_results = [{"filename": "wrong.pdf", "text": "foo"}]
    # Deep: Match
    deep_results = [
        {"filename": "correct.pdf", "text": "target", "score": 0.1},
        {"filename": "wrong.pdf", "text": "foo", "score": 0.5},
    ]

    with patch("tests.eval_harness.run_eval.search_documents_v2") as mock_search:
        # First call (Fast) returns fast_results
        # Second call (Deep) returns deep_results
        mock_search.side_effect = [fast_results, deep_results]

        res = evaluate_case(case)

        metrics = res["metrics"]

        # Fast should fail recall
        assert metrics["recall_fast"] is False
        assert metrics["hit_at_1_fast"] is False

        # Deep should pass recall (first item matches)
        assert metrics["recall_deep"] is True
        assert metrics["hit_at_1_deep"] is True

        # Verify calls
        assert mock_search.call_count == 2
