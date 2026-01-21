# Image Generation System - Architecture & Data Flow

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Zustand)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ useWebSocket Hook                                                │  │
│  │ - Singleton WebSocket connection                                 │  │
│  │ - Auto-reconnect with exponential backoff                        │  │
│  │ - Message normalization                                          │  │
│  │ - Status level ordering (prevents regressions)                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ imageJobsStore (Zustand)                                         │  │
│  │ - Jobs by job_id mapping                                         │  │
│  │ - Message-to-job linking                                         │  │
│  │ - Stuck job detection (5 min timeout)                            │  │
│  │ - Auto-removal after 10 seconds                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ ImageProgressCard Component                                      │  │
│  │ - calculateQueuePosition() [PHASE 2]                             │  │
│  │ - Shimmer placeholder animation                                  │  │
│  │ - Progress bar with gradient                                     │  │
│  │ - Queue position display (dynamic)                               │  │
│  │ - Estimated time calculation                                     │  │
│  │ - Cancel button                                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↑
                    WebSocket (Redis pub/sub)
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI + asyncio)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ API Routes (images.py)                                           │  │
│  │ - POST /image/generate                                           │  │
│  │ - GET /image/status                                              │  │
│  │ - GET /image/job/{job_id}/status                                 │  │
│  │ - DELETE /image/job/{job_id}/cancel                              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Processor (processor.py)                                         │  │
│  │ - Create message with [IMAGE_PENDING]                            │  │
│  │ - Create job_id                                                  │  │
│  │ - Call request_image_generation()                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ ImageManager (image_manager.py)                                  │  │
│  │ - request_image_generation()                                     │  │
│  │ - Create ImageJob with message_id                                │  │
│  │ - Add job to queue                                               │  │
│  │ - Register pending job                                           │  │
│  │ - Send initial WebSocket progress                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ ImageJobQueue (job_queue.py)                                     │  │
│  │ - add_job() [PHASE 1: Persist queue_position]                    │  │
│  │ - _worker_loop() - Sequential job processor                      │  │
│  │ - _process_single_job()                                          │  │
│  │ - GPU lock (sequential processing)                               │  │
│  │ - cancel_job()                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ FluxStub (flux_stub.py)                                          │  │
│  │ - generate_image_via_forge() [PHASE 1: Persist all fields]       │  │
│  │ - Circuit breaker pattern [PHASE 4: Configure thresholds]        │  │
│  │ - Retry logic (3 attempts, exponential backoff)                  │  │
│  │ - Progress polling                                               │  │
│  │ - Timeout handling [PHASE 3: User-friendly messages]             │  │
│  │ - Message persistence (status, progress, image_url, error)       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Forge API (Stable Diffusion WebUI)                               │  │
│  │ - /sdapi/v1/txt2img - Generate image                             │  │
│  │ - /sdapi/v1/progress - Get progress                              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ WebSockets (websockets.py)                                       │  │
│  │ - send_image_progress()                                          │  │
│  │ - Identity set matching (user_id or username)                    │  │
│  │ - Redis bridge for cloud relay                                   │  │
│  │ - Metrics tracking                                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Conversation (conversation.py)                                   │  │
│  │ - update_message() [PHASE 1: Deep merge]                         │  │
│  │ - Persist status, progress, queue_position, image_url, error     │  │
│  │ - Page reload recovery                                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Maintenance Task (maintenance.py) [PHASE 3]                      │  │
│  │ - cleanup_stuck_image_jobs()                                     │  │
│  │ - Detect jobs inactive for 5 minutes                             │  │
│  │ - Mark as error with message                                     │  │
│  │ - Send WebSocket notification                                    │  │
│  │ - Run every 60 seconds                                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATABASE (PostgreSQL + SQLModel)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Message {                                                              │
│    id: int                                                              │
│    conversation_id: str                                                 │
│    role: str ("user", "bot", "system")                                  │
│    content: str ("[IMAGE_PENDING]" or "[IMAGE] IMAGE_PATH: ...")        │
│    extra_metadata: dict {                                               │
│      "type": "image",                                                   │
│      "status": "queued|processing|complete|error",                      │
│      "progress": 0-100,                                                 │
│      "queue_position": 1-N,                                             │
│      "job_id": "uuid",                                                  │
│      "prompt": "user prompt",                                           │
│      "image_url": "/images/flux_xxx.png",                               │
│      "error": "error message"                                           │
│    }                                                                    │
│    created_at: datetime                                                 │
│    updated_at: datetime                                                 │
│  }                                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow Diagrams

### 1. Image Request Flow

