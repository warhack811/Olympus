# PHASE 1: Message Persistence & Deep Merge - Detailed Tasks

## Overview

Phase 1 is the foundation for all other fixes. It ensures:
- No data loss in concurrent updates (deep merge)
- All image status fields persisted to database
- Page reload recovery works
- Queue position persisted at each state

**Duration**: 3-4 hours
**Files Modified**: 3 (conversation.py, flux_stub.py, job_queue.py)
**Tests Created**: 2 (unit + integration)
**Risk**: LOW

---

## Task 1.1: Implement Deep Merge in update_message()

### File: `app/memory/conversation.py`

### Current Implementation (PROBLEM)
```python
def update_message(message_id, new_content=None, new_metadata=None):
    msg = session.get(Message, message_id)
    
    # ❌ PROBLEM: Overwrites entire metadata
    if new_metadata:
        msg.extra_metadata = new_metadata  # Data loss!
    
    if new_content:
        msg.content = new_content
    
    session.commit()
```

### New Implementation (SOLUTION)
```python
def update_message(message_id, new_content=None, new_metadata=None):
    """
    Update message content and/or metadata with deep merge.
    
    Args:
        message_id: Message ID to update
        new_content: New content (optional, if None content unchanged)
        new_metadata: New metadata fields (optional, merged with existing)
    
    Returns:
        Updated Message object
    
    Raises:
        ValueError: If message not found
    """
    msg = session.get(Message, message_id)
    if not msg:
        raise ValueError(f"Message {message_id} not found")
    
    # Deep merge metadata
    existing_metadata = msg.extra_metadata or {}
    merged_metadata = {
        **existing_metadata,
        **(new_metadata or {})
    }
    
    # Update fields
    msg.extra_metadata = merged_metadata
    if new_content is not None:
        msg.content = new_content
    
    # Update timestamp
    msg.updated_at = datetime.utcnow()
    
    session.commit()
    return msg
```

### Testing

**Unit Test**: `tests/test_message_persistence.py`

```python
def test_deep_merge_preserves_existing_fields():
    """Existing metadata fields should be preserved"""
    msg = create_test_message(extra_metadata={
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    })
    
    # Update only progress
    update_message(msg.id, None, {"progress": 50})
    
    # Verify all fields preserved
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["progress"] == 50
    assert msg.extra_metadata["queue_position"] == 1

def test_deep_merge_adds_new_fields():
    """New fields should be added without overwriting"""
    msg = create_test_message(extra_metadata={
        "status": "queued"
    })
    
    # Add new fields
    update_message(msg.id, None, {
        "progress": 0,
        "queue_position": 1
    })
    
    # Verify all fields present
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["progress"] == 0
    assert msg.extra_metadata["queue_position"] == 1

def test_deep_merge_concurrent_updates():
    """Concurrent updates should not lose data"""
    msg = create_test_message(extra_metadata={
        "status": "queued",
        "progress": 0
    })
    
    # Simulate concurrent updates
    update_message(msg.id, None, {"progress": 50})
    update_message(msg.id, None, {"queue_position": 1})
    
    # Verify no data loss
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["progress"] == 50
    assert msg.extra_metadata["queue_position"] == 1
```

### Acceptance Criteria
- ✅ Existing metadata fields preserved
- ✅ New fields added without overwriting
- ✅ Concurrent updates don't lose data
- ✅ Timestamp updated
- ✅ All unit tests pass

---

## Task 1.2: Persist All Image Status Fields

### File: `app/image/flux_stub.py`

### Current Implementation (PROBLEM)
```python
async def generate_image_via_forge(prompt: str, job, checkpoint_name=None):
    # ❌ PROBLEM: Only updates progress, not status
    await send_image_progress(
        job_id=job.job_id,
        progress=progress_value
    )
    
    # ❌ PROBLEM: Doesn't persist to DB
    # No update_message() call!
```

### New Implementation (SOLUTION)

