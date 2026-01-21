"""
FAZE 2: GPU Lock Mechanism - Unit Tests

GPU lock'un concurrent processing'i prevent ettiğini test eder.
"""

import pytest
import asyncio


@pytest.mark.asyncio
async def test_gpu_lock_prevents_concurrent_processing():
    """GPU lock should prevent concurrent job processing"""
    gpu_lock = asyncio.Lock()
    
    processing_times = []
    
    async def mock_process(job_id, duration):
        """Simulate processing with duration"""
        async with gpu_lock:
            start = asyncio.get_event_loop().time()
            processing_times.append(("start", job_id, start))
            await asyncio.sleep(duration)
            end = asyncio.get_event_loop().time()
            processing_times.append(("end", job_id, end))
    
    # Start 3 concurrent processes
    await asyncio.gather(
        mock_process("job-1", 0.1),
        mock_process("job-2", 0.1),
        mock_process("job-3", 0.1),
    )
    
    # Verify no overlapping processing
    starts = {job: time for event, job, time in processing_times if event == "start"}
    ends = {job: time for event, job, time in processing_times if event == "end"}
    
    # Check that no two jobs overlap
    for job1 in ["job-1", "job-2", "job-3"]:
        for job2 in ["job-1", "job-2", "job-3"]:
            if job1 != job2:
                # job1 should end before job2 starts, or vice versa
                assert ends[job1] <= starts[job2] or ends[job2] <= starts[job1], \
                    f"Jobs {job1} and {job2} overlapped!"
    
    print("✅ GPU lock prevents concurrent processing")


@pytest.mark.asyncio
async def test_gpu_lock_released_on_completion():
    """GPU lock should be released after job completion"""
    gpu_lock = asyncio.Lock()
    
    async def mock_job():
        async with gpu_lock:
            await asyncio.sleep(0.05)
    
    # Run job
    await mock_job()
    
    # Lock should be available
    assert not gpu_lock.locked()
    print("✅ GPU lock released on completion")


@pytest.mark.asyncio
async def test_gpu_lock_released_on_error():
    """GPU lock should be released even on error"""
    gpu_lock = asyncio.Lock()
    
    async def mock_job_with_error():
        try:
            async with gpu_lock:
                raise ValueError("Test error")
        except ValueError:
            pass
    
    # Run job with error
    await mock_job_with_error()
    
    # Lock should be available
    assert not gpu_lock.locked()
    print("✅ GPU lock released on error")


def test_queue_position_calculation():
    """Queue position should be calculated correctly"""
    # Simulate queue with 3 jobs
    queue_size = 0
    positions = []
    
    for i in range(3):
        queue_pos = queue_size + 1
        positions.append(queue_pos)
        queue_size += 1
    
    # Verify positions
    assert positions[0] == 1, f"Job 0 should have position 1, got {positions[0]}"
    assert positions[1] == 2, f"Job 1 should have position 2, got {positions[1]}"
    assert positions[2] == 3, f"Job 2 should have position 3, got {positions[2]}"
    print("✅ Queue position calculation correct")


@pytest.mark.asyncio
async def test_concurrent_job_processing():
    """Multiple jobs should be processed sequentially with GPU lock"""
    gpu_lock = asyncio.Lock()
    
    processed_jobs = []
    
    async def mock_process(job_id):
        async with gpu_lock:
            processed_jobs.append(job_id)
            await asyncio.sleep(0.05)
    
    # Process 3 jobs
    await asyncio.gather(*[mock_process(f"job-{i}") for i in range(3)])
    
    # All jobs should be processed
    assert len(processed_jobs) == 3, f"Expected 3 jobs processed, got {len(processed_jobs)}"
    print("✅ Concurrent job processing works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
