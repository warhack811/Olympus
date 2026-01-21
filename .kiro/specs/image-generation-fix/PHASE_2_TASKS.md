# FAZE 2: Implementation Tasks - Concurrent Job Handling

## Overview

FAZE 2, GPU lock mekanizması ve concurrent job handling'i implement eder. Tüm task'lar FAZE 1'in üzerine inşa edilir.

**Total Tasks**: 8
**Estimated Time**: 5-6 hours
**Test Coverage**: 30+ test cases

---

## Task 2.1: Implement GPU Lock Mechanism

**File**: `app/image/job_queue.py`
**Dependency**: FAZE 1 complete
**Time**: 1 hour

### Objective
GPU'nun aynı anda sadece bir job tarafından kullanılmasını sağlayan lock mekanizması implement etmek.

### Implementation

```python
class ImageJobQueue:
    def __init__(self):
        self._queue: asyncio.Queue[ImageJob] = asyncio.Queue()
        self._gpu_lock: asyncio.Lock = asyncio.Lock()  # GPU lock
        self._worker_task: asyncio.Task = None
        self._started: bool = False
        self._current_job: ImageJob = None
        self._total_queued_tasks: int = 0
    
    async def _worker_loop(self):
        """Main worker loop - processes jobs sequentially with GPU lock"""
        while True:
            job = await self._queue.get()
            
            # Acquire GPU lock (only one job at a time)
            async with self._gpu_lock:
                self._current_job = job
                try:
                    await self._process_single_job(job)
                finally:
                    self._current_job = None
            
            self._queue.task_done()
    
    async def _process_single_job(self, job: ImageJob):
        """Process a single job with GPU lock held"""
        logger.info(f"[GPU_LOCK] Acquired for job {job.job_id[:8]}")
        
        try:
            # Update status to processing
            from app.memory.conversation import update_message
            if job.message_id:
                await update_message(job.message_id, None, {
                    "status": "processing",
                    "progress": 0,
                    "queue_position": 0
                })
            
            # Generate image (GPU lock held)
            image_url = await generate_image_via_forge(
                job.prompt,
                job,
                checkpoint_name=job.checkpoint_name
            )
            
            job.on_done(image_url)
            
        except Exception as e:
            logger.error(f"[GPU_LOCK] Error in job {job.job_id[:8]}: {e}")
            # Error handling (see Task 2.5)
            raise
        finally:
            logger.info(f"[GPU_LOCK] Released for job {job.job_id[:8]}")
```

### Acceptance Criteria
- ✅ GPU lock acquired before processing
- ✅ GPU lock released after processing
- ✅ Only one job processes at a time
- ✅ Lock timeout after 30 seconds
- ✅ Lock released on error

### Testing
- Unit test: GPU lock prevents concurrent processing
- Unit test: GPU lock released on completion
- Unit test: GPU lock released on error

---

## Task 2.2: Implement Concurrent Job Queue Management

**File**: `app/image/job_queue.py`
**Dependency**: Task 2.1
**Time**: 1 hour

### Objective
Birden fazla job'u kuyruğa alıp sırayla işlemek.

### Implementation

```python
class ImageJobQueue:
    def add_job(self, job: ImageJob) -> int:
        """Add job to queue and persist queue position"""
        self._ensure_worker_started()
        
        # Calculate queue position
        queue_pos = self._queue.qsize() + 1
        self._total_queued_tasks += 1
        job.queue_pos = queue_pos
        
        # Persist to database
        from app.memory.conversation import update_message
        if job.message_id:
            update_message(job.message_id, None, {
                "status": "queued",
                "progress": 0,
                "queue_position": queue_pos,
                "job_id": job.job_id,
                "prompt": job.prompt
            })
        
        # Send WebSocket notification
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_queued_status(job, queue_pos))
        except RuntimeError:
            pass
        
        # Add to queue
        self._queue.put_nowait(job)
        
        logger.info(f"[IMAGE_QUEUE] Job {job.job_id[:8]} queued at position {queue_pos}")
        return queue_pos
    
    async def _send_queued_status(self, job: ImageJob, queue_pos: int):
        """Send queued status via WebSocket"""
        from app.core.websockets import send_image_progress, ImageJobStatus
        
        try:
            await send_image_progress(
                username=job.username,
                conversation_id=job.conversation_id,
                job_id=job.job_id,
                status=ImageJobStatus.QUEUED,
                progress=0,
                queue_position=queue_pos,
                prompt=job.prompt,
                message_id=job.message_id,
                estimated_seconds=queue_pos * 30
            )
        except Exception as e:
            logger.debug(f"[IMAGE_QUEUE] WebSocket notification failed: {e}")
```