#### 1. When Job Starts Processing
```python
async def generate_image_via_forge(prompt: str, job, checkpoint_name=None):
    """Generate image via Forge API with full persistence"""
    
    # 1. Mark as processing
    await update_message(job.message_id, None, {
        "status": "processing",
        "progress": 0,
        "queue_position": 0,  # No longer in queue
        "job_id": job.job_id,
        "prompt": prompt
    })
    
    await send_image_progress(
        username=job.username,
        conversation_id=job.conversation_id,
        job_id=job.job_id,
        status=ImageJobStatus.PROCESSING,
        progress=0,
        queue_position=0,
        prompt=prompt,
        message_id=job.message_id
    )
```

#### 2. During Progress Updates
```python
    # During generation, update progress every 10%
    while job.progress < 100:
        progress = await get_progress()
        
        if progress > job.progress and progress % 10 == 0:
            # Persist progress
            await update_message(job.message_id, None, {
                "status": "processing",
                "progress": progress
            })
            
            await send_image_progress(
                username=job.username,
                conversation_id=job.conversation_id,
                job_id=job.job_id,
                status=ImageJobStatus.PROCESSING,
                progress=progress,
                message_id=job.message_id
            )
        
        await asyncio.sleep(1)
```

#### 3. On Completion
```python
    # Success - persist image URL
    image_url = f"/images/flux_{job.job_id}.png"
    
    await update_message(job.message_id, 
        content=f"[IMAGE] Resminiz hazır.\nIMAGE_PATH: {image_url}",
        new_metadata={
            "status": "complete",
            "progress": 100,
            "image_url": image_url,
            "queue_position": 0
        }
    )
    
    await send_image_progress(
        username=job.username,
        conversation_id=job.conversation_id,
        job_id=job.job_id,
        status=ImageJobStatus.COMPLETE,
        progress=100,
        image_url=image_url,
        message_id=job.message_id
    )
```

#### 4. On Error
```python
    except TimeoutError:
        error_msg = "Forge API zaman aşımına uğradı (180s). Lütfen tekrar deneyin."
        
        await update_message(job.message_id,
            content=f"❌ Görsel oluşturulamadı: {error_msg}",
            new_metadata={
                "status": "error",
                "error": error_msg,
                "progress": 0,
                "queue_position": 0
            }
        )
        
        await send_image_progress(
            username=job.username,
            conversation_id=job.conversation_id,
            job_id=job.job_id,
            status=ImageJobStatus.ERROR,
            error=error_msg,
            message_id=job.message_id
        )
```

### Testing

**Integration Test**: `tests/test_image_persistence_integration.py`

```python
async def test_persistence_on_processing():
    """Message should be persisted when job starts processing"""
    msg = create_test_message()
    job = create_test_job(message_id=msg.id)
    
    # Simulate processing start
    await generate_image_via_forge("test prompt", job)
    
    # Verify persistence
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "processing"
    assert msg.extra_metadata["progress"] == 0
    assert msg.extra_metadata["queue_position"] == 0

async def test_persistence_on_completion():
    """Message should be persisted with image_url on completion"""
    msg = create_test_message()
    job = create_test_job(message_id=msg.id)
    
    # Simulate completion
    await generate_image_via_forge("test prompt", job)
    
    # Verify persistence
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "complete"
    assert msg.extra_metadata["image_url"] is not None
    assert msg.extra_metadata["progress"] == 100

async def test_persistence_on_error():
    """Message should be persisted with error on failure"""
    msg = create_test_message()
    job = create_test_job(message_id=msg.id)
    
    # Simulate error (mock Forge API timeout)
    with patch('app.image.flux_stub.generate_image_via_forge') as mock:
        mock.side_effect = TimeoutError()
        
        try:
            await generate_image_via_forge("test prompt", job)
        except:
            pass
    
    # Verify persistence
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "error"
    assert msg.extra_metadata["error"] is not None
```

### Acceptance Criteria
- ✅ Status persisted at each state change
- ✅ Progress persisted every 10%
- ✅ Queue position persisted when queued
- ✅ Image URL persisted on completion
- ✅ Error message persisted on error
- ✅ All integration tests pass

