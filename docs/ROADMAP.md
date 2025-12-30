# 🗺️ Mami AI - Proje Yol Haritası (Roadmap)

**Son Güncelleme:** 19 Aralık 2025  
**Versiyon:** 2.2.0

---

## 📊 Genel Durum Özeti

| Kategori | Tamamlanan | Devam Eden | Planlanan |
|----------|------------|------------|-----------|
| Backend Core | 95% | 5% | - |
| Frontend (new-ui) | 90% | 10% | - |
| Hafıza Sistemi | 85% | 15% | - |
| Kalite Kontrol | 50% | 50% | - |
| Monitoring | 30% | 70% | - |

**Genel Kalite Skoru:** 8.8/10 → Hedef: 10/10

---

## ✅ TAMAMLANAN ÖZELLİKLER

### 🔙 Backend Sistemleri

#### Core Altyapı ✅
- [x] 5 Katmanlı Prompt Sistemi (Core, Persona, User Prefs, Toggles, Safety)
- [x] Smart Router (Groq/Local/Image/Internet yönlendirme)
- [x] Decider LLM (Semantik analiz ve aksiyon belirleme)
- [x] Answerer (Yanıt üretim modülü)
- [x] Streaming Response (SSE)

#### Hafıza & RAG ✅
- [x] ChromaDB tabanlı vektör depolama
- [x] Semantik arama & Soft delete
- [x] **Advanced Hybrid Duplicate Detection** (Semantik + Text + Entity) ✅
- [x] Doküman chunking (PDF, TXT)

#### Görsel Üretim ✅
- [x] Flux/Forge entegrasyonu
- [x] NSFW algılama ve checkpoint seçimi
- [x] **Safe Callback & Error Handling** (Hata toleransı artırıldı) ✅
- [x] WebSocket progress bildirimi
- [x] Async job queue (UUID tabanlı)

#### İnternet Araması ✅
- [x] Multi-provider search (DuckDuckGo, Google fallback)
- [x] Structured parsers (hava, döviz, spor)
- [x] Source attribution
- [x] Async parallel queries

#### Güvenlik & Yetki ✅
- [x] 3 seviyeli sansür (Unrestricted, Normal, Strict)
- [x] Pattern-based NSFW detection
- [x] User permission system
- [x] JWT authentication

#### Persona/Mod ✅
- [x] 7 hazır persona
- [x] DB'den dinamik persona yönetimi
- [x] requires_uncensored → otomatik local model

### 🖥️ Frontend (ui-new) ✅

- [x] Responsive Chat Layout (Desktop + Mobile)
- [x] Streaming yanıt gösterimi
- [x] Code blocks + syntax highlighting
- [x] Memory Manager modal
- [x] Settings panel (4 sekme)
- [x] Command Palette (slash komutları)
- [x] Search (Ctrl+K)
- [x] Export/Import
- [x] Image Gallery
- [x] PWA desteği

---

## 🔴 FAZ 1: KRİTİK İYİLEŞTİRMELER (Güncel Durum)

### 1.1 Hafıza Sistemi 🧠
**Durum:** Büyük ölçüde tamamlandı.

| İş | Açıklama | Durum |
|----|----------|-------|
| Structured User Profile | Sabit alanlar: name, age, etc. | ⏳ Devam Ediyor |
| Duplicate Detection | Hibrit sistem (Semantik + Text) | ✅ **Tamamlandı** |
| Memory Decider | Gereksiz bilgileri reddetme | ✅ **Tamamlandı** |
| Cleanup script | Mevcut yanlış hafızaları temizle | ✅ **Tamamlandı** |

### 1.2 Cevap Kalite Kontrolü ✅
**Öncelik:** 🔴 Yüksek

| Kontrol | Açıklama | Durum |
|---------|----------|-------|
| Uzunluk kontrolü | Tercih edilen uzunluğa uygunluk | ⏳ |
| Yarım cümle düzeltme | Tamamlanmamış cümleleri tespit | ⏳ |
| Kod bloğu kontrolü | Kapanmamış ``` tespit et | ⏳ |

### 1.3 Regenerate Endpoint 🔄
**Öncelik:** 🔴 Yüksek
- [ ] Mesajı yeniden üretme API'si (Frontend butonu hazır, backend endpoint bekleniyor)

### 1.4 Search Result Cache 🔍
**Öncelik:** 🔴 Yüksek
- [ ] Döviz/Hava durumu sorguları için 5-15 dk cache

---

## 🟡 FAZ 2: ÖNEMLİ İYİLEŞTİRMELER

### 2.1 ML-Based Content Moderation 🛡️
- [ ] Pattern matching + OpenAI Moderation API
- [ ] Audit logging

### 2.2 Memory Decay Mechanism ⏳
- [ ] 30 günde kullanılmazsa önem puanı düşürme

### 2.3 Routing Cache 🚀
- [ ] Benzer sorular için router kararını cache'leme

### 2.4 Sliding Window + Summary 📜
- [ ] Uzun sohbetlerde bağlamı korumak için özetleme mekanizması

---

## 🟢 FAZ 3: İYİLEŞTİRMELER

### 3.1 Custom Persona Creator 🎭
- [ ] Kullanıcının kendi persona'sını yaratması

### 3.2 Batch Image Generation 🎨
- [ ] Tek prompt ile 4 varyasyon

---

## 📋 TEKNİK BORÇ (Technical Debt)

### Yüksek Öncelik
- [ ] `deleteAllConversations` frontend call (backend endpoint yok)
- [ ] Import functionality
- [ ] Feedback API frontend entegrasyonu

### Çözülenler
- [x] `IMAGE_QUEUE` ID mismatch sorunu (UUID geçişi tamamlandı)
- [x] Callback error handling (SafeCallback uygulandı)

---

## 📚 İLGİLİ DOKÜMANLAR

| Doküman | Açıklama |
|---------|----------|
| [PROJECT_IMPROVEMENTS_AND_ISSUES.md](./PROJECT_IMPROVEMENTS_AND_ISSUES.md) | Güncel sorun ve öneri listesi |
| [QUALITY_MASTER_PLAN.md](./QUALITY_MASTER_PLAN.md) | Kapsamlı kalite planı |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Sistem mimarisi |
