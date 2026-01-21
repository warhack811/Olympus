# FAZE 2: Quick Start Guide

## 🎯 Hedef

FAZE 2, concurrent job handling ve GPU lock mekanizmasını implement eder. Birden fazla resim oluşturma isteği aynı anda kuyruğa alınabilir ve sırayla işlenir.

**Süre**: 5-6 saat
**Test Sayısı**: 26+
**Dosya Sayısı**: 5 (3 implementation + 2 test)

---

## 📋 Gereksinimler

✅ FAZE 1 tamamlandı (19/19 test geçti)
✅ Deep merge implementasyonu çalışıyor
✅ Message persistence çalışıyor
✅ Queue position persistence çalışıyor

---

## 🚀 Başlangıç

### 1. FAZE 2 Spec'ini Oku

```bash
# Requirements
cat .kiro/specs/image-generation-fix/PHASE_2_REQUIREMENTS.md

# Design
cat .kiro/specs/image-generation-fix/PHASE_2_DESIGN.md

# Tasks
cat .kiro/specs/image-generation-fix/PHASE_2_TASKS.md
```

### 2. Dosya Yapısını Anla

```
app/
├── image/
│   ├── job_queue.py          # GPU lock + concurrent processing
│   └── flux_stub.py          # State transitions
├── memory/
│   └── conversation.py       # Deep merge (FAZE 1)
└── core/
    └── websockets.py         # WebSocket notifications

tests/
├── test_gpu_lock.py          # GPU lock unit tests
├── test_concurrent_processing.py  # Integration tests
├── test_queue_position_component.tsx  # Component tests
└── test_concurrent_e2e.ts    # E2E tests
```

### 3. Implementation Order

```
Task 2.1 → Task 2.2 → Task 2.3 → Task 2.4 → Task 2.5 → Task 2.6 → Task 2.7 → Task 2.8
(1h)      (1h)      (1h)      (1h)      (1h)      (1h)      (1h)      (1h)
```

---

## 🔧 Implementation Checklist

### Task 2.1: GPU Lock Mechanism (1 saat)

**Dosya**: `app/image/job_queue.py`

```python
# Ekle:
class ImageJobQueue:
    def __init__(self):
        self._gpu_lock: asyncio.Lock = asyncio.Lock()  # ← GPU lock
    
    async def _worker_loop(self):
        while True:
            job = await self._queue.get()
            async with self._gpu_lock:  # ← Lock acquired
                await self._process_single_job(job)
            self._queue.task_done()
```

**Kontrol**:
- [ ] GPU lock tanımlandı
- [ ] Worker loop'ta lock kullanılıyor
- [ ] Lock error'da da release ediliyor

---

### Task 2.2: Concurrent Queue Management (1 saat)

**Dosya**: `app/image/job_queue.py`

```python
# Ekle:
def add_job(self, job: ImageJob) -> int:
    queue_pos = self._queue.qsize() + 1
    
    # Persist queue position
    update_message(job.message_id, None, {
        "status": "queued",
        "queue_position": queue_pos,
        "job_id": job.job_id,
        "prompt": job.prompt
    })
    
    self._queue.put_nowait(job)
    return queue_pos
```

**Kontrol**:
- [ ] Queue position hesaplanıyor
- [ ] Database'e persist ediliyor
- [ ] WebSocket notification gönderiliyor

---

### Task 2.3: State Transitions (1 saat)

**Dosya**: `app/image/flux_stub.py`

```python
# Ekle:
async def generate_image_via_forge(prompt, job, checkpoint_name=None):
    # State 1: Processing
    update_message(job.message_id, None, {
        "status": "processing",
        "progress": 1,
        "queue_position": 0
    })
    
    try:
        # Generate...
        image_url = await _generate_image_internal(...)
        
        # State 2: Complete
        update_message(job.message_id, None, {
            "status": "complete",
            "progress": 100,
            "image_url": image_url
        })
        
    except Exception as e:
        # State 3: Error
        update_message(job.message_id, None, {
            "status": "error",
            "error": str(e)
        })
```

**Kontrol**:
- [ ] State transitions logged
- [ ] Status persist ediliyor
- [ ] Error message persist ediliyor

---

### Task 2.4: Error Recovery (1 saat)

**Dosya**: `app/image/job_queue.py`

```python
# Ekle:
async def _process_single_job(self, job):
    try:
        image_url = await generate_image_via_forge(...)
        job.on_done(image_url)
    except Exception as e:
        # Error handling
        await send_image_progress(
            status=ImageJobStatus.ERROR,
            error=str(e)
        )
        job.on_done(f"(IMAGE ERROR) {e}")
        # Next job automatically starts (worker loop continues)
```

**Kontrol**:
- [ ] Error logged
- [ ] Error persist ediliyor
- [ ] WebSocket notification gönderiliyor
- [ ] Sonraki job otomatik başlıyor

---

### Task 2.5: Unit Tests (1 saat)

**Dosya**: `tests/test_gpu_lock.py`

```python
# Test cases:
# 1. GPU lock prevents concurrent processing
# 2. GPU lock released on completion
# 3. GPU lock released on error
# 4. Queue position calculation
# 5. Concurrent job processing
```

