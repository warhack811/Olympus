# PHASE 1: Quick Start Guide

## 🚀 Start Here

This is the fastest way to get Phase 1 done. Follow these steps in order.

---

## Step 1: Understand the Problem (5 minutes)

**Current Problem**:
- When updating message metadata, old fields get overwritten
- Example: Update progress → queue_position gets deleted
- Result: Data loss in concurrent updates

**Solution**:
- Use deep merge instead of overwrite
- Preserve existing fields when updating
- Add new fields without deleting old ones

**Code Example**:
```python
# ❌ WRONG (overwrites)
msg.extra_metadata = {"progress": 50}  # queue_position deleted!

# ✅ RIGHT (deep merge)
msg.extra_metadata = {
    **msg.extra_metadata,  # Keep existing
    "progress": 50         # Add/update new
}
```

---

## Step 2: Implement Deep Merge (30 minutes)

### File: `app/memory/conversation.py`

**Find this function**:
```python
def update_message(message_id, new_content=None, new_metadata=None):
    msg = session.get(Message, message_id)
    if new_metadata:
        msg.extra_metadata = new_metadata  # ❌ PROBLEM
    if new_content:
        msg.content = new_content
    session.commit()
```

**Replace with this**:
```python
def update_message(message_id, new_content=None, new_metadata=None):
    """Update message with deep merge for metadata"""
    msg = session.get(Message, message_id)
    if not msg:
        raise ValueError(f"Message {message_id} not found")
    
    # Deep merge metadata
    existing_metadata = msg.extra_metadata or {}
    merged_metadata = {
        **existing_metadata,
        **(new_metadata or {})
    }
    
    msg.extra_metadata = merged_metadata
    if new_content is not None:
        msg.content = new_content
    
    msg.updated_at = datetime.utcnow()
    session.commit()
    return msg
```

**Verify**: Function now merges instead of overwrites ✅

---

## Step 3: Persist All Fields in flux_stub.py (45 minutes)

### File: `app/image/flux_stub.py`

**Find this section** (around line 50-100):
```python
async def generate_image_via_forge(prompt: str, job, checkpoint_name=None):
    # ... code ...
    # ❌ PROBLEM: No persistence!
```

**Add this at the start** (when job starts processing):
```python
    # Mark as processing
    await update_message(job.message_id, None, {
        "status": "processing",
        "progress": 0,
        "queue_position": 0,
        "job_id": job.job_id,
        "prompt": prompt
    })
```

**Add this during progress** (every 10%):
```python
    # During generation loop
    while job.progress < 100:
        progress = await get_progress()
        
        if progress > job.progress and progress % 10 == 0:
            await update_message(job.message_id, None, {
                "status": "processing",
                "progress": progress
            })
        
        await asyncio.sleep(1)
```

**Add this on success** (at the end):
```python
    # Success
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
```

**Add this on error** (in except block):
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
```

**Verify**: All status changes persist to DB ✅

---

## Step 4: Persist Queue Position in job_queue.py (30 minutes)

### File: `app/image/job_queue.py`

**Find this function**:
```python
async def add_job(self, job: ImageJob) -> None:
    job.queue_pos = len(self.queue._queue) + 1
    await self.queue.put(job)
    # ❌ PROBLEM: No persistence!
```

**Replace with this**:
```python
async def add_job(self, job: ImageJob) -> None:
    """Add job to queue and persist queue position"""
    # Calculate position
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
```

**Also find** `_process_single_job()` and add at the start:
```python
    # Mark as processing
    await update_message(job.message_id, None, {
        "status": "processing",
        "progress": 0,
        "queue_position": 0
    })
```

**Verify**: Queue position persisted when job added ✅

---

## Step 5: Write Unit Tests (45 minutes)

### File: `tests/test_message_persistence.py` (NEW)

**Create this file** with these tests:

```python
import pytest
from app.memory.conversation import update_message
from app.core.models import Message
from app.core.database import get_session

@pytest.fixture
def session():
    return get_session()

@pytest.fixture
def test_message(session):
    msg = Message(
        conversation_id="test",
        role="bot",
        content="[IMAGE_PENDING]",
        extra_metadata={
            "status": "queued",
            "progress": 0,
            "queue_position": 1
        }
    )
    session.add(msg)
    session.commit()
    return msg

def test_deep_merge_preserves_fields(session, test_message):
    """Existing fields should be preserved"""
    update_message(test_message.id, None, {"progress": 50})
    
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["progress"] == 50
    assert msg.extra_metadata["queue_position"] == 1

def test_deep_merge_adds_fields(session, test_message):
    """New fields should be added"""
    update_message(test_message.id, None, {
        "job_id": "test-123",
        "prompt": "test"
    })
    
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["job_id"] == "test-123"
    assert msg.extra_metadata["prompt"] == "test"
    assert msg.extra_metadata["status"] == "queued"

def test_deep_merge_overwrites_field(session, test_message):
    """Existing fields should be overwritten"""
    update_message(test_message.id, None, {"status": "processing"})
    
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["status"] == "processing"

def test_deep_merge_concurrent(session, test_message):
    """Concurrent updates should not lose data"""
    update_message(test_message.id, None, {"progress": 50})
    update_message(test_message.id, None, {"queue_position": 0})
    
    msg = session.get(Message, test_message.id)
    assert msg.extra_metadata["progress"] == 50
    assert msg.extra_metadata["queue_position"] == 0
    assert msg.extra_metadata["status"] == "queued"
