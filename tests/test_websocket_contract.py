import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.core.websockets import metrics, send_to_user, register_connection, unregister_connection

@pytest.fixture(autouse=True)
def reset_metrics():
    metrics["ws_image_event_sent_count"] = 0
    metrics["ws_image_event_dropped_no_target_count"] = 0
    metrics["ws_image_event_no_recipient_count"] = 0
    yield

@pytest.mark.asyncio
async def test_ws_payload_contract_success():
    """Verify schema for image_progress events."""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    register_connection(ws, 123, "alice")
    
    # Valid payload
    payload = {
        "type": "image_progress",
        "job_id": "job_123",
        "status": "complete",
        "progress": 100,
        "conversation_id": "conv_456",
        "message_id": "msg_789",
        "image_url": "http://example.com/img.png"
    }
    
    await send_to_user("alice", payload)
    
    # Contract Verification
    assert ws.send_json.called
    sent_msg = ws.send_json.call_args[0][0]
    assert sent_msg["job_id"] == "job_123"
    assert sent_msg["status"] == "complete"
    assert "image_url" in sent_msg
    assert metrics["ws_image_event_sent_count"] == 1
    
    unregister_connection(ws)

@pytest.mark.asyncio
async def test_ws_payload_contract_error():
    """Verify error payload contract."""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    register_connection(ws, 123, "alice")
    
    payload = {
        "type": "image_progress",
        "job_id": "job_err",
        "status": "error",
        "error": "GPU Out of Memory"
    }
    
    await send_to_user("alice", payload)
    sent_msg = ws.send_json.call_args[0][0]
    assert sent_msg["status"] == "error"
    assert "error" in sent_msg
    
    unregister_connection(ws)

@pytest.mark.asyncio
async def test_ws_metrics_no_recipient():
    """Verify metrics when no connection found for target."""
    payload = {"type": "test"}
    await send_to_user("non_existent_user", payload)
    
    assert metrics["ws_image_event_no_recipient_count"] == 1
    assert metrics["ws_image_event_sent_count"] == 0
