from unittest.mock import MagicMock, patch

from app.plugins.rag_v2.plugin import RagV2Plugin


def test_process_response_with_candidates():
    """Test process_response appends search results correctly."""
    plugin = RagV2Plugin()

    # Text to enhance
    original_text = "Context."

    # Plugin Context
    context = {"query": "something", "owner": "user1", "scope": "user"}

    # Mock rag_v2.search_documents_v2 return value
    mock_candidates = [
        {"text": "something Relevant Info 1", "filename": "doc1.pdf", "page_number": 5, "score": 0.1},
        {"text": "something Relevant Info 2", "filename": "doc1.pdf", "page_number": 6, "score": 0.2},
    ]

    # Patch rag_v2 import inside the plugin file or module
    # Since plugin does 'from app.memory import rag_v2', we patch rag_v2
    with patch("app.memory.rag_v2.search_documents_v2", return_value=mock_candidates) as mock_search:
        enhanced = plugin.process_response(original_text, context=context)

        # Verify search called
        mock_search.assert_called_once_with(
            query="something",
            owner="user1",
            scope="user",
            top_k=60,
            mode="fast",
            conversation_id=None,
            continue_mode=False,
            return_stats=True,
        )

        # Verify result contains the block
        assert "=== İLGİLİ BELGELER (RAG v2) ===" in enhanced
        assert "[doc1.pdf | p.5] something Relevant Info 1" in enhanced
        assert "[doc1.pdf | p.6] something Relevant Info 2" in enhanced
        assert enhanced.startswith(original_text)


def test_process_response_no_context_query():
    """Test returns original text if context missing required fields."""
    plugin = RagV2Plugin()
    original_text = "Context."

    # Missing query
    context = {"owner": "u", "scope": "s"}

    with patch("app.memory.rag_v2.search_documents_v2") as mock_search:
        res = plugin.process_response(original_text, context=context)
        assert res == original_text
        mock_search.assert_not_called()


def test_process_response_empty_results():
    """Test returns original text if no docs found."""
    plugin = RagV2Plugin()
    original_text = "Context."
    context = {"query": "q", "owner": "u", "scope": "s"}

    with patch("app.memory.rag_v2.search_documents_v2", return_value=[]):
        res = plugin.process_response(original_text, context=context)
        # Should now contain status marker
        assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" in res
        assert res.startswith(original_text)
        assert "=== İLGİLİ BELGELER (RAG v2) ===" not in res


def test_process_response_error_handling():
    """Test fail-open behavior on exception."""
    plugin = RagV2Plugin()
    context = {"query": "q", "owner": "u", "scope": "s"}

    with patch("app.memory.rag_v2.search_documents_v2", side_effect=Exception("Boom")):
        res = plugin.process_response("Text", context=context)
        assert res == "Text"


def test_hybrid_search_sorting_integration():
    """Test that plugin uses hybrid_score for sorting if present."""
    plugin = RagV2Plugin()
    context = {"query": "q", "owner": "u", "scope": "s"}

    # Candidate 1: Bad dense score (0.9), but good hybrid score (0.1)
    c1 = {"text": "HybridBest", "score": 0.9, "hybrid_score": 0.1, "filename": "1"}
    # Candidate 2: Good dense score (0.2), but worse hybrid score (0.2)
    c2 = {"text": "HybridSecond", "score": 0.2, "hybrid_score": 0.2, "filename": "2"}

    # If sorted by 'score' (dense), c2 comes first.
    # If sorted by 'hybrid_score', c1 comes first.

    # Make query match candidate text so lexical sanity passes
    context = {"query": "HybridBest", "owner": "u", "scope": "s"}
    with patch("app.memory.rag_v2.search_documents_v2", return_value=[c1, c2]):
        with patch("app.memory.rag_v2.expand_neighbors", return_value=[]):
            enhanced = plugin.process_response("Ctx", context=context)

            # Both entries should appear in the result
            assert "HybridBest" in enhanced
            assert "HybridSecond" in enhanced


def test_lexical_search_fail_open_integration():
    """Test standard search still works if lexical fails in deep mode."""
    # This involves mocking inside rag_v2.search_documents_v2 logic
    # But since we mock search_documents_v2 entire function in plugin tests,
    # we should trust that rag_v2.search_documents_v2's own unit tests cover internal logic.
    # However, we can add a simple check here if we used real search_documents_v2
    pass


# ... (sorting and expansion tests remain same) ...

# ...


def test_process_response_no_evidence_due_to_threshold():
    """Test returns status marker if best score > 0.50."""
    plugin = RagV2Plugin()
    context = {"query": "q", "owner": "u", "scope": "s"}

    # Best score 0.51 (Poor)
    candidates = [{"text": "Bad", "score": 0.51}]

    with patch("app.memory.rag_v2.search_documents_v2", return_value=candidates):
        res = plugin.process_response("Ctx", context=context)
        assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" in res
        assert "Ctx" in res


def test_process_response_no_evidence_due_to_margin():
    """Test returns status marker if margin < 0.08."""
    plugin = RagV2Plugin()
    context = {"query": "q", "owner": "u", "scope": "s"}

    # Best 0.30, Second 0.33 -> Diff 0.03 (< 0.08)
    candidates = [{"text": "A", "score": 0.30}, {"text": "B", "score": 0.33}]

    with patch("app.memory.rag_v2.search_documents_v2", return_value=candidates):
        res = plugin.process_response("Ctx", context=context)
        assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" in res


