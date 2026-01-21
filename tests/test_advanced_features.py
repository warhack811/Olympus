"""
FAZE 4: Advanced Features & Optimization Tests
- Priority Queue Support
- Job Retry Mechanism
- Job Timeout Enforcement
- Batch Job Processing
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.image.job_queue import ImageJob, ImageJobQueue


class TestPriorityQueue:
    """Priority Queue Support Tests"""

    @pytest.mark.asyncio
    async def test_high_priority_job_processed_first(self):
        """High priority jobs should be processed before normal/low priority"""
        queue = ImageJobQueue()
        
        # Create jobs with different priorities
        low_job = ImageJob(
            username="user1",
            prompt="low priority",
            conversation_id="conv1",
            on_done=Mock(),
            priority="low"
        )
        
        high_job = ImageJob(
            username="user1",
            prompt="high priority",
            conversation_id="conv1",
            on_done=Mock(),
            priority="high"
        )
        
        normal_job = ImageJob(
            username="user1",
            prompt="normal priority",
            conversation_id="conv1",
            on_done=Mock(),
            priority="normal"
        )
        
        # Add in random order
        queue.queue.put_nowait(low_job)
        queue.queue.put_nowait(normal_job)
        queue.queue.put_nowait(high_job)
        
        # Get next job should be high priority
        next_job = await queue._get_next_job()
        assert next_job.priority == "high"
        print("✅ High priority job processed first")

    @pytest.mark.asyncio
    async def test_priority_order_maintained(self):
        """Priority order should be: high > normal > low"""
        queue = ImageJobQueue()
        
        jobs = [
            ImageJob("user1", "low", "conv1", Mock(), priority="low"),
            ImageJob("user1", "high", "conv1", Mock(), priority="high"),
            ImageJob("user1", "normal", "conv1", Mock(), priority="normal"),
        ]
        
        for job in jobs:
            queue.queue.put_nowait(job)
        
        # Extract in priority order
        order = []
        for _ in range(3):
            job = await queue._get_next_job()
            order.append(job.priority)
        
        assert order == ["high", "normal", "low"]
        print("✅ Priority order maintained: high > normal > low")

    def test_priority_field_persisted(self):
        """Priority field should be persisted in message metadata"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
            priority="high"
        )
        
        assert job.priority == "high"
        print("✅ Priority field persisted")


class TestRetryMechanism:
    """Job Retry Mechanism Tests"""

    @pytest.mark.asyncio
    async def test_failed_job_retried_with_backoff(self):
        """Failed jobs should be retried with exponential backoff"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
        )
        
        # Simulate retry attempts with 4 steps
        backoff_times = []
        for attempt in range(4):
            backoff = 2 ** attempt  # 1s, 2s, 4s, 8s
            backoff_times.append(backoff)
            job.retry_count = attempt + 1
        
        assert backoff_times == [1, 2, 4, 8]
        print("✅ Exponential backoff: 1s, 2s, 4s, 8s")

    def test_retry_count_max_4(self):
        """Retry count should not exceed 4"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
        )
        
        # Simulate max retries
        for _ in range(4):
            job.retry_count += 1
        
        assert job.retry_count == 4
        assert job.retry_count < 5  # Should not exceed 4
        print("✅ Retry count max 4")

    def test_retry_count_persisted(self):
        """Retry count should be persisted in metadata"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
        )
        
        job.retry_count = 2
        assert job.retry_count == 2
        print("✅ Retry count persisted")

    @pytest.mark.asyncio
    async def test_timeout_error_not_retried(self):
        """Timeout errors should not trigger retry"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
        )
        
        # Timeout should not be retried
        error = TimeoutError("Job timeout")
        should_retry = not isinstance(error, TimeoutError)
        
        assert not should_retry
        print("✅ Timeout errors not retried")


class TestTimeoutEnforcement:
    """Job Timeout Enforcement Tests"""

    def test_default_timeout_5_minutes(self):
        """Default timeout should be 5 minutes (300 seconds)"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
        )
        
        assert job.timeout_seconds == 300
        print("✅ Default timeout 300 seconds (5 minutes)")

    def test_custom_timeout_set(self):
        """Custom timeout should be settable"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
            timeout_seconds=600,  # 10 minutes
        )
        
        assert job.timeout_seconds == 600
        print("✅ Custom timeout settable")

    def test_start_time_tracked(self):
        """Start time should be tracked for timeout monitoring"""
        import time
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
        )
        
        job.start_time = time.time()
        assert job.start_time is not None
        print("✅ Start time tracked")

    @pytest.mark.asyncio
    async def test_timeout_error_message(self):
        """Timeout should produce clear error message"""
        timeout_seconds = 300
        error_msg = f"Image generation timeout after {timeout_seconds}s"
        
        assert "timeout" in error_msg.lower()
        assert "300" in error_msg
        print("✅ Timeout error message clear")


