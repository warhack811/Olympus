# MAMI AI v4 - Bilinen Sorunlar ve Düzeltme Planı

**Tarih:** 15 Ocak 2026  
**Son Güncelleme:** 23:13  
**Analiz Eden:** Cline  
**Durum:** Tespit Edildi - Düzeltme Bekliyor

---

## 🔴 P0 - CRİTİK (Üretim Etkiler)

### #1: Gateway - Memory Adapter Timeout Yok
**Dosya:** `app/orchestrator_v42/gateway.py:468-490`  
**Durum:** 🔴 Açık

**Sorun:**
Memory adapter çağrısında timeout koruması yok. Memory servisi yanıt vermezse gateway sonsuza kadar bekliyor.

**Etki:**
- %5 hanging requests
- Event loop blocking
- Tüm yeni requests beklemede kalıyor

**Çözüm:**
```python
rem_budget_mem = _budget_remaining(start_ts)
if rem_budget_mem < 0.1:
    mem_ctx = {"items": [], "notes": "Budget exceeded"}
else:
    mem_ctx = await asyncio.wait_for(
        memory_adapter.get_memory_context(...),
        timeout=min(0.5, rem_budget_mem)
    )
```

**Öncelik:** P0  
**Tahmini Süre:** 1 saat  
**Bağımlılık:** Yok

---

### #2: Image Manager - Stats Race Condition
**Dosya:** `app/image/image_manager.py:36-40`  
**Durum:** 🔴 Açık

**Sorun:**
`_image_stats["total_jobs"] += 1` operasyonu atomik değil. Concurrent access durumunda data corruption oluşuyor.

**Etki:**
- %2 stats corruption
- Admin dashboard yanlış istatistikler
- Pending job count drift

**Çözüm:**
```python
import threading
_stats_lock = threading.Lock()

def _on_job_added(username, prompt):
    with _stats_lock:
        _image_stats["total_jobs"] += 1
        _image_stats["pending_jobs"] += 1
```

**Öncelik:** P0  
**Tahmini Süre:** 30 dakika  
**Bağımlılık:** Yok

---

### #3: Image Manager - Stats-DB Desync
**Dosya:** `app/image/image_manager.py:83-98`  
**Durum:** 🔴 Açık

**Sorun:**
`on_complete()` callback'inde önce stats güncelleniyor, sonra DB. DB yazma başarısız olursa stats ve DB tutarsız kalıyor.

**Etki:**
- Zombie jobs (stats'ta yok, DB'de var)
- Queue position drift
- Admin: "No jobs" ama gerçekte 5+ job bekliyor

**Çözüm:**
```python
def on_complete(result: str):
    try:
        update_message(...)  # Önce DB
    except Exception as e:
        logger.error(...)
        return  # Stats güncelleme
    
    _on_job_finished(job.job_id)  # Sonra stats
```

**Öncelik:** P0  
**Tahmini Süre:** 1 saat  
**Bağımlılık:** Yok

---

### #4: Flux Stub - Zombie Task (Thread Leak)
**Dosya:** `app/image/flux_stub.py:180-184`  
**Durum:** 🔴 Açık

**Sorun:**
`gen_task.cancel()` çağrısı var ama `await` yok. Thread içinde `requests.post(timeout=60s)` çalışmaya devam ediyor.

**Etki:**
- 100 cancelled job → 100 zombie thread
- ThreadPoolExecutor exhausted (50 dakika sonra)
- Sistem yanıt veremez hale geliyor

**Çözüm:**
```python
except Exception:
    if not gen_task.done():
        gen_task.cancel()
        try:
            await gen_task
        except asyncio.CancelledError:
            pass
    raise
```

**Öncelik:** P0  
**Tahmini Süre:** 30 dakika  
**Bağımlılık:** Yok

---

### #5: Flux Stub - Circuit Breaker Entegrasyonu Kırık
**Dosya:** `app/image/flux_stub.py:62-66`  
**Durum:** 🔴 Açık

