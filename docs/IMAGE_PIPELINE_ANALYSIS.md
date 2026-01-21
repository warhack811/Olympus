# RESİM ÜRETİM HATTI - DETAYLI ANALİZ RAPORU

**Tarih:** 15 Ocak 2026, 23:26  
**Analiz Eden:** Cline  
**Durum:** Acil Sorunlar Tespit Edildi

---

## 🔍 MEVCUT DURUM SORUNLARI

### 1. ❌ PROMPT GÖNDERİLMİYOR (Değil - Ama Karmaşık)
### 2. ⚠️ IMAGE_PENDING ÇALIŞMIYOR 
### 3. ⚠️ RESİM SAYFAYA DÜŞMÜYOR

---

## 📊 AKIM DİYAGRAMI (MEVCUT)

```
USER REQUEST ("bir kedi resmi çiz")
    ↓
processor.py:process_chat_message()
    ↓
[ROUTING] SmartRouter → RoutingTarget.IMAGE
    ↓
action = "IMAGE"
    ↓
1. build_image_prompt(message) ← GROQ ile zenginleştirme
    ↓
2. job_id = uuid4() ← ÖNCEKİ job ID
    ↓
3. append_message() ← SYNC mesaj oluştur
   └─> DB'ye "[IMAGE_PENDING]..." yaz
   └─> message_id al
    ↓
4. asyncio.create_task(_start_job()) ← ASYNC job başlat
   └─> request_image_generation()
       └─> ImageJob oluştur
       └─> job_queue.add_job(job)
       └─> update_message() ← "[IMAGE_PENDING]" tekrar yaz (DUPLICATE!)
    ↓
5. Return "[IMAGE_QUEUED:job_id:message_id]" ← Frontend'e JSON
```

---

## 🚨 TESPİT EDİLEN SORUNLAR

### SORUN #1: DOUBLE MESSAGE UPDATE (Kritik!)

**Konum:** `processor.py:L870-880` + `image_manager.py:L183-192`

**Akış:**
```python
# processor.py:L870 - SYNC
placeholder_msg = append_message(
    text="[IMAGE_PENDING] Görsel isteğiniz kuyruğa alındı...",
    extra_metadata={"type": "image", "status": "queued", "job_id": job_id}
)
message_id = placeholder_msg.id

# processor.py:L884 - ASYNC başlat
asyncio.create_task(_start_job())

# _start_job içinde:
request_image_generation(message_id=message_id, job_id=job_id, ...)

# image_manager.py:L183 - İKİNCİ KEZ!
update_message(
    message_id,
    "[IMAGE_PENDING] Görsel isteğiniz kuyruğa alındı...",  # AYNI METİN!
    {"status": "queued", ...}
)
```

**Sonuç:**
- Mesaj iki kez yazılıyor (race condition)
- İkinci update ilkini eziyor
- Frontend'de flicker olabilir
- DB'ye gereksiz write

**Çözüm:** `image_manager.py:L183-192` bloğunu kaldır! Mesaj zaten processor'da oluşturulmuş.

---

### SORUN #2: PROMPT GROQ'A GÖNDERİLİYOR (Yavaş!)

**Konum:** `processor.py:L730-755 (build_image_prompt)`

**Akış:**
```python
# Normal mesaj (! ile başlamıyorsa)
detail_messages = [
    {"role": "system", "content": "You are an image prompt translator..."},
    {"role": "user", "content": user_message}
]
detailed, _ = await call_groq_api_safe_async(detail_messages, ...)
prompt = detailed.strip()
```

**Sorun:**
- Her resim isteği için Groq API çağrısı yapılıyor
- +500ms - 2s ek gecikme
- Groq quota tüketimi
- Kullanıcı "a red apple" yazsa bile Groq'a gidiyor

**Etki:**
- Kullanıcı 2-3 saniye bekliyor (prompt hazırlama)
- Sonra queue'ya giriyor
- Sonra üretim başlıyor
- **Toplam 30+ saniye gecikme**

**Çözüm Önerileri:**

**Opsiyon A: Prefix-based bypass (Mevcut sistem genişletme)**
```python
# ! ile başlarsa raw
# !! ile başlarsa raw + no guard
# !!! ile başlarsa raw + no guard + NO GROQ ← YENİ
if normalized.startswith("!!!"):
    return normalized[3:].strip()
```