```

**Run tests**:
```bash
pytest tests/test_message_persistence.py -v
```

**Expected**: All 4 tests pass ✅

---

## Step 6: Write Integration Tests (45 minutes)

### File: `tests/test_image_persistence_integration.py` (NEW)

**Create this file** with these tests:

```python
import pytest
import asyncio
from app.image.job_queue import ImageJob, job_queue
from app.memory.conversation import update_message, append_message
from app.core.models import Message
from app.core.database import get_session

@pytest.fixture
async def test_conversation():
    from app.core.models import Conversation
    conv = Conversation(user_id=1, title="Test")
    session = get_session()
    session.add(conv)
    session.commit()
    return conv

@pytest.mark.asyncio
async def test_persistence_queued(test_conversation):
    """Job queued → message persisted"""
    session = get_session()
    
    msg = append_message(
        username="test",
        conversation_id=test_conversation.id,
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    job = ImageJob(
        username="test",
        prompt="test",
        conversation_id=test_conversation.id,
        on_done=lambda x: None,
        message_id=msg.id
    )
    
    await job_queue.add_job(job)
    
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "queued"
    assert msg.extra_metadata["queue_position"] == 1

@pytest.mark.asyncio
async def test_persistence_processing(test_conversation):
    """Job processing → message updated"""
    session = get_session()
    
    msg = append_message(
        username="test",
        conversation_id=test_conversation.id,
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    await update_message(msg.id, None, {
        "status": "processing",
        "progress": 0,
        "queue_position": 0
    })
    
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "processing"

@pytest.mark.asyncio
async def test_persistence_complete(test_conversation):
    """Job complete → image_url persisted"""
    session = get_session()
    
    msg = append_message(
        username="test",
        conversation_id=test_conversation.id,
        role="bot",
        content="[IMAGE_PENDING]"
    )
    
    image_url = "/images/flux_test.png"
    await update_message(msg.id,
        content=f"[IMAGE] Ready\nIMAGE_PATH: {image_url}",
        new_metadata={
            "status": "complete",
            "image_url": image_url,
            "progress": 100
        }
    )
    
    msg = session.get(Message, msg.id)
    assert msg.extra_metadata["status"] == "complete"
    assert msg.extra_metadata["image_url"] == image_url
```

**Run tests**:
```bash
pytest tests/test_image_persistence_integration.py -v
```

**Expected**: All 3 tests pass ✅

---

## Step 7: Verify Everything Works (15 minutes)

### Run All Tests
```bash
# Run all Phase 1 tests
pytest tests/test_message_persistence.py tests/test_image_persistence_integration.py -v

# Expected output:
# test_deep_merge_preserves_fields PASSED
# test_deep_merge_adds_fields PASSED
# test_deep_merge_overwrites_field PASSED
# test_deep_merge_concurrent PASSED
# test_persistence_queued PASSED
# test_persistence_processing PASSED
# test_persistence_complete PASSED
# ======================== 7 passed in 2.34s ========================
```

### Manual Testing
1. Start the app
2. Submit an image request
3. Check database: `SELECT extra_metadata FROM messages WHERE id=X`
4. Verify all fields present: status, progress, queue_position, job_id, prompt
5. Refresh page
6. Verify message loads with all fields

---

## ✅ Phase 1 Complete Checklist

- [ ] Deep merge implemented in update_message()
- [ ] All update_message() calls include full metadata
- [ ] Queue position persisted at each state
- [ ] Unit tests written and passing (4/4)
- [ ] Integration tests written and passing (3/3)
- [ ] Manual testing verified
- [ ] No regressions in existing tests
- [ ] Code reviewed

---

## 🐛 Troubleshooting

### Tests Failing?

**Error**: `AttributeError: 'NoneType' object has no attribute 'extra_metadata'`
- **Cause**: Message not found in database
- **Fix**: Check message_id is correct

**Error**: `AssertionError: 'queued' != 'processing'`
- **Cause**: Status not updated correctly
- **Fix**: Check update_message() is called with correct status

**Error**: `KeyError: 'queue_position'`
- **Cause**: Field not persisted
- **Fix**: Check update_message() includes queue_position

### App Not Starting?

**Error**: `ImportError: cannot import name 'update_message'`
- **Cause**: Function not found
- **Fix**: Check function is in conversation.py

**Error**: `TypeError: update_message() missing required argument`
- **Cause**: Function signature changed
- **Fix**: Check all calls pass correct arguments

---

## 📊 Progress Tracking

| Task | Status | Time | Notes |
|------|--------|------|-------|
| 1.1 Deep merge | ⏳ | 30m | Implement in conversation.py |
| 1.2 Persist fields | ⏳ | 45m | Update flux_stub.py |
| 1.3 Queue position | ⏳ | 30m | Update job_queue.py |
| 1.4 Unit tests | ⏳ | 45m | Create test_message_persistence.py |
| 1.5 Integration tests | ⏳ | 45m | Create test_image_persistence_integration.py |
| Verification | ⏳ | 15m | Run all tests + manual testing |
| **TOTAL** | ⏳ | **3-4h** | Ready for Phase 2 |

---

## 🎯 Next Steps

After Phase 1 is complete:

1. ✅ Phase 1 done
2. ⏳ Start Phase 2: Queue Position Dynamic Calculation
3. ⏳ Start Phase 3: Stuck Job Detection
4. ⏳ Start Phase 4: Concurrent Submission
5. ⏳ Comprehensive testing
6. ⏳ Production deployment

---

## 💡 Tips

- **Test as you go**: Don't wait until the end to test
- **Use git**: Commit after each task
- **Ask for help**: If stuck, ask team members
- **Document changes**: Add comments explaining why
- **Keep it simple**: Don't over-engineer
- **Follow the plan**: Don't deviate from the spec

---

**Ready to start? Begin with Step 1 above! 🚀**