**Sorun:**
Circuit breaker açık olduğunda placeholder döndürülüyor ama `job.on_done()` çağrılmıyor. Stats güncellenmemiş kalıyor.

**Etki:**
- Stats drift +15%
- Phantom jobs
- Queue görünmez olabiliyor

**Çözüm:**
```python
if not forge_circuit_breaker.can_attempt():
    error_msg = "(IMAGE ERROR) Circuit breaker açık"
    job.on_done(error_msg)  # MUTLAKA ÇAĞIR
    return PLACEHOLDER_IMAGES["maintenance"]
```

**Öncelik:** P0  
**Tahmini Süre:** 15 dakika  
**Bağımlılık:** Yok

---

## 🟠 P1 - HIGH (Performans ve Stabilite)

### #6: Flux Stub - Progress Loop Resource Leak
**Dosya:** `app/image/flux_stub.py:145-178`  
**Durum:** 🟠 Açık

**Sorun:**
Progress loop her 1 saniyede 3 ayrı I/O operasyonu yapıyor:
- HTTP → Forge progress API
- DB → Message update
- WebSocket → Progress broadcast

**30s generation:** 90 işlem  
**100 concurrent jobs:** 9000 işlem/saniye

**Etki:**
- Connection pool exhaustion (aiohttp limit: 100)
- DB connection leak
- WebSocket buffer overflow

**Çözüm:**
```python
# Throttle: Her 2s
await asyncio.sleep(2)  # 1s → 2s

# DB: Her 20%
if job.progress % 20 == 0:
    update_message(...)
```

**Öncelik:** P1  
**Tahmini Süre:** 2 saat  
**Bağımlılık:** Yok

---

### #7: Flux Stub - Message Update Blocking
**Dosya:** `app/image/flux_stub.py:152-158`  
**Durum:** 🟠 Açık

**Sorun:**
`update_message()` senkron DB call. Event loop blocking.

**Etki:**
- DB lock contention
- Diğer async tasks bekliyor

**Çözüm:**
```python
await asyncio.to_thread(update_message, job.message_id, None, {...})
```

**Öncelik:** P1  
**Tahmini Süre:** 2 saat  
**Bağımlılık:** Yok

---

### #8: Flux Stub - Retry Exponential Waste
**Dosya:** `app/image/flux_stub.py:70-94`  
**Durum:** 🟠 Açık

**Sorun:**
3 deneme × 60s timeout = 180s toplam bekleme!

**Etki:**
- 3 dakika kullanıcı beklemesi
- Client timeout (30s) → Connection drop

**Çözüm:**
```python
for attempt in range(max_retries):
    timeout = 60 / (2 ** attempt)  # 60s, 30s, 15s
    result = await _generate_image_internal(..., timeout=timeout)
```

**Öncelik:** P1  
**Tahmini Süre:** 1 saat  
**Bağımlılık:** Yok

---

### #9: Job Queue + GPU State - Double GPU Switch
**Dosya:** `app/image/job_queue.py:79` + `app/image/flux_stub.py:122`  
**Durum:** 🟠 Açık

**Sorun:**
`switch_to_flux()` iki yerde çağrılıyor:
1. job_queue.py:79
2. flux_stub.py:122 (içeride)

**Etki:**
- Gereksiz overhead
- Race condition riski

**Çözüm:**
job_queue.py'deki çağrıyı kaldır veya flux_stub.py'dekini kaldır.

**Öncelik:** P1  
**Tahmini Süre:** 1 saat  
**Bağımlılık:** Yok

---

### #10: GPU State - Thread Safety Yok
**Dosya:** `app/image/gpu_state.py:18-26`  
**Durum:** 🟠 Açık

**Sorun:**
`global current_state` thread-safe değil. Concurrent access durumunda `_unload_ollama()` iki kez çağrılabilir.

**Çözüm:**
```python
import threading
_state_lock = threading.Lock()

def switch_to_flux():
    global current_state
    with _state_lock:
        if current_state != ModelState.FLUX:
            ...
```

