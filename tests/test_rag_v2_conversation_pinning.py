import time
from unittest.mock import MagicMock, patch

from app.memory import rag_v2_conversation


def test_conversation_pinning_flow():
    """Test setting, getting, and expiry of pinned docs."""
    conv_id = "conv1"
    doc_id = "upload123"

    # Init
    rag_v2_conversation._PIN_STORE.clear()

    # 1. Active Doc
    rag_v2_conversation.set_active_doc(conv_id, doc_id)
    assert rag_v2_conversation.get_active_doc(conv_id) == doc_id

    # 2. Expiry
    with patch("time.time", return_value=time.time() + 4000):  # +1 hour+
        assert rag_v2_conversation.get_active_doc(conv_id) is None


def test_conversation_pinning_search_integration():
    """Test that search_documents_v2 applies pinned filter."""
    from app.memory import rag_v2

    conv_id = "conv2"
    rag_v2_conversation.set_active_doc(conv_id, "pinned_doc")

    mock_coll = MagicMock()
    mock_coll.query.return_value = {"ids": [[]], "metadatas": [[]], "documents": [[]], "distances": [[]]}

    with patch("app.memory.rag_v2._get_rag_v2_collection", return_value=mock_coll):
        with patch("app.memory.rag_v2_telemetry.log_stats"):
            rag_v2.search_documents_v2("q", "o", "s", conversation_id=conv_id)

            # Check filter
            call_kwargs = mock_coll.query.call_args[1]
            where = call_kwargs["where"]["$and"]

            # Should have {"upload_id": {"$eq": "pinned_doc"}}
            has_pin = any(c.get("upload_id") == {"$eq": "pinned_doc"} for c in where)
            assert has_pin