**Opsiyon B: Basit metinleri geçir**
```python
# Eğer mesaj 5 kelimeden azsa ve İngilizce ise Groq'a gitme
words = user_message.strip().split()
if len(words) <= 5 and is_english(user_message):
    return user_message  # Direkt kullan
```

**Opsiyon C: Cache ekle**
```python
# Aynı prompt'u 1 saat içinde cache'den al
@lru_cache(maxsize=100)
async def build_image_prompt_cached(user_message, ...):
    ...
```

---

### SORUN #3: FRONTEND RESPONSE FORMAT HATA

**Konum:** `processor.py:L896`

```python
return f"[IMAGE_QUEUED:{job_id}:{message_id}]", semantic
```

**Sorun:**
- Frontend bu formatı bekliyor mu?
- `[IMAGE_QUEUED:...]` marker'ını parse ediyor mu?
- WebSocket event'i yerine mi kullanılıyor?

**Test Gerekli:** Frontend kodlarını oku:
- `ui-new/src/hooks/useImageProgress.ts`
- `ui-new/src/components/MessageBubble.tsx`

---

### SORUN #4: WEBSOCKET EVENT EKSİK

**Konum:** `image_manager.py:L183-198`

```python
update_message(message_id, "[IMAGE_PENDING]...", {...})

# WebSocket event - AYRI task
asyncio.create_task(
    send_progress(username, conversation_id, 0, queue_pos, ...)
)
```

**Sorun:**
- `create_task()` exception fırlatırsa sessizce fail oluyor
- Try-except yok
- Frontend event alamıyor olabilir

**Çözüm:**
```python
try:
    await send_progress(...)  # Direkt await et
except Exception as e:
    logger.error(f"[IMAGE] WS event gönderilemedi: {e}")
```

---

### SORUN #5: IMAGE_PATH FRONTEND PARSE

**Konum:** `image_manager.py:L93`

```python
update_message(
    message_id,
    f"[IMAGE] Resminiz hazır.{prompt_snippet}\nIMAGE_PATH: {result}",
    {"status": "complete", "image_url": result}
)
```

**Şüpheli Noktalar:**
1. Frontend `IMAGE_PATH:` string'ini parse ediyor mu?
2. `\n` karakteri problemi var mı?
3. `result` formatı doğru mu? (`/images/flux_123.png`)

**Test:** Frontend'de şu regex'i ara:
```typescript
/IMAGE_PATH:\s*(.+)/g
```

---

## 🎯 ÖNCELİKLİ ÇÖZÜM PLANI

### Faz 1: Backend Hotfix (30 dakika)

**1. Double Message Update Kaldır**
```python
# image_manager.py:L183-192 - KALDIR
# Mesaj zaten processor.py'de oluşturulmuş
```

**2. WebSocket Exception Handling**
```python
# image_manager.py:L193-198
try:
    await send_progress(...)  # create_task yerine direkt await
except Exception as e:
    logger.error(f"[IMAGE] WS error: {e}")
```

**3. Prompt Bypass Ekle**
```python
# processor.py:build_image_prompt() başına
if user_message.strip().startswith("!!!"):
    return user_message[3:].strip()  # NO GROQ
```

### Faz 2: Frontend Kontrol (15 dakika)

**Okunacak dosyalar:**
- `ui-new/src/hooks/useImageProgress.ts`
- `ui-new/src/components/MessageBubble.tsx`
- `ui-new/src/components/ImageProgressCard.tsx`

**Aranacak pattern'ler:**
- `[IMAGE_PENDING]` regex
- `[IMAGE_QUEUED:...]` parse
- `IMAGE_PATH:` regex
- WebSocket event listener: `image_progress`

### Faz 3: Entegrasyon Test (10 dakika)

**Test senaryosu:**
```python
# Backend'de şunu çalıştır
async def test_image_flow():
    from app.chat.processor import process_chat_message
    from app.core.models import User
    
    user = User(id=1, username="test_user")
    
    result, semantic = await process_chat_message(
        username="test_user",
        message="a red apple",
        user=user,
        conversation_id="test-conv-123"
    )
    
    print(f"Result: {result}")
    # Beklenen: [IMAGE_QUEUED:uuid:message_id]
```

