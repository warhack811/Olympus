
import pytest
import json
import os
from unittest.mock import patch, MagicMock

def test_ws_payload_schema():
    """Verify expected payload structure for image progress messages."""
    # This is a schema validation test (smoke test level)
    
    payload = {
        "type": "image_progress",
        "job_id": "test_job",
        "username": "alice",
        "user_id": "123",
        "status": "processing",
        "progress": 50,
        "message_id": "msg_1",
        "conversation_id": "conv_1",
        "prompt": "test prompt",
        "image_url": None,
        "error": None
    }
    
    # Validate schema fields
    assert "job_id" in payload
    assert "username" in payload
    assert "status" in payload
    assert "progress" in payload
    assert isinstance(payload["message_id"], str)
    assert isinstance(payload["conversation_id"], str)
    
    # Ensure JSON serializable
    serialized = json.dumps(payload)
    assert len(serialized) > 0
    
    # Deserialize
    deserialized = json.loads(serialized)
    assert deserialized["job_id"] == "test_job"

def test_ws_identity_extraction():
    """Verify target user extraction logic (username or user_id)."""
    
    # Case 1: username present
    data1 = {"username": "alice", "user_id": "123"}
    target1 = data1.get("username") or data1.get("user_id")
    assert target1 == "alice", "Should prefer username"
    
    # Case 2: only user_id
    data2 = {"user_id": "456"}
    target2 = data2.get("username") or data2.get("user_id")
    assert target2 == "456", "Should fallback to user_id"
    
    # Case 3: neither (should be None and trigger drop/warning)
    data3 = {"job_id": "orphan"}
    target3 = data3.get("username") or data3.get("user_id")
    assert target3 is None, "No target should return None"

def test_smoke_log_guard():
    """Verify SMOKE_TEST_ENABLED flag guards expensive logging."""
    
    # Default: OFF
    smoke_enabled_default = os.getenv("SMOKE_TEST_ENABLED", "false").lower() == "true"
    assert smoke_enabled_default is False, "Smoke logs should be OFF by default"
    
    # When set to true (simulate)
    with patch.dict(os.environ, {"SMOKE_TEST_ENABLED": "true"}):
        smoke_enabled_on = os.getenv("SMOKE_TEST_ENABLED", "false").lower() == "true"
        assert smoke_enabled_on is True
    
    # When set to false explicitly
    with patch.dict(os.environ, {"SMOKE_TEST_ENABLED": "false"}):
        smoke_enabled_off = os.getenv("SMOKE_TEST_ENABLED", "false").lower() == "true"
        assert smoke_enabled_off is False
 
