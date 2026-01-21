"""
Test Suite: Queue Position Fix
================================

Tests for:
1. Queue position calculation correctness (using total_queued_tasks counter)
2. Queue position in all status updates (queued, processing, complete, error)
3. Message metadata persistence
4. WebSocket message delivery with queue_position
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.image.worker_local import AtlasLocalWorker
from app.core.websockets import send_image_progress, ImageJobStatus


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: Queue Position Calculation with Counter
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_queue_position_calculation_with_counter():
    """
    Test that queue position is calculated correctly when task enters queue.
    
    Approach: Queue position is calculated at entry time and stored in task
    
    Scenario:
    - 3 tasks queued: Job1, Job2, Job3
    - Job1 enters: total_queued_tasks=1, _queue_position=1
    - Job2 enters: total_queued_tasks=2, _queue_position=2
    - Job3 enters: total_queued_tasks=3, _queue_position=3
    
    Processing (FIFO):
    - Job1 pops: _queue_position=1 (1st in queue)
    - Job2 pops: _queue_position=2 (2nd in queue)
    - Job3 pops: _queue_position=3 (3rd in queue)
    """
    worker = AtlasLocalWorker()
    
    # Create 3 mock tasks
    tasks = [
        {
            "job_id": f"job-{i}",
            "prompt": f"Test prompt {i}",
            "user_id": "test_user",
            "username": "test_user",
            "message_id": i,
            "conversation_id": "conv-1",
            "payload": {}
        }
        for i in range(1, 4)
    ]
    
    # Add tasks to queue with position calculation (simulating run_loop)
    for task in tasks:
        worker.total_queued_tasks += 1
        task['_queue_position'] = worker.total_queued_tasks
        await worker.processing_queue.put(task)
    
    # Verify setup
    assert worker.processing_queue.qsize() == 3, "Queue should have 3 tasks"
    assert worker.total_queued_tasks == 3, "Total queued should be 3"
    
    # Process Job1
    task1 = await worker.processing_queue.get()
    queue_pos_1 = task1.get('_queue_position', 1)
    assert queue_pos_1 == 1, f"Job1 should have queue_pos=1, got {queue_pos_1}"
    print(f"✅ Job1: queue_pos={queue_pos_1}")
    
    # Process Job2
    task2 = await worker.processing_queue.get()
    queue_pos_2 = task2.get('_queue_position', 1)
    assert queue_pos_2 == 2, f"Job2 should have queue_pos=2, got {queue_pos_2}"
    print(f"✅ Job2: queue_pos={queue_pos_2}")
    
    # Process Job3
    task3 = await worker.processing_queue.get()
    queue_pos_3 = task3.get('_queue_position', 1)
    assert queue_pos_3 == 3, f"Job3 should have queue_pos=3, got {queue_pos_3}"
    print(f"✅ Job3: queue_pos={queue_pos_3}")
    
    print("✅ Queue position calculation test PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: Queue Position in All Status Updates
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_queue_position_in_all_status_updates():
    """
    Test that queue_position is included in all status updates:
    - queued: queue_position = actual position
    - processing: queue_position = 0 (not in queue)
    - complete: queue_position = 0 (not in queue)
    - error: queue_position = 0 (not in queue)
    """
    worker = AtlasLocalWorker()
    
    # Mock Redis client
    mock_redis = AsyncMock()
    worker.redis_client = mock_redis
    
    # Track published messages
    published_messages = []
    
    async def capture_publish(channel, message):
        published_messages.append(json.loads(message))
    
    mock_redis.publish = capture_publish
    
    # Test 1: Queued status
    await worker.publish_status(
        job_id="job-1",
        status="queued",
        progress=0,
        message_id=1,
        conv_id="conv-1",
        prompt="Test prompt",
        queue_position=3,
        user_id="user-1",
        username="test_user"
    )
    
    assert len(published_messages) == 1, "Should have 1 published message"
    msg = published_messages[0]
    assert msg["status"] == "queued", "Status should be queued"
    assert msg["queue_position"] == 3, "Queue position should be 3 for queued"
    print("✅ Queued status has queue_position=3")
    
    # Test 2: Processing status
    published_messages.clear()
    await worker.publish_status(
        job_id="job-1",
        status="processing",
        progress=50,
        message_id=1,
        conv_id="conv-1",
        queue_position=0,  # Not in queue anymore
        user_id="user-1",
        username="test_user"
    )
    
    assert len(published_messages) == 1, "Should have 1 published message"
    msg = published_messages[0]
    assert msg["status"] == "processing", "Status should be processing"
    assert msg["queue_position"] == 0, "Queue position should be 0 for processing"
    assert msg["progress"] == 50, "Progress should be 50"
    print("✅ Processing status has queue_position=0")
    
    # Test 3: Complete status
    published_messages.clear()
    await worker.publish_status(
        job_id="job-1",
        status="complete",
        progress=100,
        message_id=1,
        conv_id="conv-1",
        image_url="http://example.com/image.png",
        queue_position=0,  # Not in queue anymore
        user_id="user-1",
        username="test_user"
    )
    
    assert len(published_messages) == 1, "Should have 1 published message"
    msg = published_messages[0]
    assert msg["status"] == "complete", "Status should be complete"
    assert msg["queue_position"] == 0, "Queue position should be 0 for complete"
    assert msg["image_url"] == "http://example.com/image.png", "Image URL should be present"
    print("✅ Complete status has queue_position=0 and image_url")
    
    # Test 4: Error status
    published_messages.clear()
    await worker.publish_status(
        job_id="job-1",
        status="error",
        progress=0,
        message_id=1,
        conv_id="conv-1",
        error="Test error",
        queue_position=0,  # Not in queue anymore
        user_id="user-1",
        username="test_user"
    )
    
    assert len(published_messages) == 1, "Should have 1 published message"
    msg = published_messages[0]
    assert msg["status"] == "error", "Status should be error"
    assert msg["queue_position"] == 0, "Queue position should be 0 for error"
    assert msg["error"] == "Test error", "Error message should be present"
    print("✅ Error status has queue_position=0 and error message")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: Sequential Processing with Queue Position Updates
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sequential_processing_queue_positions():
    """
    Test that queue positions are correctly stored and used as jobs complete.
    
    Scenario:
    - 3 jobs in queue with positions 1, 2, 3
    - Job1 (pos=1) starts processing
    - Job1 completes
    - Job2 (pos=2) starts processing
    - Job2 completes
    - Job3 (pos=3) starts processing
    - Job3 completes
    """
    worker = AtlasLocalWorker()
    
    # Mock Redis
    mock_redis = AsyncMock()
    worker.redis_client = mock_redis
    
    published_messages = []
    
    async def capture_publish(channel, message):
        published_messages.append(json.loads(message))
    
    mock_redis.publish = capture_publish
    
    # Create 3 tasks
    tasks = [
        {
            "job_id": f"job-{i}",
            "prompt": f"Test prompt {i}",
            "user_id": "user-1",
            "username": "test_user",
            "message_id": i,
            "conversation_id": "conv-1",
            "payload": {}
        }
        for i in range(1, 4)
    ]
    
    # Add all tasks to queue with position calculation (simulating run_loop)
    for task in tasks:
        worker.total_queued_tasks += 1
        task['_queue_position'] = worker.total_queued_tasks
        await worker.processing_queue.put(task)
    
    # Simulate processing each task
    for idx in range(1, 4):
        # Pop task
        popped_task = await worker.processing_queue.get()
        queue_pos = popped_task.get('_queue_position', 1)
        
        # Publish queued status
        published_messages.clear()
        await worker.publish_status(
            job_id=popped_task["job_id"],
            status="queued",
            progress=0,
            message_id=popped_task["message_id"],
            conv_id=popped_task["conversation_id"],
            prompt=popped_task["prompt"],
            queue_position=queue_pos,
            user_id=popped_task["user_id"],
            username=popped_task["username"]
        )
        
        # Verify queued status
        assert len(published_messages) == 1
        msg = published_messages[0]
        assert msg["status"] == "queued"
        assert msg["queue_position"] == idx, f"Job {idx} should have queue_pos={idx}"
        print(f"✅ Job {idx}: Queued with queue_pos={queue_pos}")
        
        # Publish processing status
        published_messages.clear()
        await worker.publish_status(
            job_id=popped_task["job_id"],
            status="processing",
            progress=50,
            message_id=popped_task["message_id"],
            conv_id=popped_task["conversation_id"],
            queue_position=0,  # Not in queue
            user_id=popped_task["user_id"],
            username=popped_task["username"]
        )
        
        # Verify processing status
        assert len(published_messages) == 1
        msg = published_messages[0]
        assert msg["status"] == "processing"
        assert msg["queue_position"] == 0
        print(f"✅ Job {idx}: Processing with queue_pos=0")
        
        # Publish complete status
        published_messages.clear()
        await worker.publish_status(
            job_id=popped_task["job_id"],
            status="complete",
            progress=100,
            message_id=popped_task["message_id"],
            conv_id=popped_task["conversation_id"],
            image_url=f"http://example.com/image-{idx}.png",
            queue_position=0,  # Not in queue
            user_id=popped_task["user_id"],
            username=popped_task["username"]
        )
        
        # Verify complete status
        assert len(published_messages) == 1
        msg = published_messages[0]
        assert msg["status"] == "complete"
        assert msg["queue_position"] == 0
        assert msg["image_url"] == f"http://example.com/image-{idx}.png"
        print(f"✅ Job {idx}: Complete with queue_pos=0 and image_url")
        
        # Mark task as done
        worker.processing_queue.task_done()


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: GPU Lock Prevents Concurrent Processing
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_gpu_lock_prevents_concurrent_processing():
    """
    Test that GPU lock ensures only one job processes at a time.
    """
    worker = AtlasLocalWorker()
    
    processing_times = []
    
    async def mock_process(job_id, duration):
        """Simulate processing with duration"""
        async with worker.gpu_lock:
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
    # Extract start and end times
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


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: Message Metadata Persistence
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_message_metadata_persistence():
    """
    Test that message metadata is correctly persisted with all fields.
    """
    worker = AtlasLocalWorker()
    
    # Mock Redis
    mock_redis = AsyncMock()
    worker.redis_client = mock_redis
    
    published_messages = []
    
    async def capture_publish(channel, message):
        published_messages.append(json.loads(message))
    
    mock_redis.publish = capture_publish
    
    # Publish complete status with all metadata
    await worker.publish_status(
        job_id="job-123",
        status="complete",
        progress=100,
        message_id=42,
        conv_id="conv-456",
        prompt="A beautiful sunset",
        image_url="http://example.com/sunset.png",
        queue_position=0,
        user_id="user-789",
        username="john_doe"
    )
    
    # Verify all fields are present
    assert len(published_messages) == 1
    msg = published_messages[0]
    
    assert msg["type"] == "image_progress"
    assert msg["job_id"] == "job-123"
    assert msg["status"] == "complete"
    assert msg["progress"] == 100
    assert msg["message_id"] == "42"
    assert msg["conversation_id"] == "conv-456"
    assert msg["prompt"] == "A beautiful sunset"
    assert msg["image_url"] == "http://example.com/sunset.png"
    assert msg["queue_position"] == 0
    assert msg["user_id"] == "user-789"
    assert msg["username"] == "john_doe"
    
    print("✅ Message metadata persistence test PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