---

## Task 1.3: Update job_queue.py to Persist Queue Position

### File: `app/image/job_queue.py`

### Current Implementation (PROBLEM)
```python
async def add_job(self, job: ImageJob) -> None:
    # ❌ PROBLEM: Queue position calculated but not persisted
    job.queue_pos = len(self.queue._queue) + 1
    
    await self.queue.put(job)
    
    # ❌ PROBLEM: No update_message() call!
```

### New Implementation (SOLUTION)

```python
async def add_job(self, job: ImageJob) -> None:
    """
    Add job to queue and persist queue position to database.
    
    Args:
        job: ImageJob to add
    """
    # Calculate queue position
    job.queue_pos = self.queue.qsize() + 1
    
    # Persist to database
    await update_message(job.message_id, None, {
        "status": "queued",
        "progress": 0,
        "queue_position": job.queue_pos,
        "job_id": job.job_id,
        "prompt": job.prompt
    })
    
    # Send WebSocket notification
    await send_image_progress(
        username=job.username,
        conversation_id=job.conversation_id,
        job_id=job.job_id,
        status=ImageJobStatus.QUEUED,
        progress=0,
        queue_position=job.queue_pos,
        prompt=job.prompt,
        message_id=job.message_id
    )
    
    # Add to queue
    await self.queue.put(job)
    
    logger.info(f"[IMAGE_QUEUE] Job {job.job_id[:8]} queued at position {job.queue_pos}")
```

### When Job Starts Processing
```python
async def _process_single_job(self, job: ImageJob) -> None:
    """Process a single job"""
    
    # Mark as processing (queue_position = 0)
    await update_message(job.message_id, None, {
        "status": "processing",
        "progress": 0,
        "queue_position": 0
    })
    
    await send_image_progress(
        username=job.username,
        conversation_id=job.conversation_id,
        job_id=job.job_id,
        status=ImageJobStatus.PROCESSING,
        progress=0,
        queue_position=0,
        message_id=job.message_id
    )
    
    # Process job...
    result = await generate_image_via_forge(job.prompt, job)
```

### Testing

**Unit Test**: `tests/test_message_persistence.py`

```python
async def test_queue_position_persisted_on_add():
    """Queue position should be persisted when job added"""
    msg = create_test_message()
    job = create_test_job(message_id=msg.id)
    
    # Add to queue
    await job_queue.add_job(job)
    
    # Verify persistence
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["queue_position"] == 1

async def test_queue_position_updated_on_processing():
    """Queue position should be 0 when job starts processing"""
    msg = create_test_message()
    job = create_test_job(message_id=msg.id)
    
    # Add to queue
    await job_queue.add_job(job)
    
    # Start processing
    await job_queue._process_single_job(job)
    
    # Verify persistence
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "processing"
    assert msg.extra_metadata["queue_position"] == 0
```

### Acceptance Criteria
- ✅ Queue position persisted when job added
- ✅ Queue position updated when job starts
- ✅ Remaining jobs' positions updated
- ✅ All unit tests pass

---

## Task 1.4: Create Unit Tests for Deep Merge

### File: `tests/test_message_persistence.py` (new)

