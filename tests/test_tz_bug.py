
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

@pytest.mark.asyncio
async def test_naive_vs_aware_comparison_bug():
    """
    Test ensuring that naive datetime (from utcnow) compared with 
    aware datetime (from isoformat with Z or +00:00) works correctly
    due to normalization logic in maintenance.py.
    """
    
    # 1. Setup
    # Current time (system uses UTC naive mostly)
    now_naive = datetime.utcnow()
    # Threshold is 30 mins ago (naive)
    threshold = now_naive - timedelta(minutes=30)
    
    # This job WAS active 45 mins ago (should be cleaned)
    # BUT the timestamp has timezone info (+00:00) which causes TypeError if compared directly with naive
    act_aware_str = (now_naive - timedelta(minutes=45)).replace(tzinfo=timezone.utc).isoformat()
    
    mock_msg_buggy = MagicMock()
    # Configure mock to behave like SQLModel object
    mock_msg_buggy.extra_metadata = {
        "type": "image",
        "status": "processing",
        "job_id": "buggy_tz_job",
        "last_activity_at": act_aware_str # Aware string
    }
    # Created long ago
    mock_msg_buggy.created_at = now_naive - timedelta(hours=2)
    
    mock_session = MagicMock()
    mock_session.exec.return_value.all.return_value = [mock_msg_buggy]
    
    # 2. Execute with mocks
    with patch("app.core.maintenance.acquire_leader_lock", new_callable=AsyncMock) as mock_locks, \
         patch("app.core.maintenance.release_leader_lock", new_callable=AsyncMock), \
         patch("app.core.database.get_session") as mock_get_session, \
         patch("sqlmodel.select"):
         
        mock_locks.return_value = "token"
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        from app.core.maintenance import cleanup_stuck_image_jobs
        
        # This calls the function. If comparison fails (TypeError: can't compare offset-naive and offset-aware), 
        # the test will raise exception and fail.
        await cleanup_stuck_image_jobs()
        
    # 3. Verify
    # If no exception raised, normalization worked.
    # Also verify it was actually cleaned (45m > 30m)
    assert mock_session.add.called, "Buggy TZ job should be cleaned"
    assert mock_msg_buggy.extra_metadata["status"] == "error"