**Öncelik:** P1  
**Tahmini Süre:** 30 dakika  
**Bağımlılık:** Yok

---

## 🟡 P2 - MEDIUM (Code Quality)

### #11: Job Queue - Cancelled Job Memory Leak
**Dosya:** `app/image/job_queue.py:100-107`  
**Durum:** 🟡 Açık

**Sorun:**
`_cancelled_jobs: set[str]` sonsuz büyüyebilir. Temizleme sadece job işlendiğinde.

**Etki:**
- Yavaş memory leak (30 gün sonra MB'lar)

**Çözüm:**
```python
from collections import deque
self._cancelled_jobs = deque(maxlen=1000)  # FIFO
```

**Öncelik:** P2  
**Tahmini Süre:** 30 dakika  
**Bağımlılık:** Yok

---

### #12: Gateway - God Function Anti-Pattern
**Dosya:** `app/orchestrator_v42/gateway.py:try_handle()`  
**Durum:** 🟡 Açık

**Sorun:**
800+ satır tek fonksiyon. 15+ try-except, 50+ conditional branch.

**Metrikler:**
- Cyclomatic Complexity: ~45 (kabul edilebilir: <10)
- Testability: 2/10

**Çözüm:**
Refactor → 5-7 modül

**Öncelik:** P2  
**Tahmini Süre:** 2 gün  
**Bağımlılık:** Yok (ama büyük değişiklik)

---

### #13: Image Manager - Sloppy Error Handling
**Dosya:** `app/image/image_manager.py:116-120`  
**Durum:** 🟡 Açık

**Sorun:**
```python
except Exception as e:
    spec = None  # Sonra spec.checkpoint_name kullanılıyor!
```

**Etki:**
AttributeError riski

**Çözüm:**
Fallback spec objesi oluştur.

**Öncelik:** P2  
**Tahmini Süre:** 30 dakika  
**Bağımlılık:** Yok

---

### #14: GPU State - Blocking Sleep
**Dosya:** `app/image/gpu_state.py:24`  
**Durum:** 🟡 Açık

**Sorun:**
`time.sleep(2)` event loop'u 2 saniye blokluyor.

**Çözüm:**
```python
async def switch_to_flux():
    await asyncio.sleep(2)
```

**Öncelik:** P2  
**Tahmini Süre:** 2 saat (tüm çağrıları değiştirmek gerekiyor)  
**Bağımlılık:** #9 ile birlikte yapılabilir

---

## 📊 ÖZET

**Toplam Sorun:** 14  
**Critical (P0):** 5 sorun (3 saat)  
**High (P1):** 5 sorun (6.5 saat)  
**Medium (P2):** 4 sorun (5+ saat)

---

## 🎯 EYLEM PLANI

### Faz 1: Critical Hotfix (Bugün)
- [ ] #5: Circuit breaker on_done (15m)
- [ ] #2: Stats lock (30m)
- [ ] #3: Stats-DB rollback (1h)
- [ ] #4: Zombie task await (30m)
- [ ] #1: Gateway memory timeout (1h)

**Toplam:** 3 saat

### Faz 2: Stability (Yarın)
- [ ] #10: GPU thread safety (30m)
- [ ] #9: Double GPU switch (1h)
- [ ] #8: Retry timeout decay (1h)
- [ ] #6: Progress loop throttle (2h)
- [ ] #7: Message update async (2h)

**Toplam:** 6.5 saat

### Faz 3: Resilience (Bu Hafta)
- [ ] #11: Cancelled job cleanup (30m)
- [ ] #13: Sloppy error fix (30m)
- [ ] #14: Blocking sleep (2h - opsiyonel)
- [ ] Integration tests (2h)
- [ ] Monitoring dashboards (1.5h)

---

## 📝 NOTLAR

- Tüm fix'ler backward compatible
- Production'da feature flag ile kontrol edilebilir
- Rollback planı her fix için hazırlanmalı
- Unit test coverage artırılmalı

**Son Güncelleme:** 15 Ocak 2026, 23:13
