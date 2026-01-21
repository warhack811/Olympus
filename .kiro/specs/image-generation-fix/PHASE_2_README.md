# FAZE 2: Concurrent Job Handling & Queue Position Dynamics

## 📌 Overview

FAZE 2, image generation system'inde concurrent job handling ve GPU lock mekanizmasını implement eder. Birden fazla resim oluşturma isteği aynı anda kuyruğa alınabilir ve sırayla işlenir.

**Status**: 🟡 Ready for Implementation
**Dependency**: ✅ FAZE 1 Complete (19/19 tests passed)
**Duration**: 5-6 hours
**Test Coverage**: 26+ test cases

---

## 🎯 Key Objectives

1. **GPU Lock Mechanism** - GPU'nun aynı anda sadece bir job tarafından kullanılmasını sağla
2. **Concurrent Queue Management** - Birden fazla job'u kuyruğa al ve sırayla işle
3. **State Transitions** - Job'ların tüm state geçişlerini doğru şekilde handle et
4. **Error Recovery** - Bir job hata verirse sonraki job'un otomatik olarak işlenmesini sağla
5. **Queue Position Persistence** - Queue position'ı database'e persist et ve page reload'dan sonra recover et
6. **Dynamic Position Updates** - Queue position'ları dinamik olarak güncelle

---

## 📂 Spec Files

| File | Purpose | Status |
|------|---------|--------|
| [PHASE_2_REQUIREMENTS.md](./PHASE_2_REQUIREMENTS.md) | 9 detailed requirements with acceptance criteria | ✅ Complete |
| [PHASE_2_DESIGN.md](./PHASE_2_DESIGN.md) | Architecture, components, data models, correctness properties | ✅ Complete |
| [PHASE_2_TASKS.md](./PHASE_2_TASKS.md) | 8 implementation tasks with code examples and tests | ✅ Complete |
| [PHASE_2_QUICK_START.md](./PHASE_2_QUICK_START.md) | Quick reference guide for implementation | ✅ Complete |

---

## 🔧 Implementation Tasks

### Backend Tasks (Python)

| Task | File | Time | Tests |
|------|------|------|-------|
| 2.1 GPU Lock Mechanism | `app/image/job_queue.py` | 1h | 3 |
| 2.2 Concurrent Queue Management | `app/image/job_queue.py` | 1h | 3 |
| 2.3 State Transitions | `app/image/flux_stub.py` | 1h | 2 |
| 2.4 Error Recovery | `app/image/job_queue.py` | 1h | 2 |
| 2.5 Unit Tests | `tests/test_gpu_lock.py` | 1h | 5 |
| 2.6 Integration Tests | `tests/test_concurrent_processing.py` | 1h | 4 |

### Frontend Tasks (TypeScript/React)

| Task | File | Time | Tests |
|------|------|------|-------|
| 2.7 Component Tests | `tests/test_queue_position_component.tsx` | 1h | 3 |
| 2.8 E2E Tests | `tests/test_concurrent_e2e.ts` | 1h | 4 |

**Total**: 8 tasks, 8 hours, 26+ tests

---

## 📋 Requirements Summary

### Requirement 1: Concurrent Job Processing
- Multiple jobs queued with unique positions
- Jobs processed sequentially (FIFO)
- Each job gets unique queue_position

### Requirement 2: GPU Lock Mechanism
- GPU lock acquired before processing
- GPU lock released after processing
- Only one job processes at a time

### Requirement 3: Queue Position Persistence
- Queue position persisted to database
- Position updated when job starts/completes
- Page reload recovery works

### Requirement 4: Dynamic Queue Position Calculation
- Position updates when jobs complete
- Position recalculated for remaining jobs
- UI updates in real-time

### Requirement 5: Job State Transitions
- pending → queued → processing → (complete|error)
- Status persisted at each transition
- Timestamp updated

### Requirement 6: Error Recovery
- Error logged and persisted
- Next job automatically starts
- User sees error message

### Requirement 7: Concurrent Update Safety
- Deep merge prevents data loss
- Existing fields preserved
- New fields added without overwriting

### Requirement 8: WebSocket Queue Position Updates
- WebSocket message sent for each state change
- Queue position included in message
- Real-time UI updates

### Requirement 9: Performance & Scalability
- Supports 100+ concurrent jobs
- Queue position calculation < 100ms
- No database lock contention

---

## 🏗️ Architecture

```
Frontend (React)
    ↓ WebSocket
Backend (FastAPI)
    ├── ImageJobQueue (GPU lock + queue management)
    ├── generate_image_via_forge (state transitions)
    └── update_message (deep merge persistence)
    ↓ SQL
Database (SQLite/PostgreSQL)
    └── Message.extra_metadata (status, progress, queue_position)
```

---

## 🧪 Testing Strategy

### Unit Tests (Backend)
- GPU lock prevents concurrent processing
- GPU lock released on completion/error
- Queue position calculation
- Concurrent job processing