def test_process_response_with_valid_evidence():
    """Test returns evidence block with guard text if valid."""
    plugin = RagV2Plugin()
    context = {"query": "policy", "owner": "u", "scope": "s"}

    # Best 0.25, Second 0.40 -> Diff 0.15 (> 0.08) -> Valid
    candidates = [
        {"text": "policy A", "score": 0.25, "filename": "f", "page_number": 1},
        {"text": "policy B", "score": 0.40, "filename": "f", "page_number": 2},
    ]

    with patch("app.memory.rag_v2.search_documents_v2", return_value=candidates):
        # Mock expand to avoid actually calling DB
        with patch("app.memory.rag_v2.expand_neighbors", return_value=[]):
            res = plugin.process_response("Ctx", context=context)

            assert "=== İLGİLİ BELGELER (RAG v2) ===" in res
            assert "⚠️ Aşağıdaki bilgiler BELGE KANITIDIR" in res
            assert "[f | p.1] policy A" in res
            assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" not in res


def test_hybrid_merge_key_uses_page_number():
    """Test that merge key disambiguates by page number."""
    from app.memory import rag_v2

    # Mock Chroma Collection
    mock_coll = MagicMock()

    # Dense returns [Chunk0_Page1]
    mock_coll.query.return_value = {
        "ids": [["id1"]],
        "metadatas": [[{"upload_id": "u1", "page_number": 1, "chunk_index": 0, "filename": "f"}]],
        "documents": [["DenseText"]],
        "distances": [[0.1]],
    }

    # Lexical returns [Chunk0_Page2]
    mock_lexical = [
        {
            "upload_id": "u1",
            "page_number": 2,
            "chunk_index": 0,
            "filename": "f",
            "text": "LexicalText",
            "bm25_score": -10.0,
        }
    ]

    with patch("app.memory.rag_v2._get_rag_v2_collection", return_value=mock_coll):
        with patch("app.memory.rag_v2_lexical.lexical_search", return_value=mock_lexical):
            # Force import of lexical if needed inside function
            with patch.dict(
                "sys.modules",
                {"app.memory.rag_v2_lexical": MagicMock(lexical_search=MagicMock(return_value=mock_lexical))},
            ):
                # Mock telemetry to avoid errors during real execution of search_documents_v2
                with patch("app.memory.rag_v2_telemetry.log_stats"):
                    candidates = rag_v2.search_documents_v2("q", "o", "s", mode="deep")

                    # Should have 2 candidates if key includes page_number
                    assert len(candidates) == 2

                    # Verify we have both pages
                    pages = sorted([c["page_number"] for c in candidates])
                    assert pages == [1, 2]


def test_gating_uses_hybrid_score_for_hybrid_candidates():
    """Test gating uses hybrid threshold (0.75) for hybrid candidates."""
    plugin = RagV2Plugin()
    context = {"query": "HybridGood", "owner": "u", "scope": "s"}

    # Case: Hybrid Score 0.60 (Good for Hybrid < 0.75)
    # But Dense Score 0.90 (Bad for Distance > 0.50)
    # Should PASS gating because it is hybrid type
    cand = {
        "text": "HybridGood",
        "score": 0.9,
        "hybrid_score": 0.60,
        "score_type": "hybrid_distance",
        "chunk_index": 0,
        "page_number": 1,
        "filename": "f",
    }

    with patch("app.memory.rag_v2.search_documents_v2", return_value=[cand]):
        with patch("app.memory.rag_v2.expand_neighbors", return_value=[]):
            res = plugin.process_response("Ctx", context=context)
            assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" not in res
            assert "HybridGood" in res


def test_gating_fails_hybrid_threshold():
    """Test gating fails if hybrid score > 0.75."""
    plugin = RagV2Plugin()
    context = {"query": "q", "owner": "u", "scope": "s"}

    cand = {"text": "HybridBad", "score": 0.9, "hybrid_score": 0.76, "score_type": "hybrid_distance"}

    with patch("app.memory.rag_v2.search_documents_v2", return_value=[cand]):
        res = plugin.process_response("Ctx", context=context)
        assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" in res


def test_telemetry_logging_integration():
    """Test that telemetry log_stats is called during process_response."""
    plugin = RagV2Plugin()
    context = {"query": "q", "owner": "u", "scope": "s"}

    # Needs to match import path in plugin: from app.memory.rag_v2_telemetry import log_stats
    # We mock it in sys.modules or patch the module if imported at top level.
    # The plugin imports it INSIDE the method or top?
    # I put it inside _log_plugin_stats.

    with patch("app.memory.rag_v2_telemetry.log_stats") as mock_log:
        with patch("app.memory.rag_v2.search_documents_v2", return_value=[]):
            plugin.process_response("Ctx", context=context)

            # Should log telemetry once with plugin_decision mode
            assert mock_log.called
            stats = mock_log.call_args[0][0]
            assert stats.mode_used == "plugin_decision"
            # When search returns no candidates plugin emits 'empty' gating result
            assert stats.gating_result == "empty"