### Acceptance Criteria
- ✅ Multiple jobs queued with unique positions
- ✅ Queue position persisted to database
- ✅ WebSocket notification sent
- ✅ Jobs processed in FIFO order
- ✅ Queue position calculated correctly

### Testing
- Unit test: Multiple jobs get unique positions
- Unit test: Queue position persisted
- Integration test: Jobs processed in order

---

## Task 2.3: Implement State Transitions

**File**: `app/image/flux_stub.py`
**Dependency**: Task 2.1
**Time**: 1 hour

### Objective
Job'ların tüm state geçişlerini doğru şekilde handle etmek.

### Implementation

```python
async def generate_image_via_forge(prompt: str, job, checkpoint_name: str = None) -> str:
    """Generate image with proper state transitions"""
    
    # State 1: Processing started
    from app.memory.conversation import update_message
    if job.message_id:
        update_message(job.message_id, None, {
            "status": "processing",
            "progress": 1,
            "queue_position": 0,
            "job_id": job.job_id,
            "prompt": prompt
        })
    
    try:
        # Generate image...
        image_url = await _generate_image_internal(prompt, job, checkpoint_name)
        
        # State 2: Processing complete
        if job.message_id:
            update_message(job.message_id,
                content=f"[IMAGE] Resminiz hazır.\nIMAGE_PATH: {image_url}",
                new_metadata={
                    "status": "complete",
                    "progress": 100,
                    "image_url": image_url,
                    "queue_position": 0
                }
            )
        
        return image_url
        
    except TimeoutError as e:
        # State 3: Error - timeout
        if job.message_id:
            update_message(job.message_id,
                content=f"❌ Timeout: {str(e)}",
                new_metadata={
                    "status": "error",
                    "error": str(e),
                    "progress": 0,
                    "queue_position": 0
                }
            )
        raise
        
    except Exception as e:
        # State 3: Error - other
        if job.message_id:
            update_message(job.message_id,
                content=f"❌ Error: {str(e)}",
                new_metadata={
                    "status": "error",
                    "error": str(e),
                    "progress": 0,
                    "queue_position": 0
                }
            )
        raise
```

### Acceptance Criteria
- ✅ State transitions logged
- ✅ Status persisted at each transition
- ✅ Timestamp updated
- ✅ Error messages persisted
- ✅ WebSocket notifications sent

### Testing
- Unit test: State transitions valid
- Integration test: Status persisted correctly

---

## Task 2.4: Implement Error Recovery

**File**: `app/image/job_queue.py`
**Dependency**: Task 2.3
**Time**: 1 hour

### Objective
Bir job hata verirse sonraki job'un otomatik olarak işlenmesini sağlamak.

### Implementation

```python
async def _process_single_job(self, job: ImageJob):
    """Process job with error recovery"""
    logger.info(f"[IMAGE_QUEUE] Processing: {job.job_id[:8]}")
    
    try:
        # Generate image
        image_url = await generate_image_via_forge(
            job.prompt,
            job,
            checkpoint_name=job.checkpoint_name
        )
        
        # Success callback
        job.on_done(image_url)
        
    except Exception as e:
        logger.error(f"[IMAGE_QUEUE] Job error: {e}", exc_info=True)
        
        # Error callback
        from app.core.websockets import send_image_progress, ImageJobStatus
        
        try:
            await send_image_progress(
                username=job.username,
                conversation_id=job.conversation_id,
                job_id=job.job_id,
                status=ImageJobStatus.ERROR,
                progress=0,
                queue_position=0,
                prompt=job.prompt,
                error=str(e),
                message_id=job.message_id
            )
        except Exception as ws_err:
            logger.debug(f"[IMAGE_QUEUE] WebSocket error: {ws_err}")
        
        job.on_done(f"(IMAGE ERROR) {e}")
        
        # Next job will automatically start (worker loop continues)
    
    finally:
        # Always release GPU lock
        logger.info(f"[IMAGE_QUEUE] Completed: {job.job_id[:8]}")
```

### Acceptance Criteria
- ✅ Error logged with details
- ✅ Error persisted to database
- ✅ WebSocket error notification sent
- ✅ Next job automatically starts
- ✅ GPU lock released

### Testing
- Unit test: Error recovery works
- Integration test: Next job starts after error

---