```
User Input
    ↓
[Chat Input] "Resim çiz"
    ↓
[Processor] Create message + job_id
    ↓
[ImageManager] request_image_generation()
    ↓
[JobQueue] add_job()
    ├─ Calculate queue_position
    ├─ Persist to DB [PHASE 1]
    └─ Send WebSocket notification
    ↓
[Worker] _worker_loop()
    ├─ Wait for job
    └─ Call _process_single_job()
    ↓
[FluxStub] generate_image_via_forge()
    ├─ Mark as processing [PHASE 1]
    ├─ Poll progress [PHASE 1]
    ├─ Handle timeout [PHASE 3]
    ├─ Generate image
    └─ Persist result [PHASE 1]
    ↓
[Conversation] update_message()
    ├─ Deep merge metadata [PHASE 1]
    └─ Persist to DB
    ↓
[WebSockets] send_image_progress()
    ├─ Send to connected clients
    └─ Redis bridge for cloud
    ↓
[Frontend] useWebSocket
    ├─ Receive message
    ├─ Update imageJobsStore
    └─ Re-render UI
    ↓
[UI] ImageProgressCard
    ├─ Calculate queue_position [PHASE 2]
    ├─ Show progress bar
    └─ Display image
```

### 2. Queue Position Update Flow

```
Job1 Processing Starts
    ↓
[JobQueue] _process_single_job(Job1)
    ├─ Mark Job1 as processing
    ├─ Update Job1 queue_position = 0
    └─ Send WebSocket update
    ↓
[Frontend] useWebSocket receives update
    ├─ Update imageJobsStore
    └─ Trigger re-render
    ↓
[ImageProgressCard] Re-render
    ├─ calculateQueuePosition() [PHASE 2]
    │  ├─ Get all jobs from store
    │  ├─ Filter queued jobs
    │  ├─ Sort by creation time
    │  └─ Calculate position
    ├─ Job2: position = 1 (was 2)
    ├─ Job3: position = 2 (was 3)
    └─ Update UI
```

### 3. Message Persistence Flow

```
Job Status Change
    ↓
[FluxStub] generate_image_via_forge()
    ├─ Status: queued → processing
    ├─ Progress: 0 → 50
    └─ Call update_message()
    ↓
[Conversation] update_message()
    ├─ Get existing metadata
    ├─ Deep merge [PHASE 1]
    │  ├─ Keep: status, progress, queue_position
    │  ├─ Add: job_id, prompt
    │  └─ Result: all fields preserved
    ├─ Update DB
    └─ Return updated message
    ↓
[Database] Message updated
    ├─ extra_metadata merged
    ├─ updated_at timestamp
    └─ All fields preserved
    ↓
[Frontend] Page Reload
    ├─ Load messages from DB
    ├─ Reconstruct job state
    └─ Resume progress tracking
```

### 4. Stuck Job Detection Flow

```
Job Processing Started
    ↓
[FluxStub] generate_image_via_forge()
    ├─ Status: processing
    ├─ Progress: 0
    └─ updated_at: now
    ↓
[Maintenance Task] cleanup_stuck_image_jobs() [PHASE 3]
    ├─ Runs every 60 seconds
    ├─ Check all processing jobs
    ├─ If updated_at < now - 5 minutes
    │  ├─ Mark as error
    │  ├─ Set error message
    │  └─ Send WebSocket notification
    └─ Continue checking
    ↓
[Frontend] Receives error notification
    ├─ Update imageJobsStore
    ├─ Show error message
    └─ Allow retry
```

### 5. Concurrent Submission Flow

```
User Submits 3 Jobs Rapidly
    ↓
T=0.000: Job1 arrives
    ├─ Redis INCR "image_queue_counter" → 1
    ├─ queue_position = 1
    └─ Persist to DB
    ↓
T=0.001: Job2 arrives
    ├─ Redis INCR "image_queue_counter" → 2
    ├─ queue_position = 2
    └─ Persist to DB
    ↓
T=0.002: Job3 arrives
    ├─ Redis INCR "image_queue_counter" → 3
    ├─ queue_position = 3
    └─ Persist to DB
    ↓
[Frontend] Receives all 3 jobs
    ├─ calculateQueuePosition() [PHASE 2]
    ├─ Job1: position = 1 ✓
    ├─ Job2: position = 2 ✓
    ├─ Job3: position = 3 ✓
    └─ All unique positions
```

---

## 🔄 State Transitions

### Job Status State Machine

```
                    ┌─────────────┐
                    │   QUEUED    │
                    └──────┬──────┘
                           │
                    (Job starts processing)
                           │
                           ↓
                    ┌─────────────┐
                    │ PROCESSING  │
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │                     │
        (Success)              (Error/Timeout)
                │                     │
                ↓                     ↓
        ┌─────────────┐        ┌─────────────┐
        │  COMPLETE   │        │    ERROR    │
        └─────────────┘        └─────────────┘
                │                     │
        (Terminal State)      (Terminal State)
```

### Message Persistence State

