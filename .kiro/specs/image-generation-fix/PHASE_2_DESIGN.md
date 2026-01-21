# FAZE 2: Design Document - Concurrent Job Handling

## Overview

FAZE 2, birden fazla image generation job'unu concurrent olarak handle etmek için GPU lock mekanizması ve queue position persistence'ı implement eder.

**Architecture**: Async queue-based processing with GPU lock
**Language**: Python (backend), TypeScript (frontend)
**Database**: SQLModel with deep merge
**Testing**: Unit + Integration + Component + E2E

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ImageProgressCard                                   │   │
│  │  - calculateQueuePosition()                          │   │
│  │  - Display dynamic position                          │   │
│  │  - Real-time updates via WebSocket                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ImageJobQueue                                       │   │
│  │  - GPU Lock (asyncio.Lock)                           │   │
│  │  - Queue management                                  │   │
│  │  - Job processing loop                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  generate_image_via_forge()                          │   │
│  │  - State transitions                                 │   │
│  │  - Progress updates                                  │   │
│  │  - Error handling                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  update_message() (Deep Merge)                       │   │
│  │  - Persist status, progress, queue_position         │   │
│  │  - Concurrent update safety                          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ SQL
┌─────────────────────────────────────────────────────────────┐
│                   Database (SQLite/PostgreSQL)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Message.extra_metadata                              │   │
│  │  {                                                   │   │
│  │    "status": "queued|processing|complete|error",    │   │
│  │    "progress": 0-100,                                │   │
│  │    "queue_position": 1-N,                            │   │
│  │    "job_id": "uuid",                                 │   │
│  │    "prompt": "...",                                  │   │
│  │    "image_url": "...",                               │   │
│  │    "error": "..."                                    │   │
│  │  }                                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Components & Interfaces

### 1. ImageJobQueue (Backend)

```python
class ImageJobQueue:
    """Concurrent job queue with GPU lock"""
    
    def __init__(self):
        self._queue: asyncio.Queue[ImageJob] = asyncio.Queue()
        self._gpu_lock: asyncio.Lock = asyncio.Lock()
        self._worker_task: asyncio.Task = None
        self._current_job: ImageJob = None
        self._total_queued_tasks: int = 0
    
    async def add_job(self, job: ImageJob) -> int:
        """
        Add job to queue and persist queue position.
        
        Args:
            job: ImageJob to add
        
        Returns:
            Queue position (1-based)
        """
        # Calculate position
        queue_pos = self._queue.qsize() + 1
        self._total_queued_tasks += 1
        job._queue_position = queue_pos
        
        # Persist to database
        await update_message(job.message_id, None, {
            "status": "queued",
            "progress": 0,
            "queue_position": queue_pos,
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
            queue_position=queue_pos,
            prompt=job.prompt,
            message_id=job.message_id
        )
        
        # Add to queue
        await self._queue.put(job)
        
        return queue_pos
    
    async def _worker_loop(self):
        """Main worker loop - processes jobs sequentially"""
        while True:
            # Get next job from queue
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
        """Process a single job"""
        try:
            # Update status to processing
            await update_message(job.message_id, None, {
                "status": "processing",
                "progress": 0,
                "queue_position": 0
            })
            
            # Generate image
            image_url = await generate_image_via_forge(
                job.prompt,
                job,
                checkpoint_name=job.checkpoint_name
            )
            
            # Call completion callback
            job.on_done(image_url)
            
        except Exception as e:
            # Handle error
            await update_message(job.message_id,
                content=f"❌ Görsel oluşturulamadı: {str(e)}",
                new_metadata={
                    "status": "error",
                    "error": str(e),
                    "progress": 0,
                    "queue_position": 0
                }
            )
            
            await send_image_progress(
                username=job.username,
                conversation_id=job.conversation_id,
                job_id=job.job_id,
                status=ImageJobStatus.ERROR,
                error=str(e),
                message_id=job.message_id
            )
            
            job.on_done(f"(IMAGE ERROR) {e}")
```

### 2. State Transitions

```
┌─────────┐
│ pending │  (job created)
└────┬────┘
     │ add_job()
     ↓
┌─────────┐
│ queued  │  (in queue, waiting for GPU)
└────┬────┘
     │ GPU lock acquired
     ↓
┌──────────────┐
│ processing   │  (generating image)
└────┬─────────┘
     │
     ├─→ success ──→ ┌──────────┐
     │               │ complete │
     │               └──────────┘
     │
     └─→ error ────→ ┌───────┐
                     │ error │
                     └───────┘
```

### 3. Message Persistence Schema

```python
# Message.extra_metadata structure
{
    # Status tracking
    "status": "pending|queued|processing|complete|error",
    "progress": 0-100,  # Percentage
    "queue_position": 0-N,  # 0 = not in queue
    
    # Job identification
    "job_id": "uuid",
    "prompt": "user prompt",
    
    # Results
    "image_url": "/images/flux_xxx.png",  # On success
    "error": "error message",  # On error
    
    # Metadata
    "created_at": "2024-01-21T10:00:00Z",
    "updated_at": "2024-01-21T10:05:00Z"
}
```

### 4. Deep Merge Logic

```python
def update_message(message_id, new_content=None, new_metadata=None):
    """Update message with deep merge"""
    msg = session.get(Message, message_id)
    
    if new_content is not None:
        msg.content = new_content
    
    if new_metadata is not None:
        # Deep merge: preserve existing fields
        existing = msg.extra_metadata or {}
        merged = {**existing, **new_metadata}
        msg.extra_metadata = merged
    
    msg.updated_at = datetime.utcnow()
    session.commit()
    return msg
```