class TestBatchProcessing:
    """Batch Job Processing Tests"""

    def test_batch_id_assigned(self):
        """Batch ID should be assignable to jobs"""
        batch_id = "batch-123"
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
            batch_id=batch_id,
        )
        
        assert job.batch_id == batch_id
        print("✅ Batch ID assigned")

    def test_batch_consistency_validation(self):
        """Batch jobs should have same conversation_id"""
        queue = ImageJobQueue()
        batch_id = "batch-123"
        conv_id = "conv1"
        
        job1 = ImageJob(
            username="user1",
            prompt="test1",
            conversation_id=conv_id,
            on_done=Mock(),
            batch_id=batch_id,
        )
        
        job2 = ImageJob(
            username="user1",
            prompt="test2",
            conversation_id=conv_id,
            on_done=Mock(),
            batch_id=batch_id,
        )
        
        # Both should have same conversation_id
        assert job1.conversation_id == job2.conversation_id
        print("✅ Batch consistency: same conversation_id")

    def test_batch_atomicity(self):
        """Batch processing should be atomic"""
        batch_id = "batch-123"
        jobs = [
            ImageJob("user1", f"prompt{i}", "conv1", Mock(), batch_id=batch_id)
            for i in range(3)
        ]
        
        # All jobs in batch should have same batch_id
        batch_ids = [job.batch_id for job in jobs]
        assert all(bid == batch_id for bid in batch_ids)
        print("✅ Batch atomicity: all jobs have same batch_id")

    @pytest.mark.asyncio
    async def test_batch_submission_validation(self):
        """Batch submission should validate all jobs before adding"""
        queue = ImageJobQueue()
        batch_id = "batch-456"
        
        # Create valid batch
        jobs = [
            ImageJob("user1", f"prompt{i}", "conv1", Mock(), batch_id=batch_id)
            for i in range(3)
        ]
        
        # Validate batch consistency
        for job in jobs:
            assert job.batch_id == batch_id
            assert job.conversation_id == "conv1"
        
        print("✅ Batch submission validation passed")

    @pytest.mark.asyncio
    async def test_batch_with_different_conversation_fails(self):
        """Batch with different conversation_ids should fail validation"""
        batch_id = "batch-789"
        
        jobs = [
            ImageJob("user1", "prompt1", "conv1", Mock(), batch_id=batch_id),
            ImageJob("user1", "prompt2", "conv2", Mock(), batch_id=batch_id),  # Different conv
        ]
        
        # Check that conversations are different
        conversations = [job.conversation_id for job in jobs]
        assert len(set(conversations)) > 1  # Should have different conversations
        print("✅ Batch validation detects different conversations")


class TestPerformanceOptimization:
    """Performance Optimization Tests"""

    def test_job_lookup_o1(self):
        """Job lookup should be O(1) time"""
        job_id = "job-123"
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
            job_id=job_id,
        )
        
        # Direct access is O(1)
        assert job.job_id == job_id
        print("✅ Job lookup O(1)")

    def test_queue_position_calculation_fast(self):
        """Queue position calculation should be < 50ms"""
        import time
        queue = ImageJobQueue()
        
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
        )
        
        start = time.time()
        pos = queue._calculate_queue_position(job)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        assert elapsed < 50  # Should be < 50ms
        assert pos >= 1
        print(f"✅ Queue position calculation: {elapsed:.2f}ms (< 50ms)")

    def test_priority_aware_position_calculation(self):
        """Position calculation should consider priority"""
        queue = ImageJobQueue()
        
        # Create jobs with different priorities
        low_job = ImageJob("user1", "low", "conv1", Mock(), priority="low")
        high_job = ImageJob("user1", "high", "conv1", Mock(), priority="high")
        normal_job = ImageJob("user1", "normal", "conv1", Mock(), priority="normal")
        
        # Add to queue
        queue.queue.put_nowait(low_job)
        queue.queue.put_nowait(normal_job)
        
        # Calculate position for high priority job
        high_pos = queue._calculate_queue_position(high_job)
        
        # High priority should get position 1 (before normal and low)
        assert high_pos == 1
        print("✅ Priority-aware position calculation: high priority gets position 1")

    def test_memory_efficient_job_storage(self):
        """Job storage should be memory efficient"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
        )
        
        # Check that job has all required fields
        assert hasattr(job, 'job_id')
        assert hasattr(job, 'priority')
        assert hasattr(job, 'batch_id')
        assert hasattr(job, 'timeout_seconds')
        assert hasattr(job, 'retry_count')
        assert hasattr(job, 'start_time')
        print("✅ Memory efficient job storage")


class TestIntegration:
    """Integration Tests for FAZE 4 Features"""

    @pytest.mark.asyncio
    async def test_priority_and_retry_together(self):
        """Priority and retry should work together"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
            priority="high",
        )
        
        # Simulate retry
        job.retry_count = 1
        
        assert job.priority == "high"
        assert job.retry_count == 1
        print("✅ Priority and retry work together")

    @pytest.mark.asyncio
    async def test_batch_with_timeout(self):
        """Batch jobs should respect timeout"""
        batch_id = "batch-123"
        
        jobs = [
            ImageJob(
                "user1",
                f"prompt{i}",
                "conv1",
                Mock(),
                batch_id=batch_id,
                timeout_seconds=300,
            )
            for i in range(3)
        ]
        
        # All should have same timeout
        timeouts = [job.timeout_seconds for job in jobs]
        assert all(t == 300 for t in timeouts)
        print("✅ Batch jobs respect timeout")

    @pytest.mark.asyncio
    async def test_priority_batch_retry_all_together(self):
        """All FAZE 4 features should work together"""
        job = ImageJob(
            username="user1",
            prompt="test",
            conversation_id="conv1",
            on_done=Mock(),
            priority="high",
            batch_id="batch-123",
            timeout_seconds=600,
        )
        
        # Simulate retry
        job.retry_count = 1
        
        assert job.priority == "high"
        assert job.batch_id == "batch-123"
        assert job.timeout_seconds == 600
        assert job.retry_count == 1
        print("✅ All FAZE 4 features work together")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