```python
import pytest
from datetime import datetime
from app.memory.conversation import update_message
from app.core.models import Message
from app.core.database import get_session

@pytest.fixture
def session():
    """Get test database session"""
    return get_session()

@pytest.fixture
def test_message(session):
    """Create test message"""
    msg = Message(
        conversation_id="test-conv",
        role="bot",
        content="[IMAGE_PENDING]",
        extra_metadata={
            "type": "image",
            "status": "queued",
            "progress": 0,
            "queue_position": 1
        }
    )
    session.add(msg)
    session.commit()
    return msg

def test_deep_merge_preserves_existing_fields(session, test_message):
    """Existing metadata fields should be preserved"""
    # Update only progress
    update_message(test_message.id, None, {"progress": 50})
    
    # Verify all fields preserved
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["progress"] == 50
    assert msg.extra_metadata["queue_position"] == 1

def test_deep_merge_adds_new_fields(session, test_message):
    """New fields should be added without overwriting"""
    # Add new fields
    update_message(test_message.id, None, {
        "job_id": "test-job-123",
        "prompt": "test prompt"
    })
    
    # Verify all fields present
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["progress"] == 0
    assert msg.extra_metadata["queue_position"] == 1
    assert msg.extra_metadata["job_id"] == "test-job-123"
    assert msg.extra_metadata["prompt"] == "test prompt"

def test_deep_merge_overwrites_existing_field(session, test_message):
    """Existing fields should be overwritten if provided"""
    # Update status
    update_message(test_message.id, None, {"status": "processing"})
    
    # Verify field overwritten
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["status"] == "processing"
    assert msg.extra_metadata["progress"] == 0
    assert msg.extra_metadata["queue_position"] == 1

def test_deep_merge_with_content_update(session, test_message):
    """Content and metadata should both update"""
    # Update both
    update_message(test_message.id, 
        content="[IMAGE] New content",
        new_metadata={"status": "complete"}
    )
    
    # Verify both updated
    msg = session.get(Message, test_message.id)
    assert msg.content == "[IMAGE] New content"
    assert msg.extra_metadata["status"] == "complete"
    assert msg.extra_metadata["progress"] == 0

def test_deep_merge_null_metadata(session, test_message):
    """Null metadata should not cause errors"""
    # Update with None metadata
    update_message(test_message.id, None, None)
    
    # Verify unchanged
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["status"] == "queued"

def test_deep_merge_empty_metadata(session, test_message):
    """Empty metadata should not cause errors"""
    # Update with empty metadata
    update_message(test_message.id, None, {})
    
    # Verify unchanged
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["status"] == "queued"

def test_deep_merge_timestamp_updated(session, test_message):
    """Updated_at timestamp should be updated"""
    original_time = test_message.updated_at
    
    # Wait a bit
    import time
    time.sleep(0.1)
    
    # Update
    update_message(test_message.id, None, {"progress": 50})
    
    # Verify timestamp updated
    msg = session.get(Message, test_message.id)
    assert msg.updated_at > original_time
```

### Acceptance Criteria
- ✅ All 8 test cases pass
- ✅ 100% code coverage for update_message()
- ✅ No data loss scenarios

---

## Task 1.5: Create Integration Tests for Message Persistence

### File: `tests/test_image_persistence_integration.py` (new)

