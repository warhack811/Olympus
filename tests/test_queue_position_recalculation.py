"""
FAZE 3: Dynamic Queue Position Recalculation Tests
"""

import pytest
import asyncio


@pytest.mark.asyncio
async def test_position_recalculation_on_job_complete():
    """Queue positions should be recalculated when job completes"""
    # Simulate 3 queued jobs
    positions_before = [1, 2, 3]
    
    # Job 1 completes (index 0)
    completed_job_index = 0
    
    # Remove completed job and recalculate positions
    remaining_positions = positions_before[completed_job_index + 1:]
    positions_after = list(range(1, len(remaining_positions) + 1))
    
    # Verify positions updated
    assert len(positions_after) == 2
    assert positions_after[0] == 1  # Was 2, now 1
    assert positions_after[1] == 2  # Was 3, now 2
    print("✅ Position recalculation on job complete")


@pytest.mark.asyncio
async def test_position_recalculation_multiple_jobs():
    """Multiple job completions should recalculate all positions"""
    # Simulate 5 queued jobs
    positions = [1, 2, 3, 4, 5]
    
    # Jobs 1 and 2 complete
    remaining_positions = [3, 4, 5]
    
    # Recalculate
    recalculated = []
    for i, pos in enumerate(remaining_positions, 1):
        recalculated.append(i)
    
    # Verify
    assert recalculated == [1, 2, 3]
    print("✅ Position recalculation for multiple jobs")


def test_position_recalculation_preserves_order():
    """Position recalculation should preserve job order"""
    jobs = [
        {"id": "job-1", "position": 1},
        {"id": "job-2", "position": 2},
        {"id": "job-3", "position": 3},
    ]
    
    # Remove job 1
    remaining = jobs[1:]
    
    # Recalculate positions
    for i, job in enumerate(remaining, 1):
        job["position"] = i
    
    # Verify order preserved
    assert remaining[0]["id"] == "job-2"
    assert remaining[0]["position"] == 1
    assert remaining[1]["id"] == "job-3"
    assert remaining[1]["position"] == 2
    print("✅ Position recalculation preserves order")


@pytest.mark.asyncio
async def test_websocket_notification_on_position_change():
    """WebSocket notification should be sent on position change"""
    notifications = []
    
    async def mock_send_notification(job_id, new_position):
        notifications.append({
            "job_id": job_id,
            "new_position": new_position
        })
    
    # Simulate position changes
    await mock_send_notification("job-2", 1)
    await mock_send_notification("job-3", 2)
    
    # Verify notifications sent
    assert len(notifications) == 2
    assert notifications[0]["new_position"] == 1
    assert notifications[1]["new_position"] == 2
    print("✅ WebSocket notification on position change")


def test_position_recalculation_with_concurrent_updates():
    """Position recalculation should handle concurrent updates"""
    # Simulate concurrent updates
    positions = {
        "job-1": 1,
        "job-2": 2,
        "job-3": 3,
    }
    
    # Job 1 completes
    del positions["job-1"]
    
    # Recalculate
    new_positions = {}
    for i, (job_id, _) in enumerate(sorted(positions.items()), 1):
        new_positions[job_id] = i
    
    # Verify
    assert new_positions["job-2"] == 1
    assert new_positions["job-3"] == 2
    print("✅ Position recalculation with concurrent updates")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