## Task 2.5: Create Unit Tests for GPU Lock

**File**: `tests/test_gpu_lock.py` (new)
**Dependency**: Task 2.1
**Time**: 1 hour

### Test Cases

```python
import pytest
import asyncio
from app.image.job_queue import ImageJobQueue, ImageJob

@pytest.mark.asyncio
async def test_gpu_lock_prevents_concurrent_processing():
    """GPU lock should prevent concurrent job processing"""
    queue = ImageJobQueue()
    
    processing_times = []
    
    async def mock_process(job_id, duration):
        async with queue._gpu_lock:
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
    
    for job1 in ["job-1", "job-2", "job-3"]:
        for job2 in ["job-1", "job-2", "job-3"]:
            if job1 != job2:
                assert ends[job1] <= starts[job2] or ends[job2] <= starts[job1]

@pytest.mark.asyncio
async def test_gpu_lock_released_on_completion():
    """GPU lock should be released after job completion"""
    queue = ImageJobQueue()
    
    async def mock_job():
        async with queue._gpu_lock:
            await asyncio.sleep(0.1)
    
    # Run job
    await mock_job()
    
    # Lock should be available
    assert not queue._gpu_lock.locked()

@pytest.mark.asyncio
async def test_gpu_lock_released_on_error():
    """GPU lock should be released even on error"""
    queue = ImageJobQueue()
    
    async def mock_job_with_error():
        try:
            async with queue._gpu_lock:
                raise ValueError("Test error")
        except ValueError:
            pass
    
    # Run job with error
    await mock_job_with_error()
    
    # Lock should be available
    assert not queue._gpu_lock.locked()

@pytest.mark.asyncio
async def test_queue_position_calculation():
    """Queue position should be calculated correctly"""
    queue = ImageJobQueue()
    
    # Add 3 jobs
    jobs = []
    for i in range(3):
        job = ImageJob(
            username="test_user",
            prompt=f"prompt {i}",
            conversation_id="conv-1",
            on_done=lambda x: None,
            message_id=i+1
        )
        pos = queue.add_job(job)
        jobs.append((job, pos))
    
    # Verify positions
    assert jobs[0][1] == 1
    assert jobs[1][1] == 2
    assert jobs[2][1] == 3

@pytest.mark.asyncio
async def test_concurrent_job_processing():
    """Multiple jobs should be processed sequentially"""
    queue = ImageJobQueue()
    
    processed_jobs = []
    
    async def mock_process(job):
        async with queue._gpu_lock:
            processed_jobs.append(job.job_id)
            await asyncio.sleep(0.05)
    
    # Create 3 jobs
    jobs = []
    for i in range(3):
        job = ImageJob(
            username="test_user",
            prompt=f"prompt {i}",
            conversation_id="conv-1",
            on_done=lambda x: None,
            message_id=i+1
        )
        jobs.append(job)
    
    # Process all jobs
    await asyncio.gather(*[mock_process(job) for job in jobs])
    
    # All jobs should be processed
    assert len(processed_jobs) == 3
```

### Acceptance Criteria
- ✅ All 5 test cases pass
- ✅ GPU lock prevents concurrent processing
- ✅ GPU lock released on completion
- ✅ GPU lock released on error
- ✅ Queue position calculated correctly

---

## Task 2.6: Create Integration Tests for Concurrent Processing

**File**: `tests/test_concurrent_processing.py` (new)
**Dependency**: Tasks 2.1-2.5
**Time**: 1 hour

### Test Cases