---

## 📋 DEBUG CHECKLİST

### Backend Log Kontrolü
```bash
# 1. Processor giriş
grep "ROUTER.*IMAGE" logs/app.log

# 2. Prompt oluşturma
grep "IMAGE_PROMPT" logs/app.log

# 3. Message oluşturma
grep "IMAGE.*Mesaj oluşturuldu" logs/app.log

# 4. Job başlatma
grep "IMAGE.*Job başlatıldı" logs/app.log

# 5. Queue ekleme
grep "IMAGE_QUEUE.*İş eklendi" logs/app.log

# 6. Progress events
grep "send_image_progress" logs/app.log
```

### DB Kontrolü
```sql
-- Son oluşturulan image mesajları
SELECT id, content, metadata, created_at 
FROM messages 
WHERE metadata->>'type' = 'image' 
ORDER BY created_at DESC 
LIMIT 10;

-- Pending durumda kalan mesajlar
SELECT id, content, metadata 
FROM messages 
WHERE metadata->>'status' = 'queued' 
  AND created_at < NOW() - INTERVAL '5 minutes';
```

---

## 🔧 ÖNER İLEN FİXLER (KOD)

### Fix #1: processor.py - Prompt Bypass

```python
# processor.py:L730 (build_image_prompt başında)

async def build_image_prompt(user_message: str, style_profile: dict[str, Any] | None = None) -> str:
    """Görsel üretimi için prompt oluşturur."""
    
    normalized = user_message.strip()
    
    # !!! prefix: NO GROQ, NO GUARD, RAW
    if normalized.startswith("!!!"):
        prompt = normalized[3:].strip()
        logger.info(f"[IMAGE_PROMPT] BYPASS MODE | '{user_message}' -> '{prompt}'")
        return prompt
    
    # !! prefix: RAW + NO GUARD
    if normalized.startswith("!!"):
        prompt = normalized[2:].strip()
        logger.info(f"[IMAGE_PROMPT] RAW MODE | '{user_message}' -> '{prompt}'")
        return prompt
    
    # ... (mevcut kod devam)
```

### Fix #2: image_manager.py - Double Update Kaldır

```python
# image_manager.py:L175-192 - TAMAMINI KALDIR

# İlk durumu mesaja yaz - KALDIRILDI (processor.py'de yapılıyor)
# update_message(...) ← BU SATIR KALDIRILDI

# WebSocket ile progress gönder - KALDIR (try-except ile değiştir)
# asyncio.create_task(...) ← BU DA KALDIRILDI
```

### Fix #3: image_manager.py - WebSocket Direct Await

```python
# image_manager.py:L175 civarı (update_message çağrısından SONRA)

# WebSocket event (direkt await)
try:
    await send_progress(
        username=username,
        conversation_id=conversation_id,
        progress=0,
        queue_position=queue_pos,
        job_id=job.job_id,
        message_id=message_id,
    )
except Exception as e:
    logger.error(f"[IMAGE_MANAGER] WebSocket event error: {e}")
```

---

## ❓ YANIT BEKLEYENler

1. **Frontend `[IMAGE_QUEUED:...]` formatını parse ediyor mu?**
   - Yoksa değiştirmemiz gerekir

2. **WebSocket event'i frontend dinliyor mu?**
   - `useImageProgress.ts` hook'u var mı?

3. **`IMAGE_PATH:` marker'ı frontend'de aranıyor mu?**
   - MessageBubble.tsx'te regex var mı?

4. **Prompt Groq bypass'ı kullanıcıya açıklanmalı mı?**
   - Dokümantasyon gerekir mi?

---

## 🚀 BİR SONRAKİ ADIMLAR

1. ✅ Backend hotfix'leri uygula (30dk)
2. 🔄 Frontend kodlarını oku (15dk) ← ŞİMDİ BURADAY IZ
3. 🔄 Entegrasyon test (10dk)
4. 🔄 Production deploy

**Toplam tahmini süre:** 55 dakika

---

**Son Güncelleme:** 15 Ocak 2026, 23:26