---

## Data Models

### ImageJob

```python
class ImageJob:
    def __init__(
        self,
        username: str,
        prompt: str,
        conversation_id: str,
        on_done: Callable[[str], None],
        job_id: str = None,
        checkpoint_name: str = None,
        message_id: int = None,
        image_settings: dict = None
    ):
        self.username = username
        self.prompt = prompt
        self.conversation_id = conversation_id
        self.on_done = on_done
        self.progress = 0
        self.queue_pos = 0
        self.job_id = job_id or str(uuid4())
        self.checkpoint_name = checkpoint_name
        self.message_id = message_id
        self.image_settings = image_settings or {}
        self._queue_position = 0  # Calculated at queue entry
```

### Message (Updated)

```python
class Message(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    conversation_id: str
    role: str  # "user", "bot", "system"
    content: str
    extra_metadata: dict = Field(default_factory=dict)  # Deep merge here
    created_at: datetime
    updated_at: datetime
```

---

## Correctness Properties

### Property 1: GPU Lock Exclusivity
**For any** two concurrent jobs, only one should hold the GPU lock at a time.
**Validates**: Requirement 2 (GPU Lock Mechanism)

### Property 2: Queue Position Uniqueness
**For any** set of queued jobs, each should have a unique queue_position.
**Validates**: Requirement 1 (Concurrent Job Processing)

### Property 3: Queue Position Ordering
**For any** set of queued jobs, positions should be sequential (1, 2, 3, ...).
**Validates**: Requirement 1 (Concurrent Job Processing)

### Property 4: State Transition Validity
**For any** job, state transitions should follow: pending → queued → processing → (complete|error).
**Validates**: Requirement 5 (Job State Transitions)

### Property 5: Deep Merge Preservation
**For any** concurrent updates to a message, all fields should be preserved (no data loss).
**Validates**: Requirement 7 (Concurrent Update Safety)

### Property 6: Persistence Consistency
**For any** job state change, the database should reflect the current state.
**Validates**: Requirement 3 (Queue Position Persistence)

### Property 7: WebSocket Delivery
**For any** job state change, a WebSocket message should be sent to the client.
**Validates**: Requirement 8 (WebSocket Queue Position Updates)

### Property 8: Error Recovery
**For any** failed job, the next job in queue should automatically start processing.
**Validates**: Requirement 6 (Error Recovery)

---

## Error Handling

### Timeout Handling
```python
try:
    async with asyncio.timeout(settings.FORGE_TIMEOUT):
        response = await generate_image_via_forge(prompt, job)
except asyncio.TimeoutError:
    await update_message(job.message_id,
        content="❌ Timeout: Forge API yanıt vermedi",
        new_metadata={
            "status": "error",
            "error": "Timeout after 180s"
        }
    )
```

### GPU Lock Timeout
```python
try:
    async with asyncio.timeout(30):
        async with self._gpu_lock:
            # Process job
except asyncio.TimeoutError:
    logger.error(f"GPU lock timeout for job {job.job_id}")
    # Release lock and continue
```

### Concurrent Update Conflict
```python
# Deep merge prevents conflicts
existing = {"status": "queued", "progress": 0}
update1 = {"progress": 50}
update2 = {"queue_position": 0}

# Both updates preserved
merged = {**existing, **update1, **update2}
# Result: {"status": "queued", "progress": 50, "queue_position": 0}
```

---

## Testing Strategy

### Unit Tests (Backend)
1. GPU lock acquisition/release
2. Queue position calculation
3. State transitions
4. Deep merge logic
5. Error handling

### Integration Tests (Backend)
1. Concurrent job processing
2. GPU lock prevents concurrent processing
3. Message persistence
4. Error recovery
5. WebSocket notifications

### Component Tests (Frontend)
1. Queue position display
2. Real-time position updates
3. Dynamic position calculation
4. Page reload recovery

### E2E Tests
1. Submit 3 jobs → all queued with correct positions
2. First job completes → remaining jobs update positions
3. Job error → next job starts automatically
4. Page reload → positions recalculated from DB

---

## Performance Considerations

### Database Queries
- Message lookup: O(1) by ID
- Queue position calculation: O(N) where N = queued jobs
- Concurrent updates: Atomic with transaction

### Memory Usage
- Queue: O(N) where N = pending jobs
- GPU lock: O(1)
- Message cache: O(M) where M = active messages

### Scalability
- Supports 100+ concurrent jobs
- Queue position calculation < 100ms
- No database lock contention

---

## Deployment Checklist

- [ ] FAZE 1 tests passing (19/19)
- [ ] FAZE 2 unit tests passing (15+)
- [ ] FAZE 2 integration tests passing (10+)
- [ ] FAZE 2 component tests passing (5+)
- [ ] FAZE 2 E2E tests passing (4+)
- [ ] No regressions in existing tests
- [ ] Performance verified (< 100ms queue position calc)
- [ ] Database migrations applied
- [ ] WebSocket notifications working
- [ ] Error handling verified
- [ ] Concurrent job processing verified
- [ ] Page reload recovery verified
- [ ] Production-ready code review passed

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Unit test pass rate | 100% | ⏳ |
| Integration test pass rate | 100% | ⏳ |
| Component test pass rate | 100% | ⏳ |
| E2E test pass rate | 100% | ⏳ |
| Code coverage | > 90% | ⏳ |
| Queue position calc time | < 100ms | ⏳ |
| Concurrent jobs supported | 100+ | ⏳ |
| Data loss incidents | 0 | ⏳ |
| Regression incidents | 0 | ⏳ |