```
Message Created
    ↓
extra_metadata = {
    "status": "queued",
    "progress": 0,
    "queue_position": 1
}
    ↓
Job Processing Starts
    ↓
extra_metadata = {
    "status": "processing",  ← Updated
    "progress": 0,           ← Updated
    "queue_position": 0,     ← Updated
    "job_id": "...",         ← Added
    "prompt": "..."          ← Added
}
    ↓
Progress Update (10%)
    ↓
extra_metadata = {
    "status": "processing",  ← Preserved
    "progress": 10,          ← Updated
    "queue_position": 0,     ← Preserved
    "job_id": "...",         ← Preserved
    "prompt": "..."          ← Preserved
}
    ↓
Job Complete
    ↓
extra_metadata = {
    "status": "complete",    ← Updated
    "progress": 100,         ← Updated
    "queue_position": 0,     ← Preserved
    "job_id": "...",         ← Preserved
    "prompt": "...",         ← Preserved
    "image_url": "..."       ← Added
}
```

---

## 🔌 Integration Points

### Backend to Frontend
- **WebSocket**: Real-time progress updates
- **REST API**: Status queries, job cancellation
- **Database**: Message persistence for page reload

### Backend to Forge API
- **HTTP**: Image generation requests
- **Progress Polling**: Real-time progress tracking
- **Error Handling**: Timeout, connection errors

### Backend to Redis
- **Queue**: Job queue management
- **Pub/Sub**: WebSocket message relay
- **Atomic Counter**: Queue position [PHASE 4]

### Frontend to Backend
- **WebSocket**: Receive progress updates
- **REST API**: Submit requests, cancel jobs
- **Local Storage**: Cache job state

---

## 📈 Performance Considerations

### Queue Processing
- **Sequential**: One job at a time (GPU lock)
- **Async**: Non-blocking I/O
- **Progress Polling**: Every 1 second
- **WebSocket Updates**: Every 10% progress

### Database
- **Persistence**: Every status change
- **Deep Merge**: Efficient metadata updates
- **Indexing**: On job_id, conversation_id
- **Cleanup**: Auto-remove after 10 seconds

### Frontend
- **Re-renders**: On WebSocket updates only
- **Calculations**: calculateQueuePosition() on every render
- **Memoization**: ImageProgressCard memoized
- **Animations**: Framer Motion for smooth transitions

---

## 🛡️ Error Handling

### Timeout Handling [PHASE 3]
```
Forge API Timeout (180s)
    ↓
Retry 1: Wait 1s, retry
    ↓
Retry 2: Wait 2s, retry
    ↓
Retry 3: Wait 4s, retry
    ↓
All retries failed
    ↓
Send error to user: "Forge API zaman aşımına uğradı (180s). Lütfen tekrar deneyin."
    ↓
Mark job as error
    ↓
Persist to DB
    ↓
Send WebSocket notification
```

### Stuck Job Detection [PHASE 3]
```
Job Processing Started
    ↓
5 minutes pass without progress update
    ↓
Maintenance task detects stuck job
    ↓
Mark as error: "İşlem zaman aşımına uğradı (Stuck Job Guard)"
    ↓
Persist to DB
    ↓
Send WebSocket notification
    ↓
Frontend shows error
```

### Circuit Breaker [PHASE 4]
```
Forge API Error
    ↓
Failure count++
    ↓
Failure count < 5?
    ├─ YES: Continue normal operation
    └─ NO: Open circuit breaker
    ↓
Circuit Open
    ├─ Return placeholder image
    ├─ Log error
    └─ Wait 60 seconds
    ↓
60 seconds pass
    ↓
Circuit Half-Open
    ├─ Try one request
    ├─ Success? → Close circuit
    └─ Failure? → Open circuit again
```

---

## 🎯 Critical Paths

### Path 1: Message Persistence (Foundation)
```
update_message() → Deep merge → DB persistence → Page reload recovery
```

### Path 2: Queue Position Dynamic (User Experience)
```
Job status change → WebSocket → calculateQueuePosition() → UI update
```

### Path 3: Stuck Job Detection (Reliability)
```
Maintenance task → Detect inactive → Mark error → WebSocket notification
```

### Path 4: Concurrent Submission (Edge Cases)
```
Rapid submissions → Atomic counter → Unique positions → No race conditions
```

---

## 📊 Dependency Matrix

| Component | Depends On | Provides To | Phase |
|-----------|-----------|------------|-------|
| update_message() | Database | All persistence | 1 |
| add_job() | update_message() | Queue management | 1 |
| generate_image_via_forge() | update_message() | Image generation | 1 |
| send_image_progress() | WebSocket | Frontend updates | 1 |
| calculateQueuePosition() | imageJobsStore | UI rendering | 2 |
| cleanup_stuck_image_jobs() | Database | Error handling | 3 |
| Atomic counter | Redis | Queue position | 4 |
| Circuit breaker | Forge API | Error handling | 4 |

---

## ✨ Key Design Principles

1. **Sequential Processing**: GPU lock ensures one job at a time
2. **Async I/O**: Non-blocking operations throughout
3. **Message Persistence**: All state persisted to DB
4. **Deep Merge**: Concurrent updates don't lose data
5. **Real-time Updates**: WebSocket for instant feedback
6. **Error Resilience**: Retry logic, circuit breaker, stuck job detection
7. **User Experience**: Dynamic queue position, user-friendly errors
8. **Scalability**: Atomic counters, efficient queries

---

**This architecture ensures production-ready reliability, performance, and user experience.**

