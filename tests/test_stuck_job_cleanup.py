
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_cleanup_stuck_jobs_logic():
    """
    Validation test for cleanup_stuck_image_jobs.
    Coverage:
    A) Stuck job (old activity) -> CLEANED (status=error)
    B) Active job (recent activity) -> SKIPPED (status stays active)
    C) Terminal job -> SKIPPED (status stays complete)
    """
    
    # 1. SETUP MOCKS
    # --------------------------------------------------------------------------
    mock_acquire = AsyncMock(return_value="valid-lock-token")
    mock_release = AsyncMock()
    mock_session = MagicMock()
    
    # Use simple classes to avoid mock nesting issues & SQLModel validation
    class MockMessage:
        def __init__(self, id, created_hours_ago, meta_status, last_activity_min_ago=None):
            self.id = id
            self.created_at = datetime.utcnow() - timedelta(hours=created_hours_ago)
            self.extra_metadata = {
                "type": "image",
                "status": meta_status,
                "job_id": f"job_{id}"
            }
            if last_activity_min_ago is not None:
                act_time = datetime.utcnow() - timedelta(minutes=last_activity_min_ago)
                self.extra_metadata["last_activity_at"] = act_time.isoformat()

    # Case A: Stuck Job (Processing, Activity 45m ago) -> Expect CLEANUP
    msg_stuck = MockMessage("stuck", 1, "processing", 45)
    
    # Case B: Active Job (Processing, Activity 5m ago) -> Expect KEEP
    msg_active = MockMessage("active", 1, "processing", 5)
    
    # Case C: Terminal Job (Complete) -> Expect IGNORE
    # Even if activity is old, status is complete, so should be skipped by logic
    msg_complete = MockMessage("done", 2, "complete", 60)
    
    # Mock Select Result
    mock_messages = [msg_stuck, msg_active, msg_complete]
    mock_session.exec.return_value.all.return_value = mock_messages
    
    # 2. EXECUTE
    # --------------------------------------------------------------------------
    # Patch get_session AND sqlmodel.select (since it's imported in func)
    with patch("app.core.maintenance.acquire_leader_lock", mock_acquire), \
         patch("app.core.maintenance.release_leader_lock", mock_release), \
         patch("app.core.database.get_session") as mock_get_session, \
         patch("sqlmodel.select"): # Vital: Patch global select to allow execution

        mock_get_session.return_value.__enter__.return_value = mock_session
        
        from app.core.maintenance import cleanup_stuck_image_jobs
        await cleanup_stuck_image_jobs()
    
    # 3. VERIFY
    # --------------------------------------------------------------------------
    
    # Verify Session Add calls (which imply update)
    # We expect ONLY msg_stuck to be added with status=error
    
    added_msgs = [call[0][0] for call in mock_session.add.call_args_list]
    
    # Assert Stuck Job was added/updated
    assert msg_stuck in added_msgs, "Stuck job was not updated!"
    assert msg_stuck.extra_metadata["status"] == "error", "Stuck job status not changed to error"
    assert "Zaman aşımı" in msg_stuck.extra_metadata["error"], "Error message mismatch"
    
    # Assert Active Job was NOT added
    # (Note: In some implementations session.add might be called harmlessly, 
    # but our logic specifically only calls add if it changes state. Good check.)
    assert msg_active not in added_msgs, "Active job was incorrectly updated!"
    
    # Assert Terminal Job was NOT added
    assert msg_complete not in added_msgs, "Terminal job was incorrectly updated!"
    
    # Verify Commit was called
    mock_session.commit.assert_called_once()
    
    # Verify Lock Release
    mock_release.assert_called_with("stuck_job_cleanup", "valid-lock-token")