### Integration Tests (Backend)
- Multiple jobs queued with positions
- Job processing updates status
- Error recovery starts next job
- Concurrent updates no data loss

### Component Tests (Frontend)
- Queue position display
- Real-time position updates
- Non-queued jobs show no position

### E2E Tests
- Submit 3 jobs → all queued with correct positions
- First job completes → remaining jobs update
- Job error → next job starts automatically
- Page reload → positions recalculated from DB

**Total**: 26+ test cases, all must pass

---

## ✅ Success Criteria

- ✅ All 9 requirements' acceptance criteria pass
- ✅ 26+ test cases pass (unit + integration + component + E2E)
- ✅ 0 regressions (FAZE 1 tests still passing)
- ✅ GPU lock prevents concurrent processing
- ✅ Queue position persisted and updated dynamically
- ✅ Error recovery works
- ✅ Page reload recovery works
- ✅ Production-ready code
- ✅ No data loss in concurrent scenarios

---

## 🚀 Getting Started

### 1. Read the Spec

```bash
# Quick start
cat PHASE_2_QUICK_START.md

# Detailed requirements
cat PHASE_2_REQUIREMENTS.md

# Architecture & design
cat PHASE_2_DESIGN.md

# Implementation tasks
cat PHASE_2_TASKS.md
```

### 2. Verify FAZE 1 Complete

```bash
pytest tests/test_message_persistence.py tests/test_image_persistence_integration.py -v
# Expected: 19/19 passed ✅
```

### 3. Start Implementation

Follow the tasks in order:
1. Task 2.1: GPU Lock Mechanism
2. Task 2.2: Concurrent Queue Management
3. Task 2.3: State Transitions
4. Task 2.4: Error Recovery
5. Task 2.5: Unit Tests
6. Task 2.6: Integration Tests
7. Task 2.7: Component Tests
8. Task 2.8: E2E Tests

### 4. Verify All Tests Pass

```bash
# All FAZE 2 tests
pytest tests/test_gpu_lock.py tests/test_concurrent_processing.py -v
npm test -- test_queue_position_component.tsx
npx playwright test test_concurrent_e2e.ts

# Expected: 26+ tests passed ✅
```

---

## 📊 Progress Tracking

| Phase | Status | Tests | Duration |
|-------|--------|-------|----------|
| FAZE 1 | ✅ Complete | 19/19 | 4h |
| FAZE 2 | 🟡 Ready | 26+ | 8h |
| FAZE 3 | ⏳ Planned | 20+ | 6h |
| FAZE 4 | ⏳ Planned | 15+ | 4h |

---

## 🔗 Related Documents

- [PHASE_1_TEST_RESULTS.md](./PHASE_1_TEST_RESULTS.md) - FAZE 1 results
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Overall plan
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [requirements.md](./requirements.md) - Original requirements

---

## 💡 Key Concepts

### GPU Lock
- `asyncio.Lock()` ensures only one job processes at a time
- Acquired before processing, released after
- Prevents GPU resource conflicts

### Queue Position
- Calculated when job added to queue
- Persisted to database
- Updated dynamically as jobs complete
- Used for UI display and page reload recovery

### State Transitions
- pending → queued → processing → (complete|error)
- Each transition logged and persisted
- Timestamp updated at each transition

### Deep Merge
- Preserves existing metadata fields
- Adds new fields without overwriting
- Prevents data loss in concurrent updates

### Error Recovery
- Error logged and persisted
- Next job automatically starts
- User sees error message
- System continues processing

---

## 🎓 Learning Resources

### Async/Await in Python
- `asyncio.Lock()` for mutual exclusion
- `async with` for context management
- `asyncio.Queue()` for job queue

### Database Transactions
- SQLModel for ORM
- Deep merge for concurrent updates
- Transaction rollback on error

### WebSocket Communication
- Real-time status updates
- Queue position notifications
- Error message delivery

### Testing Best Practices
- Unit tests for isolated logic
- Integration tests for workflows
- Component tests for UI
- E2E tests for full scenarios

---

## 🚨 Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| GPU lock deadlock | Add timeout, implement monitoring |
| Queue position inconsistency | Persist to database, recalculate on reload |
| Data loss in concurrent updates | Use deep merge, not overwrite |
| WebSocket message loss | Implement retry mechanism |
| Performance degradation | Optimize queries, add caching |

---

## 📞 Support

For questions or issues:
1. Check the spec files
2. Review test cases
3. Check error logs
4. Request code review

---

## 📝 Checklist

Before starting FAZE 3:

- [ ] All 8 FAZE 2 tasks completed
- [ ] All 26+ tests passing
- [ ] No regressions in FAZE 1 tests
- [ ] Code review approved
- [ ] Performance verified
- [ ] Production-ready code
- [ ] Documentation complete

---

**FAZE 2 Specification Complete! 🎉**

Ready to implement? Start with [PHASE_2_QUICK_START.md](./PHASE_2_QUICK_START.md)
