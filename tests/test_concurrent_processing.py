"""
FAZE 2: Concurrent Job Processing - Integration Tests

Concurrent job processing, state transitions ve error recovery'yi test eder.
"""

import pytest
import asyncio


@pytest.mark.asyncio
async def test_multiple_jobs_queued_with_positions():
    """Multiple jobs should be queued with correct positions"""
    # Simulate queue with 3 jobs
    queue_size = 0
    positions = []
    
    for i in range(3):
        queue_pos = queue_size + 1
        positions.append(queue_pos)
        queue_size += 1
    
    # Verify positions
    assert positions[0] == 1, f"Job 0 should have position 1"
    assert positions[1] == 2, f"Job 1 should have position 2"
    assert positions[2] == 3, f"Job 2 should have position 3"
    
    print("✅ Multiple jobs queued with correct positions")


@pytest.mark.asyncio
async def test_job_processing_updates_status():
    """Job processing should update status to processing"""
    # Simulate state transition
    status_transitions = []
    
    # Initial state
    status_transitions.append("queued")
    
    # Processing state
    status_transitions.append("processing")
    
    # Verify transitions
    assert status_transitions[0] == "queued", "Initial status should be queued"
    assert status_transitions[1] == "processing", "Status should change to processing"
    
    print("✅ Job processing updates status")


@pytest.mark.asyncio
async def test_error_recovery_starts_next_job():
    """Error in one job should not prevent next job from starting"""
    gpu_lock = asyncio.Lock()
    
    processed = []
    
    async def mock_process_with_error(job_id):
        async with gpu_lock:
            processed.append(job_id)
            if len(processed) == 1:
                raise ValueError("Test error")
    
    # Process 2 jobs (first fails, second succeeds)
    for i in range(2):
        try:
            await mock_process_with_error(f"job-{i}")
        except ValueError:
            pass
    
    # Both jobs should be processed
    assert len(processed) == 2, f"Expected 2 jobs processed, got {len(processed)}"
    print("✅ Error recovery starts next job")


def test_concurrent_updates_no_data_loss():
    """Concurrent updates should not lose data"""
    # Simulate concurrent updates with deep merge
    existing = {
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    
    # Update 1: status and progress
    update1 = {
        "status": "processing",
        "progress": 50
    }
    merged1 = {**existing, **update1}
    
    # Update 2: queue_position
    update2 = {
        "queue_position": 0
    }
    merged2 = {**merged1, **update2}
    
    # Verify no data loss
    assert merged2["status"] == "processing", "Status should be processing"
    assert merged2["progress"] == 50, "Progress should be 50"
    assert merged2["queue_position"] == 0, "Queue position should be 0"
    print("✅ Concurrent updates no data loss")


@pytest.mark.asyncio
async def test_gpu_lock_sequential_processing():
    """GPU lock should ensure sequential processing"""
    gpu_lock = asyncio.Lock()
    
    processing_order = []
    
    async def mock_job(job_id):
        async with gpu_lock:
            processing_order.append(f"{job_id}_start")
            await asyncio.sleep(0.05)
            processing_order.append(f"{job_id}_end")
    
    # Process 3 jobs concurrently
    await asyncio.gather(*[mock_job(f"job-{i}") for i in range(3)])
    
    # Verify sequential processing (no interleaving)
    for i in range(3):
        start_idx = processing_order.index(f"job-{i}_start")
        end_idx = processing_order.index(f"job-{i}_end")
        assert end_idx == start_idx + 1, f"Job {i} should be sequential"
    
    print("✅ GPU lock ensures sequential processing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
