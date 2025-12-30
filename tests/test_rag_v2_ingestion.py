from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from app.memory import rag_v2


def test_add_txt_document_v2():
    """Test TXT ingestion in V2 (treats as single page)."""

    mock_collection = MagicMock()

    with patch("app.memory.rag_v2._get_rag_v2_collection", return_value=mock_collection):
        text = "Hello content that is long enough to verify basic flow."
        rag_v2.add_txt_document(text=text, filename="test.txt", owner="user1", scope="user", conversation_id="conv123")

        # Verify collection.add called
        assert mock_collection.add.called
        call_args = mock_collection.add.call_args[1]

        assert "ids" in call_args
        assert "documents" in call_args
        assert "metadatas" in call_args

        # Verify ID format and metadata
        ids = call_args["ids"]
        metas = call_args["metadatas"]

        assert len(ids) == 1
        # Check fuzzy match because upload_id is random uuid
        # owner:safe_filename:upload_id:pX:cY
        assert ids[0].startswith("user1:test.txt:")
        assert ":p1:c0" in ids[0]

        meta = metas[0]
        assert meta["page_number"] == 1
        assert meta["filename"] == "test.txt"
        assert meta["source"] == "upload_v2"
        assert meta["chunk_index"] == 0
        assert "upload_id" in meta


def test_sanitize_filename():
    """Verify filename sanitization."""
    raw = "bad/file\\name?.pdf"
    clean = rag_v2._sanitize_filename(raw)
    assert clean == "bad_file_name_.pdf"


@patch("app.memory.rag_v2.PyPDF2")
def test_add_pdf_document_v2_mock(mock_pypdf):
    """Test PDF ingestion with mock PyPDF2."""

    # Mock PDF behavior
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 content."

    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page 2 content."

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page1, mock_page2]
    mock_pypdf.PdfReader.return_value = mock_reader

    mock_collection = MagicMock()

    with patch("app.memory.rag_v2._get_rag_v2_collection", return_value=mock_collection):
        # We need to mock open() as well since rag_v2 opens the file
        with patch("builtins.open", mock_open(read_data=b"pdf_data")):
            chunks_added = rag_v2.add_document_pages_from_pdf(
                file_path=Path("dummy.pdf"), filename="doc.pdf", owner="user1"
            )

            # 2 pages, assuming short text = 1 chunk per page = 2 chunks total
            assert chunks_added == 2

            # Verify separate add calls per page
            assert mock_collection.add.call_count == 2

            # Check ID of first page add
            call1 = mock_collection.add.call_args_list[0][1]
            id1 = call1["ids"][0]
            assert ":p1:c0" in id1
            assert "user1:doc.pdf:" in id1

            # Check ID of second page add
            call2 = mock_collection.add.call_args_list[1][1]
            id2 = call2["ids"][0]
            assert ":p2:c0" in id2
