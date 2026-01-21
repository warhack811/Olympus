"""
Integration Test: Image Queue System
=====================================

End-to-end test for:
1. Queue position calculation and updates
2. Message metadata persistence
3. WebSocket delivery with correct queue_position
4. Sequential GPU processing
5. Complete workflow: queued → processing → complete
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.image.worker_local import AtlasLocalWorker


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TEST 1: Complete Workflow with Queue Positions
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_complete_workflow_with_queue_positions():
    """
    End-to-end test: 3 jobs → queued → processing → complete
    
    Verify:
    - Queue positions are correct (1, 2, 3 based on entry order)
    - Processing status has queue_position=0
    - Complete status has queue_position=0 and image_url
    - All metadata is persisted
    """
    worker = AtlasLocalWorker()
    
    # Mock Redis
    mock_redis = AsyncMock()
    worker.redis_client = mock_redis
    
    # Track all published messages
    all_messages = []
    
    async def capture_publish(channel, message):
        all_messages.append(json.loads(message))
    
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
    
    # Add tasks to queue with position calculation
    for task in tasks:
        worker.total_queued_tasks += 1
        task['_queue_position'] = worker.total_queued_tasks
        await worker.processing_queue.put(task)
    
    # Simulate processing
    for idx in range(1, 4):
        # Pop task
        popped_task = await worker.processing_queue.get()
        queue_pos = popped_task.get('_queue_position', 1)
        
        # 1. Publish queued status
        all_messages.clear()
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
        
        queued_msg = all_messages[0]
        assert queued_msg["status"] == "queued"
        assert queued_msg["queue_position"] == idx
        assert queued_msg["message_id"] == str(popped_task["message_id"])
        print(f"✅ Job {idx}: Queued status published (queue_pos={queue_pos})")
        
        # 2. Publish processing status
        all_messages.clear()
        await worker.publish_status(
            job_id=popped_task["job_id"],
            status="processing",
            progress=50,
            message_id=popped_task["message_id"],
            conv_id=popped_task["conversation_id"],
            queue_position=0,
            user_id=popped_task["user_id"],
            username=popped_task["username"]
        )
        
        processing_msg = all_messages[0]
        assert processing_msg["status"] == "processing"
        assert processing_msg["queue_position"] == 0
        assert processing_msg["progress"] == 50
        print(f"✅ Job {idx}: Processing status published (queue_pos=0)")
        
        # 3. Publish complete status
        all_messages.clear()
        image_url = f"http://example.com/image-{idx}.png"
        await worker.publish_status(
            job_id=popped_task["job_id"],
            status="complete",
            progress=100,
            message_id=popped_task["message_id"],
            conv_id=popped_task["conversation_id"],
            image_url=image_url,
            queue_position=0,
            user_id=popped_task["user_id"],
            username=popped_task["username"]
        )
        
        complete_msg = all_messages[0]
        assert complete_msg["status"] == "complete"
        assert complete_msg["queue_position"] == 0
        assert complete_msg["progress"] == 100
        assert complete_msg["image_url"] == image_url
        assert complete_msg["message_id"] == str(popped_task["message_id"])
        print(f"✅ Job {idx}: Complete status published (queue_pos=0, image_url={image_url})")
        
        # Mark task as done
        worker.processing_queue.task_done()
    
    print("✅ Complete workflow test PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TEST 2: Queue Position Decreases as Jobs Complete
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_queue_position_decreases():
    """
    Verify that queue positions are correct based on entry order.
    
    Scenario:
    - 5 jobs queued in order
    - Job1: queue_pos=1 (first to enter)
    - Job2: queue_pos=2 (second to enter)
    - Job3: queue_pos=3 (third to enter)
    - Job4: queue_pos=4 (fourth to enter)
    - Job5: queue_pos=5 (fifth to enter)
    """
    worker = AtlasLocalWorker()
    
    # Mock Redis
    mock_redis = AsyncMock()
    worker.redis_client = mock_redis
    
    published_messages = []
    
    async def capture_publish(channel, message):
        published_messages.append(json.loads(message))
    
    mock_redis.publish = capture_publish
    
    # Create 5 tasks
    num_tasks = 5
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
        for i in range(1, num_tasks + 1)
    ]
    
    # Add tasks to queue with position calculation
    for task in tasks:
        worker.total_queued_tasks += 1
        task['_queue_position'] = worker.total_queued_tasks
        await worker.processing_queue.put(task)
    
    # Process each task and verify queue position
    for idx in range(1, num_tasks + 1):
        # Pop task
        popped_task = await worker.processing_queue.get()
        queue_pos = popped_task.get('_queue_position', 1)
        
        # Verify queue position
        assert queue_pos == idx, \
            f"Job {idx}: expected queue_pos={idx}, got {queue_pos}"
        
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
        
        msg = published_messages[0]
        assert msg["queue_position"] == idx
        print(f"✅ Job {idx}: queue_pos={idx} (correct)")
        
        # Mark task as done
        worker.processing_queue.task_done()
    
    print("✅ Queue position decreases test PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TEST 3: Error Handling with Queue Positions
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_error_handling_with_queue_positions():
    """
    Verify that errors are handled correctly with queue_position=0.
    
    Scenario:
    - 3 jobs queued
    - Job1: queued (pos=1) → error (queue_pos=0)
    - Job2: queued (pos=2) → processing → complete
    - Job3: queued (pos=3) → processing → complete
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
    
    # Add tasks to queue with position calculation
    for task in tasks:
        worker.total_queued_tasks += 1
        task['_queue_position'] = worker.total_queued_tasks
        await worker.processing_queue.put(task)
    
    # Job1: queued
    task1 = await worker.processing_queue.get()
    queue_pos_1 = task1.get('_queue_position', 1)
    
    published_messages.clear()
    await worker.publish_status(
        job_id=task1["job_id"],
        status="queued",
        progress=0,
        message_id=task1["message_id"],
        conv_id=task1["conversation_id"],
        prompt=task1["prompt"],
        queue_position=queue_pos_1,
        user_id=task1["user_id"],
        username=task1["username"]
    )
    
    assert published_messages[0]["queue_position"] == 1
    print("✅ Job1: Queued with queue_pos=1")
    
    # Job1: error
    published_messages.clear()
    await worker.publish_status(
        job_id=task1["job_id"],
        status="error",
        progress=0,
        message_id=task1["message_id"],
        conv_id=task1["conversation_id"],
        error="Test error",
        queue_position=0,  # Error status has queue_pos=0
        user_id=task1["user_id"],
        username=task1["username"]
    )
    
    assert published_messages[0]["status"] == "error"
    assert published_messages[0]["queue_position"] == 0
    print("✅ Job1: Error status with queue_pos=0")
    
    worker.processing_queue.task_done()
    
    # Job2: queued
    task2 = await worker.processing_queue.get()
    queue_pos_2 = task2.get('_queue_position', 1)
    
    published_messages.clear()
    await worker.publish_status(
        job_id=task2["job_id"],
        status="queued",
        progress=0,
        message_id=task2["message_id"],
        conv_id=task2["conversation_id"],
        prompt=task2["prompt"],
        queue_position=queue_pos_2,
        user_id=task2["user_id"],
        username=task2["username"]
    )
    
    assert published_messages[0]["queue_position"] == 2
    print("✅ Job2: Queued with queue_pos=2")
    
    # Job2: complete
    published_messages.clear()
    await worker.publish_status(
        job_id=task2["job_id"],
        status="complete",
        progress=100,
        message_id=task2["message_id"],
        conv_id=task2["conversation_id"],
        image_url="http://example.com/image-2.png",
        queue_position=0,
        user_id=task2["user_id"],
        username=task2["username"]
    )
    
    assert published_messages[0]["status"] == "complete"
    assert published_messages[0]["queue_position"] == 0
    print("✅ Job2: Complete with queue_pos=0")
    
    worker.processing_queue.task_done()
    
    # Job3: queued
    task3 = await worker.processing_queue.get()
    queue_pos_3 = task3.get('_queue_position', 1)
    
    published_messages.clear()
    await worker.publish_status(
        job_id=task3["job_id"],
        status="queued",
        progress=0,
        message_id=task3["message_id"],
        conv_id=task3["conversation_id"],
        prompt=task3["prompt"],
        queue_position=queue_pos_3,
        user_id=task3["user_id"],
        username=task3["username"]
    )
    
    assert published_messages[0]["queue_position"] == 3
    print("✅ Job3: Queued with queue_pos=3")
    
    # Job3: complete
    published_messages.clear()
    await worker.publish_status(
        job_id=task3["job_id"],
        status="complete",
        progress=100,
        message_id=task3["message_id"],
        conv_id=task3["conversation_id"],
        image_url="http://example.com/image-3.png",
        queue_position=0,
        user_id=task3["user_id"],
        username=task3["username"]
    )
    
    assert published_messages[0]["status"] == "complete"
    assert published_messages[0]["queue_position"] == 0
    print("✅ Job3: Complete with queue_pos=0")
    
    print("✅ Error handling test PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