**Çalıştır**:
```bash
pytest tests/test_gpu_lock.py -v
# Expected: 5/5 passed
```

---

### Task 2.6: Integration Tests (1 saat)

**Dosya**: `tests/test_concurrent_processing.py`

```python
# Test scenarios:
# 1. Multiple jobs queued with positions
# 2. Job processing updates status
# 3. Error recovery starts next job
# 4. Concurrent updates no data loss
```

**Çalıştır**:
```bash
pytest tests/test_concurrent_processing.py -v
# Expected: 4/4 passed
```

---

### Task 2.7: Component Tests (1 saat)

**Dosya**: `tests/test_queue_position_component.tsx`

```typescript
// Test cases:
// 1. Display queue position for queued jobs
// 2. Update queue position dynamically
// 3. Show 0 for non-queued jobs
```

**Çalıştır**:
```bash
npm test -- test_queue_position_component.tsx
# Expected: 3/3 passed
```

---

### Task 2.8: E2E Tests (1 saat)

**Dosya**: `tests/test_concurrent_e2e.ts`

```typescript
// Test scenarios:
// 1. Process 3 jobs sequentially
// 2. Update positions when job completes
// 3. Recover from error and process next job
// 4. Recover positions after page reload
```

**Çalıştır**:
```bash
npx playwright test test_concurrent_e2e.ts
# Expected: 4/4 passed
```

---

## ✅ Verification

### Tüm Testleri Çalıştır

```bash
# FAZE 1 tests (regression check)
pytest tests/test_message_persistence.py tests/test_image_persistence_integration.py -v
# Expected: 19/19 passed

# FAZE 2 unit tests
pytest tests/test_gpu_lock.py -v
# Expected: 5/5 passed

# FAZE 2 integration tests
pytest tests/test_concurrent_processing.py -v
# Expected: 4/4 passed

# FAZE 2 component tests
npm test -- test_queue_position_component.tsx
# Expected: 3/3 passed

# FAZE 2 E2E tests
npx playwright test test_concurrent_e2e.ts
# Expected: 4/4 passed

# Total: 35/35 tests passed ✅
```

### Code Quality

```bash
# Type checking
mypy app/image/job_queue.py app/image/flux_stub.py

# Linting
ruff check app/image/job_queue.py app/image/flux_stub.py

# Format
black app/image/job_queue.py app/image/flux_stub.py
```

### Performance

```bash
# Queue position calculation < 100ms
# GPU lock acquisition < 10ms
# Message persistence < 50ms
```

---

## 🎯 Success Criteria

- ✅ 26+ tests passing (5 unit + 4 integration + 3 component + 4 E2E)
- ✅ 0 regressions (FAZE 1 tests still passing)
- ✅ GPU lock prevents concurrent processing
- ✅ Queue position persisted and updated dynamically
- ✅ Error recovery works
- ✅ Page reload recovery works
- ✅ Production-ready code
- ✅ No data loss in concurrent scenarios

---

## 📊 Progress Tracking

| Task | Status | Tests | Time |
|------|--------|-------|------|
| 2.1 GPU Lock | ⏳ | 3 | 1h |
| 2.2 Queue Mgmt | ⏳ | 3 | 1h |
| 2.3 State Trans | ⏳ | 2 | 1h |
| 2.4 Error Rec | ⏳ | 2 | 1h |
| 2.5 Unit Tests | ⏳ | 5 | 1h |
| 2.6 Integration | ⏳ | 4 | 1h |
| 2.7 Component | ⏳ | 3 | 1h |
| 2.8 E2E | ⏳ | 4 | 1h |
| **TOTAL** | **⏳** | **26** | **8h** |

---

## 🔗 Related Documents

- [PHASE_2_REQUIREMENTS.md](./PHASE_2_REQUIREMENTS.md) - Detailed requirements
- [PHASE_2_DESIGN.md](./PHASE_2_DESIGN.md) - Architecture & design
- [PHASE_2_TASKS.md](./PHASE_2_TASKS.md) - Detailed implementation tasks
- [PHASE_1_TEST_RESULTS.md](../PHASE_1_TEST_RESULTS.md) - FAZE 1 results

---

## 💡 Tips

1. **GPU Lock**: `asyncio.Lock()` kullan, deadlock'tan kaçın
2. **Queue Position**: Database'e persist et, page reload'dan sonra recover et
3. **State Transitions**: Tüm state'leri log et, debug'ı kolaylaştır
4. **Error Recovery**: Bir job fail'erse, sonraki job otomatik başlasın
5. **Testing**: Unit → Integration → Component → E2E sırasında test et

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| GPU lock deadlock | Timeout ekle, monitoring yap |
| Queue position inconsistency | Database'e persist et |
| Data loss in concurrent updates | Deep merge kullan |
| WebSocket message loss | Retry mechanism ekle |
| Performance degradation | Query optimization yap |

---

## 📞 Support

Sorular veya sorunlar için:
1. Spec dosyalarını oku
2. Test case'leri kontrol et
3. Error log'ları incele
4. Code review iste

---

**FAZE 2 Ready! 🚀**

Başlamaya hazır mısın? Task 2.1'den başla!