```python
import pytest
import asyncio
from app.image.job_queue import ImageJob, job_queue
from app.image.flux_stub import generate_image_via_forge
from app.memory.conversation import update_message, append_message
from app.core.models import Message
from app.core.database import get_session

@pytest.fixture
async def session():
    """Get test database session"""
    return get_session()

@pytest.fixture
async def test_conversation(session):
    """Create test conversation"""
    from app.core.models import Conversation
    conv = Conversation(
        user_id=1,
        title="Test Conversation"
    )
    session.add(conv)
    session.commit()
    return conv

async def test_persistence_job_queued(session, test_conversation):
    """Job queued → message persisted with status/progress/queue_position"""
    # Create message
    msg = append_message(
        username="test_user",
        conversation_id=test_conversation.id,
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    # Create job
    job = ImageJob(
        username="test_user",
        prompt="test prompt",
        conversation_id=test_conversation.id,
        on_done=lambda x: None,
        message_id=msg.id
    )
    
    # Add to queue
    await job_queue.add_job(job)
    
    # Verify persistence
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["progress"] == 0
    assert msg.extra_metadata["queue_position"] == 1
    assert msg.extra_metadata["job_id"] == job.job_id
    assert msg.extra_metadata["prompt"] == "test prompt"

async def test_persistence_job_processing(session, test_conversation):
    """Job processing → message updated with status/progress"""
    # Create message
    msg = append_message(
        username="test_user",
        conversation_id=test_conversation.id,
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    # Create job
    job = ImageJob(
        username="test_user",
        prompt="test prompt",
        conversation_id=test_conversation.id,
        on_done=lambda x: None,
        message_id=msg.id
    )
    
    # Simulate processing
    await update_message(msg.id, None, {
        "status": "processing",
        "progress": 0,
        "queue_position": 0
    })
    
    # Verify persistence
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "processing"
    assert msg.extra_metadata["progress"] == 0
    assert msg.extra_metadata["queue_position"] == 0

async def test_persistence_job_complete(session, test_conversation):
    """Job complete → message updated with image_url"""
    # Create message
    msg = append_message(
        username="test_user",
        conversation_id=test_conversation.id,
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    # Simulate completion
    image_url = "/images/flux_test.png"
    await update_message(msg.id,
        content=f"[IMAGE] Resminiz hazır.\nIMAGE_PATH: {image_url}",
        new_metadata={
            "status": "complete",
            "progress": 100,
            "image_url": image_url
        }
    )
    
    # Verify persistence
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "complete"
    assert msg.extra_metadata["image_url"] == image_url
    assert msg.extra_metadata["progress"] == 100

async def test_persistence_page_reload(session, test_conversation):
    """Page reload → message loaded from DB with all fields"""
    # Create message with full metadata
    msg = append_message(
        username="test_user",
        conversation_id=test_conversation.id,
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    # Persist full metadata
    await update_message(msg.id, None, {
        "status": "processing",
        "progress": 50,
        "queue_position": 0,
        "job_id": "test-job-123",
        "prompt": "test prompt"
    })
    
    # Simulate page reload (new session)
    new_session = get_session()
    loaded_msg = new_session.get(Message, msg.id)
    
    # Verify all fields loaded
    assert loaded_msg.extra_metadata["status"] == "processing"
    assert loaded_msg.extra_metadata["progress"] == 50
    assert loaded_msg.extra_metadata["queue_position"] == 0
    assert loaded_msg.extra_metadata["job_id"] == "test-job-123"
    assert loaded_msg.extra_metadata["prompt"] == "test prompt"

async def test_persistence_concurrent_updates(session, test_conversation):
    """Concurrent updates → no data loss"""
    # Create message
    msg = append_message(
        username="test_user",
        conversation_id=test_conversation.id,
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    # Simulate concurrent updates
    await update_message(msg.id, None, {
        "status": "processing",
        "progress": 50
    })
    
    await update_message(msg.id, None, {
        "queue_position": 0
    })
    
    # Verify no data loss
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "processing"
    assert msg.extra_metadata["progress"] == 50
    assert msg.extra_metadata["queue_position"] == 0
```

### Acceptance Criteria
- ✅ All 5 scenarios pass
- ✅ Database state verified after each step
- ✅ Page reload recovery works
- ✅ No data loss in concurrent scenarios

---

## Phase 1 Verification Checklist

Before moving to Phase 2, verify:

- [ ] Deep merge implemented in update_message()
- [ ] All update_message() calls include full metadata
- [ ] Queue position persisted at each state
- [ ] Unit tests pass (8/8)
- [ ] Integration tests pass (5/5)
- [ ] No data loss in concurrent scenarios
- [ ] Page reload recovery verified
- [ ] Code reviewed and approved
- [ ] No regressions in existing tests

---

## Files Modified Summary

| File | Changes | Lines | Risk |
|------|---------|-------|------|
| app/memory/conversation.py | Deep merge in update_message() | 20 | LOW |
| app/image/flux_stub.py | Persist all fields at each state | 50 | LOW |
| app/image/job_queue.py | Persist queue position | 30 | LOW |
| tests/test_message_persistence.py | New unit tests | 150 | N/A |
| tests/test_image_persistence_integration.py | New integration tests | 200 | N/A |

**Total Changes**: ~450 lines
**Total Tests**: 13 (8 unit + 5 integration)