```python
import pytest
import asyncio
from app.image.job_queue import ImageJobQueue, ImageJob
from app.memory.conversation import update_message, append_message
from app.core.models import Message, Conversation
from app.core.database import get_session

@pytest.mark.asyncio
async def test_multiple_jobs_queued_with_positions():
    """Multiple jobs should be queued with correct positions"""
    queue = ImageJobQueue()
    session = get_session()
    
    # Create conversation
    conv = Conversation(user_id=1, title="Test")
    session.add(conv)
    session.commit()
    
    # Create 3 messages
    messages = []
    for i in range(3):
        msg = append_message(
            username="test_user",
            conv_id=conv.id,
            role="bot",
            content="[IMAGE_PENDING]"
        )
        messages.append(msg)
    
    # Create 3 jobs
    jobs = []
    for i, msg in enumerate(messages):
        job = ImageJob(
            username="test_user",
            prompt=f"prompt {i}",
            conversation_id=conv.id,
            on_done=lambda x: None,
            message_id=msg.id
        )
        pos = queue.add_job(job)
        jobs.append((job, pos))
    
    # Verify positions persisted
    for i, (job, pos) in enumerate(jobs):
        msg = session.get(Message, job.message_id)
        assert msg.extra_metadata["queue_position"] == i + 1
        assert msg.extra_metadata["status"] == "queued"

@pytest.mark.asyncio
async def test_job_processing_updates_status():
    """Job processing should update status to processing"""
    queue = ImageJobQueue()
    session = get_session()
    
    # Create message
    msg = append_message(
        username="test_user",
        conv_id="conv-1",
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    # Simulate processing
    update_message(msg.id, None, {
        "status": "processing",
        "progress": 0,
        "queue_position": 0
    })
    
    # Verify status updated
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "processing"
    assert msg.extra_metadata["queue_position"] == 0

@pytest.mark.asyncio
async def test_error_recovery_starts_next_job():
    """Error in one job should not prevent next job from starting"""
    queue = ImageJobQueue()
    
    processed = []
    
    async def mock_process_with_error(job):
        processed.append(job.job_id)
        if len(processed) == 1:
            raise ValueError("Test error")
    
    # Create 2 jobs
    jobs = []
    for i in range(2):
        job = ImageJob(
            username="test_user",
            prompt=f"prompt {i}",
            conversation_id="conv-1",
            on_done=lambda x: None,
            message_id=i+1
        )
        jobs.append(job)
    
    # Process jobs (first fails, second succeeds)
    for job in jobs:
        try:
            await mock_process_with_error(job)
        except ValueError:
            pass
    
    # Both jobs should be processed
    assert len(processed) == 2

@pytest.mark.asyncio
async def test_concurrent_updates_no_data_loss():
    """Concurrent updates should not lose data"""
    session = get_session()
    
    # Create message
    msg = append_message(
        username="test_user",
        conv_id="conv-1",
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    # Simulate concurrent updates
    update_message(msg.id, None, {
        "status": "processing",
        "progress": 50
    })
    
    update_message(msg.id, None, {
        "queue_position": 0
    })
    
    # Verify no data loss
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "processing"
    assert msg.extra_metadata["progress"] == 50
    assert msg.extra_metadata["queue_position"] == 0
```

### Acceptance Criteria
- ✅ All 4 test cases pass
- ✅ Multiple jobs queued correctly
- ✅ Status updated during processing
- ✅ Error recovery works
- ✅ No data loss in concurrent updates

---

## Task 2.7: Create Component Tests for Frontend

**File**: `tests/test_queue_position_component.tsx` (new)
**Dependency**: FAZE 1 complete
**Time**: 1 hour

### Test Cases

```typescript
import { render, screen } from '@testing-library/react'
import { ImageProgressCard } from '@/components/chat/ImageProgressCard'

describe('ImageProgressCard - Queue Position', () => {
  it('should display queue position for queued jobs', () => {
    const job = {
      id: 'job-1',
      status: 'queued',
      queuePosition: 2,
      progress: 0,
      prompt: 'test'
    }
    
    render(<ImageProgressCard job={job} />)
    
    expect(screen.getByText(/Position: 2/)).toBeInTheDocument()
  })
  
  it('should update queue position dynamically', () => {
    const allJobs = [
      { id: 'job-1', status: 'queued', createdAt: new Date() },
      { id: 'job-2', status: 'queued', createdAt: new Date() },
      { id: 'job-3', status: 'queued', createdAt: new Date() }
    ]
    
    const calculatePosition = (jobId) => {
      const queuedJobs = allJobs
        .filter(j => j.status === 'queued')
        .sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime())
      
      return queuedJobs.findIndex(j => j.id === jobId) + 1
    }
    
    expect(calculatePosition('job-1')).toBe(1)
    expect(calculatePosition('job-2')).toBe(2)
    expect(calculatePosition('job-3')).toBe(3)
  })
  
  it('should show 0 for non-queued jobs', () => {
    const job = {
      id: 'job-1',
      status: 'processing',
      queuePosition: 0,
      progress: 50
    }
    
    render(<ImageProgressCard job={job} />)
    
    expect(screen.queryByText(/Position:/)).not.toBeInTheDocument()
  })
})
```

### Acceptance Criteria
- ✅ All 3 test cases pass
- ✅ Queue position displayed correctly
- ✅ Position updates dynamically
- ✅ Non-queued jobs show no position

---

## Task 2.8: Create E2E Tests

