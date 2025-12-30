from unittest.mock import MagicMock, patch

from app.memory import rag_v2, rag_v2_docs


def test_doc_selection_from_seeds_logic():
    """Test standard doc selection logic using initial candidates."""

    # Init Cands:
    # U1: Score 0.1 (Best)
    # U2: Score 0.3
    # U1: Score 0.4
    # U3: Score 0.2

    seeds = [
        {"upload_id": "u1", "score": 0.1},
        {"upload_id": "u2", "score": 0.3},
        {"upload_id": "u1", "score": 0.4},
        {"upload_id": "u3", "score": 0.2},
    ]

    selected = rag_v2_docs.get_doc_candidates_from_seeds(seeds, top_k_docs=2)

    # Expect: U1 (best 0.1), U3 (best 0.2), U2 (best 0.3)
    # Top 2 -> U1, U3
    assert selected == ["u1", "u3"]


def test_search_documents_v2_uses_two_stage_query():
    """Test that DEEP mode performs a seed search then filtered search."""

    mock_coll = MagicMock()
    # First query (seed): Returns top 20
    # Second query (main): Returns top K with filter

    # Mock return values for seed search
    # Returns [uX, uY]
    seed_return = {
        "ids": [["s1", "s2"]],
        "metadatas": [[{"upload_id": "uX"}, {"upload_id": "uY"}]],
        "documents": [["doc1", "doc2"]],
        "distances": [[0.1, 0.2]],
    }

    # Mock return values for main search
    main_return = {"ids": [["m1"]], "metadatas": [[{"upload_id": "uX"}]], "documents": [["main"]], "distances": [[0.1]]}

    mock_coll.query.side_effect = [seed_return, main_return]

    with patch("app.memory.rag_v2._get_rag_v2_collection", return_value=mock_coll):
        with patch("app.memory.rag_v2_telemetry.log_stats"):
            rag_v2.search_documents_v2("q", "o", "s", mode="deep")

            assert mock_coll.query.call_count == 2

            # Check First Call (Seed)
            args1 = mock_coll.query.call_args_list[0][1]
            assert args1["n_results"] == 20

            # Check Second Call (Main)
            args2 = mock_coll.query.call_args_list[1][1]
            assert args2["n_results"] >= 200  # deep mode uses 200
            where = args2["where"]["$and"]
            # Should contain upload_id IN ["uX", "uY"]
            has_selection = any(c.get("upload_id") == {"$in": ["uX", "uY"]} for c in where)
            assert has_selection


def test_auto_pinning_margin_logic():
    """Test pinning is skipped if margin is small."""

    # Needs to return candidates with scores close to each other
    mock_coll = MagicMock()

    # Distances: Best 0.1 (Good), Second 0.12 (Diff 0.02 < 0.08 Margin)
    # Should NOT Pin
    mock_res = {
        "ids": [["1", "2"]],
        "metadatas": [[{"upload_id": "u1"}, {"upload_id": "u2"}]],
        "documents": [["d1", "d2"]],
        "distances": [[0.1, 0.12]],
    }
    mock_coll.query.return_value = mock_res

    # Clear pins
    with patch("app.memory.rag_v2_conversation.set_active_doc") as mock_set:
        with patch("app.memory.rag_v2._get_rag_v2_collection", return_value=mock_coll):
            with patch("app.memory.rag_v2_telemetry.log_stats"):
                rag_v2.search_documents_v2("q", "o", "s", mode="fast", conversation_id="convX")
                mock_set.assert_not_called()


def test_auto_pinning_success():
    """Test pinning happens when margin is good."""
    mock_coll = MagicMock()
    # Distances: Best 0.1, Second 0.3 (Diff 0.2 > 0.08)
    mock_res = {
        "ids": [["1", "2"]],
        "metadatas": [[{"upload_id": "u1"}, {"upload_id": "u2"}]],
        "documents": [["d1", "d2"]],
        "distances": [[0.1, 0.3]],
    }
    mock_coll.query.return_value = mock_res

    with patch("app.memory.rag_v2_conversation.set_active_doc") as mock_set:
        with patch("app.memory.rag_v2._get_rag_v2_collection", return_value=mock_coll):
            with patch("app.memory.rag_v2_telemetry.log_stats"):
                rag_v2.search_documents_v2("q", "o", "s", mode="fast", conversation_id="convY")
                mock_set.assert_called_with("convY", "u1")
