# FAZE 3: Dynamic Queue Position Recalculation & UI Enhancements

## 📌 Genel Bakış

FAZE 3, queue position'ların dinamik olarak yeniden hesaplanmasını ve frontend UI'ında gerçek zamanlı gösterilmesini sağlar.

**Bağımlılık**: FAZE 2 Complete ✅
**Süre**: 6 saat
**Test Coverage**: 20+ test cases

---

## 🎯 Gereksinimler

### Requirement 1: Dynamic Queue Position Recalculation
- Job tamamlandığında kalan job'ların position'ları otomatik güncellenmeli
- Position'lar database'den yeniden hesaplanmalı
- WebSocket üzerinden UI'a bildirim gönderilmeli

### Requirement 2: Real-time UI Updates
- Queue position değişikliği anında UI'da görünmeli
- WebSocket mesajları alındığında component güncellenmelidir
- Smooth animation ile position değişimi gösterilmeli

### Requirement 3: Queue Position Display
- Chat UI'da queue position gösterilmeli
- Processing sırasında position 0 gösterilmeli
- Queued job'lar için "Position: X" formatında gösterilmeli

### Requirement 4: Job Status Indicators
- Job status'u (queued/processing/complete/error) gösterilmeli
- Progress bar gösterilmeli
- Error mesajları gösterilmeli

### Requirement 5: Page Reload Recovery
- Sayfa yenilendiğinde queue position'lar database'den yüklenmelidir
- Job status'u korunmalıdır
- Hiçbir veri kaybı olmamalıdır

---

## 🏗️ Implementation Tasks

### Task 3.1: Backend - Dynamic Position Recalculation
**File**: `app/image/job_queue.py`
**Time**: 1.5 hours

Implement position recalculation when job completes:
- Get all queued jobs from database
- Recalculate positions (1-based)
- Update each job's position
- Send WebSocket notifications

### Task 3.2: Backend - Position Update on Job Complete
**File**: `app/image/flux_stub.py`
**Time**: 1 hour

Update position when job completes:
- Call recalculation function
- Persist updated positions
- Send WebSocket notifications to all affected users

### Task 3.3: Frontend - Queue Position Component
**File**: `ui-new/src/components/chat/ImageProgressCard.tsx`
**Time**: 1.5 hours

Display queue position in UI:
- Show "Position: X" for queued jobs
- Show progress bar for processing jobs
- Show status indicator (queued/processing/complete/error)
- Smooth animations for position changes

### Task 3.4: Frontend - WebSocket Position Updates
**File**: `ui-new/src/stores/imageJobsStore.ts`
**Time**: 1 hour

Handle WebSocket position updates:
- Listen for position change events
- Update local state
- Trigger component re-renders
- Handle concurrent updates

### Task 3.5: Frontend - Page Reload Recovery
**File**: `ui-new/src/hooks/useImageJobs.ts`
**Time**: 1 hour

Recover state on page reload:
- Fetch all jobs from API
- Restore queue positions from database
- Restore job status
- Restore progress

### Task 3.6: Testing
**Files**: `tests/test_queue_position_recalculation.py`, `tests/test_ui_updates.tsx`
**Time**: 1 hour

Write tests for:
- Position recalculation logic
- WebSocket updates
- UI component rendering
- Page reload recovery

---

## ✅ Success Criteria

- ✅ All 5 requirements implemented
- ✅ 20+ tests passing
- ✅ 0 regressions (FAZE 1 & 2 tests still passing)
- ✅ Dynamic position recalculation working
- ✅ Real-time UI updates working
- ✅ Page reload recovery working
- ✅ Production-ready code

---

## 🧪 Test Coverage

### Backend Tests (10 tests)
- Position recalculation logic
- WebSocket notifications
- Database persistence
- Concurrent updates

### Frontend Tests (10 tests)
- Component rendering
- Position display
- WebSocket updates
- Page reload recovery

---

## 📋 Implementation Order

1. Task 3.1: Backend position recalculation
2. Task 3.2: Position update on job complete
3. Task 3.3: Frontend component
4. Task 3.4: WebSocket updates
5. Task 3.5: Page reload recovery
6. Task 3.6: Testing

---

## 🚀 Ready to Start

All prerequisites met. FAZE 2 complete. Ready for FAZE 3 implementation.