**File**: `tests/test_concurrent_e2e.ts` (new)
**Dependency**: All tasks complete
**Time**: 1 hour

### Test Scenarios

```typescript
import { test, expect } from '@playwright/test'

test.describe('Concurrent Job Processing E2E', () => {
  test('should process 3 jobs sequentially', async ({ page }) => {
    // Submit 3 jobs
    await page.goto('/chat')
    
    for (let i = 0; i < 3; i++) {
      await page.fill('[data-testid="prompt-input"]', `prompt ${i}`)
      await page.click('[data-testid="submit-button"]')
      await page.waitForTimeout(500)
    }
    
    // Verify all jobs queued with correct positions
    const positions = await page.locator('[data-testid="queue-position"]').allTextContents()
    expect(positions).toContain('Position: 1')
    expect(positions).toContain('Position: 2')
    expect(positions).toContain('Position: 3')
  })
  
  test('should update positions when job completes', async ({ page }) => {
    // Submit 3 jobs
    await page.goto('/chat')
    
    for (let i = 0; i < 3; i++) {
      await page.fill('[data-testid="prompt-input"]', `prompt ${i}`)
      await page.click('[data-testid="submit-button"]')
      await page.waitForTimeout(500)
    }
    
    // Wait for first job to complete
    await page.waitForSelector('[data-testid="job-complete"]', { timeout: 60000 })
    
    // Verify remaining jobs updated
    const positions = await page.locator('[data-testid="queue-position"]').allTextContents()
    expect(positions).toContain('Position: 1')
    expect(positions).toContain('Position: 2')
  })
  
  test('should recover from error and process next job', async ({ page }) => {
    // Submit 2 jobs
    await page.goto('/chat')
    
    for (let i = 0; i < 2; i++) {
      await page.fill('[data-testid="prompt-input"]', `prompt ${i}`)
      await page.click('[data-testid="submit-button"]')
      await page.waitForTimeout(500)
    }
    
    // Wait for first job to error (mock)
    await page.waitForSelector('[data-testid="job-error"]', { timeout: 10000 })
    
    // Verify second job starts processing
    await page.waitForSelector('[data-testid="job-processing"]', { timeout: 10000 })
  })
  
  test('should recover positions after page reload', async ({ page }) => {
    // Submit 3 jobs
    await page.goto('/chat')
    
    for (let i = 0; i < 3; i++) {
      await page.fill('[data-testid="prompt-input"]', `prompt ${i}`)
      await page.click('[data-testid="submit-button"]')
      await page.waitForTimeout(500)
    }
    
    // Reload page
    await page.reload()
    
    // Verify positions recovered from DB
    const positions = await page.locator('[data-testid="queue-position"]').allTextContents()
    expect(positions.length).toBeGreaterThan(0)
  })
})
```

### Acceptance Criteria
- ✅ All 4 E2E scenarios pass
- ✅ Jobs processed sequentially
- ✅ Positions update dynamically
- ✅ Error recovery works
- ✅ Page reload recovery works

---

## Verification Checklist

Before moving to FAZE 3:

- [ ] Task 2.1: GPU lock implemented
- [ ] Task 2.2: Concurrent queue management implemented
- [ ] Task 2.3: State transitions implemented
- [ ] Task 2.4: Error recovery implemented
- [ ] Task 2.5: GPU lock unit tests pass (5/5)
- [ ] Task 2.6: Integration tests pass (4/4)
- [ ] Task 2.7: Component tests pass (3/3)
- [ ] Task 2.8: E2E tests pass (4/4)
- [ ] Total: 16+ tests passing
- [ ] No regressions in FAZE 1 tests
- [ ] Code review approved
- [ ] Performance verified
- [ ] Production-ready

---

## Summary

| Task | Time | Tests | Status |
|------|------|-------|--------|
| 2.1 GPU Lock | 1h | 3 | ⏳ |
| 2.2 Queue Management | 1h | 3 | ⏳ |
| 2.3 State Transitions | 1h | 2 | ⏳ |
| 2.4 Error Recovery | 1h | 2 | ⏳ |
| 2.5 Unit Tests | 1h | 5 | ⏳ |
| 2.6 Integration Tests | 1h | 4 | ⏳ |
| 2.7 Component Tests | 1h | 3 | ⏳ |
| 2.8 E2E Tests | 1h | 4 | ⏳ |
| **TOTAL** | **8h** | **26** | **⏳** |

**Target**: 26+ tests passing, 0 regressions, production-ready code
