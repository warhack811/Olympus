from unittest.mock import patch

from app.plugins.rag_v2.plugin import RagV2Plugin


def test_bypass_python_question():
    plugin = RagV2Plugin()
    original = "Context."
    context = {"query": "Python'da liste nasıl sıralanır? kod örneği", "owner": "u", "scope": "s"}

    with patch("app.memory.rag_v2.search_documents_v2") as mock_search:
        res = plugin.process_response(original, context=context)
        # RAG should be bypassed: original text unchanged and search not called
        assert res == original
        mock_search.assert_not_called()


def test_non_bypass_but_sanity_fails():
    plugin = RagV2Plugin()
    original = "Context."
    context = {"query": "Bir liste nasıl sıralanır? örnek ver", "owner": "u", "scope": "s"}

    # Return a candidate that does NOT contain query keywords -> lexical sanity should fail
    candidates = [
        {"text": "Unrelated content that does not match the query", "filename": "f", "page_number": 1, "score": 0.1}
    ]

    with patch("app.memory.rag_v2.search_documents_v2", return_value=candidates) as mock_search:
        res = plugin.process_response(original, context=context)
        # Should write ONLY marker and no evidence block
        assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" in res
        assert "=== İLGİLİ BELGELER (RAG v2) ===" not in res
        mock_search.assert_called()


def test_rag_pass():
    plugin = RagV2Plugin()
    original = "Context."
    context = {"query": "Şirket yönergeleri nelerdir?", "owner": "u", "scope": "s"}

    # Candidate contains a phrase matching keywords -> should PASS and include evidence
    candidates = [
        {
            "text": "Şirket yönergeleri: Bu belgede ... açıklama",
            "filename": "policy.pdf",
            "page_number": 3,
            "score": 0.1,
        }
    ]

    with patch("app.memory.rag_v2.search_documents_v2", return_value=candidates):
        with patch("app.memory.rag_v2.expand_neighbors", return_value=[]):
            res = plugin.process_response(original, context=context)
            assert "=== İLGİLİ BELGELER (RAG v2) ===" in res
            assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" not in res


def test_telemetry_single_write():
    plugin = RagV2Plugin()
    context = {"query": "q", "owner": "u", "scope": "s"}

    with patch("app.memory.rag_v2_telemetry.log_stats") as mock_log:
        with patch("app.memory.rag_v2.search_documents_v2", return_value=[]):
            plugin.process_response("Ctx", context=context)
            # Exactly one telemetry write per query
            assert mock_log.call_count == 1
