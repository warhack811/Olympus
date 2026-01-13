# 🏛️ ATLAS CORE v1 - Teknik Uygulama Planı (Revize)

**Tarih:** 1 Ocak 2026  
**Versiyon:** 1.4.0 (Proaktif, Cascading Intent, RAG v3 entegre)  
**Hedef:** 10 Premium Müşteri için Production-Ready AI Sistemi  
**Tahmini Süre:** 9-10 hafta (tek kişi) / 6-7 hafta (2 kişi)

---

## 📋 İlerleme Durumu

| Faz | Durum | İlerleme |
|-----|-------|----------|
| Faz 0: Kritik Düzeltmeler | ⏳ Bekliyor | 0% |
| Faz 1: Core Orchestrator | ⏳ Bekliyor | 0% |
| Faz 2: Intelligence + Quality Spine | ⏳ Bekliyor | 0% |
| Faz 3A: Solid RAG (V1) | ⏳ Bekliyor | 0% |
| Faz 3B: Graph RAG (V2) | ⏳ Bekliyor | 0% |
| Faz 4: Tools & Memory | ⏳ Bekliyor | 0% |
| Faz 5: Admin Panel | ⏳ Bekliyor | 0% |
| Faz 6: Polish & Deploy | ⏳ Bekliyor | 0% |

---

## 🎯 STRATEJİK KARARLAR

### 🏆 Rekabet Avantajı (Neden Bizi Seçmeli?)

| Özellik | ChatGPT | Claude | **ATLAS CORE** |
|---------|---------|--------|----------------|
| **TR Quality** | %70-80 | %75-85 | **%95+** ✅ |
| **KVKK Compliance** | ❌ Yok | ❌ Yok | **✅ Tam uyum** |
| **Private Deployment** | ❌ | ❌ | **✅ Veri TR'de** |
| **Custom Tools** | Sınırlı | Sınırlı | **✅ Müşteriye özel** |
| **Proaktif Asistan** | ❌ Reaktif | ❌ Reaktif | **✅ Hatırlatıcı + öneri** |
| **Intent Maliyeti** | Her mesaj LLM | Her mesaj LLM | **%60-70 rule-based** |

### Teknoloji Stack (Enterprise-Grade)

| Bileşen | Mevcut | Hedef | Gerekçe |
|---------|--------|-------|---------|
| **Ana DB** | SQLite | **PostgreSQL** | ACID, FTS, scale |
| **Vector DB** | ChromaDB | **pgvector** | Tek DB, operasyonel basitlik |
| **Cache/Queue** | Redis | **Redis (genişletilmiş)** | Session, cache, pub/sub, working memory |
| **Migration** | - | **Alembic** | Şema versiyonlama, geri uyumluluk |

### SLA Hedefleri (Premium Müşteri)

| Metrik | Hedef | Kabul Edilebilir | Alarm |
|--------|-------|------------------|-------|
| **Uptime** | %99.5 | %99 | <%99 |
| **TTFT (p50)** | <500ms | <1000ms | >1000ms |
| **Total Latency (p95)** | <5s | <8s | >8s |
| **Hallucination Rate** | <%2 | <%5 | >%5 |
| **TR Quality Score** | %95+ | %90+ | <%90 |
| **Citation Coverage** | %90+ | %85+ | <%85 |
| **Rate Limit Hit** | <%1 | <%5 | >%5 |

### Başarı Kriterleri

| Ölçüm | Minimum | Hedef |
|-------|---------|-------|
| **Golden Set Pass Rate** | %90 | %95+ |
| **Multi-Task Accuracy** | %85 | %92+ |
| **Follow-Up Resolution** | %80 | %90+ |
| **User Satisfaction** | 4.0/5 | 4.5+/5 |

### Rollout Stratejisi

```
Local Dev → Staging (CI/CD) → Prod %10 → %30 → %70 → %100
                  ↓
            Golden Set
            Automated
               Test
```

| Aşama | Kriter | Geri Dönüş |
|-------|--------|------------|
| Staging | Golden Set %95+ | Fix & retry |
| Prod %10 | 24 saat metrik izleme | Instant rollback |
| Prod %30 | 48 saat, hata <%1 | Rollback to %10 |
| Prod %70 | 1 hafta, SLA karşılanıyor | Rollback to %30 |
| Prod %100 | Full production | - |

### Zaman Planı

| Senaryo | Süre | Açıklama |
|---------|------|----------|
| **Tek kişi** | 9-10 hafta | Faz'lar sıralı |
| **2 kişi** | 6-7 hafta | Backend + Quality paralel |
| **3+ kişi** | 5-6 hafta | Frontend de paralel |

**Önerilen Paralel Plan (2 kişi):**
```
Kişi 1 (Backend):        Kişi 2 (Quality/Test):
───────────────────      ───────────────────
Faz 0: Endpoint'ler      Faz 0: Metrikler + Mock
Faz 1: Orchestrator      Faz 1: Golden Set v0
Faz 2: Verifiers         Faz 2: Test coverage
Faz 3: RAG               Faz 3: RAG test suite
Faz 4: Tools             Faz 4: E2E tests
Faz 5: Admin Panel       Faz 5: UI tests
Faz 6: Deploy            Faz 6: Load test
```

---

## � KALİTE KONTRATI (Non-Negotiable)

> Her yanıt bu 5 kapıdan geçmeden kullanıcıya dönmez.

| # | Kapı | Ne Kontrol Eder | Geçemezse |
|---|------|-----------------|-----------|
| 1 | **Coverage Check** | Her task cevapta karşılandı mı? | Eksik task için tamamlama turu |
| 2 | **Groundedness Check** | İddialar kanıtlandı mı? | "Emin değilim" etiketi + rewrite |
| 3 | **Tool Safety Check** | Tool output injection var mı? | Yazma eylemi → onay |
| 4 | **TR Kalite Kapısı** | Dil, imla, yasak kalıplar | 2-pass rewrite |
| 5 | **Tutarlılık Check** | Çelişki, ton, format | Synthesizer ile düzeltme |

---

## 📐 CANONICAL TASKSPEC (Şema)

> Her mesaj için tek format:

```json
{
  "tasks": [
    {
      "id": "task_1",
      "intent": "email_write",
      "input": "müşteriye özür maili",
      "expected_output": "email_text",
      "constraints": {"tone": "formal", "length": "short"},
      "depends_on": [],
      "tool_needs": [],
      "privacy_class": "low",
      "priority": 1
    }
  ],
  "execution_plan": {
    "parallel_groups": [["task_1", "task_2"], ["task_3"]],
    "timeouts": {"task_1": 10},
    "budgets": {"tokens": 2000}
  },
  "answer_plan": {
    "format": "numbered_list",
    "sections": ["mail", "plan", "reminder"]
  }
}
```

---

## 🎨 MEVCUT UI ÖZELLİKLERİ (Entegrasyon Gerekli)

> Bu özellikler UI'da var, backend ile tam entegrasyon planlanmalı.

| Özellik | UI Durumu | Backend Durumu | Plan Notu |
|---------|-----------|----------------|-----------|
| **Response Style** (tone, emoji, length) | ✅ SettingsSheet | ⚠️ Kısmi kullanım | Faz 2: Adaptive Stylist'e entegre |
| **Personas/Modlar** (7 adet) | ✅ SettingsSheet | ✅ `/personas` API | Prompt Manager'dan yönetilecek |
| **Themes** (13 tema) | ✅ AppearanceTab | ✅ Client-side | Tamam |
| **Memory Tab** | ✅ SettingsSheet | ✅ `/memories` | Selective Writer ile güçlenecek |
| **Image Settings** | ✅ SettingsSheet | ✅ Forge API | Tamam |
| **Future Plans** | ✅ SettingsSheet | ⚠️ Client-only | Scheduler Service ile senkronize |
| **Documents Tab** | ✅ SettingsSheet | ✅ `/documents` | Parser'lar genişleyecek |
| **OrchDebugPanel** | ✅ Chat | ✅ `/orch/snapshot` | RDR Explorer ile genişleyecek |

---

## 🔴 FAZ 0: KRİTİK DÜZELTMELER (3 Gün)

### Adım 0.1: Backend Eksik Endpoint'ler
- [ ] **Regenerate Endpoint** - `/api/chat/regenerate`
- [ ] **deleteAllConversations** - `/api/admin/conversations/delete-all`
  - Soft-delete + retention + audit log
- [ ] **Export/Import** - `/api/conversations/export`, `/import`
  - Şifreli export dosyası
  - authz kontrolü

### Adım 0.2: Search Result Cache
- [ ] Redis cache (5-15 dk TTL)

### Adım 0.3: Output Gate (Unified)
> Response Quality Checker + TR Gate birleşik:
- [ ] Uzunluk kontrolü
- [ ] Yarım cümle düzeltme
- [ ] Kapanmamış kod bloğu
- [ ] JSON/Markdown bütünlüğü
- [ ] TR kalite (yabancı kelime, yasak kalıp)

### Adım 0.4: Feedback Entegrasyonu
- [ ] MessageBubble'a like/dislike butonları

### Adım 0.5: Future Plans Backend Sync (YENİ)
- [ ] `/api/plans` endpoint (CRUD)
- [ ] DB persistence (şu an client-only)
- [ ] Scheduler Service ile bağlantı hazırlığı

### Adım 0.6: Response Style Backend Kullanımı (YENİ)
- [ ] `style_profile` parametresini LLM prompt'a inject et
- [ ] tone, emoji_level, length kontrolü

### Adım 0.7: Mevcut Admin Endpoint Kontrolü
- [ ] `/system/features/toggle` → Runtime Config entegrasyonu
- [ ] `/admin/summary-settings` → Conversation summary ayarları
- [ ] `/admin/usage/messages` → Analytics bağlantısı

### Adım 0.8: Ürün Güvenliği Katmanı (YENİ - KRİTİK)
> Bu maddeler olmadan "aylarca test" mümkün değil.

- [ ] **PostgreSQL + pgvector Kurulum**
  - PostgreSQL 15+ kurulum
  - pgvector extension
  - SQLite → PostgreSQL data migration scripti
  - ChromaDB → pgvector migration planı (Faz 3A'da)

- [ ] **DB Şema Versiyonlama**
  - Alembic migration'ları
  - Sohbet/mesaj formatı geri uyumluluğu
  - RDR saklama şeması

- [ ] **Mock & Chaos Engineering**
  - Groq API mock (test ortamı)
  - Rate-limit simülatörü
  - Hata enjeksiyonu (tool failure, timeout)

- [ ] **Temel Metrikler (Day 1)**
  - TTFT (Time To First Token)
  - Toplam süre (p50, p95, p99)
  - Model bazlı hata oranı
  - Tool başarı oranı
  - Gate başarısızlık oranı

- [ ] **Trace Kimliği**
  - Her istekte `request_id`
  - Tüm adımları bu ID'ye iliştir
  - Log correlation

- [ ] **Staging Ortamı**
  - Ayrı PostgreSQL instance
  - Golden Set CI/CD entegrasyonu
  - Otomatik test pipeline

- [ ] **User-Level Rate Limiter (YENİ - KRİTİK)**
  - Redis-based token bucket
  - Per-user RPM: 10 (normal), 30 (premium)
  - Endpoint: `/api/chat`
  - 429 response with retry-after header

- [ ] **Structured Logging (YENİ)**
  - JSON formatter (structlog)
  - Request ID middleware (UUID per request)
  - Log rotation (max 100MB per file)
  - Log levels: DEBUG (dev), INFO (prod)

**Definition of Done:** PostgreSQL, user rate limiter, structured logging çalışıyor, staging hazır.

---

## ⚡ FAZ 1: CORE ORCHESTRATOR (1 Hafta)

> Router değil, Orchestrator. DAG + RDR burada başlar.

### Adım 1.1: Enterprise Key Manager
```
Dosya: app/orchestrator_v42/key_manager.py
```
- [ ] 4 API key tanımlama
- [ ] Least-loaded selection
- [ ] Cooldown mechanism (429)
- [ ] Health tracking

### Adım 1.2: Budget Tracker
```
Dosya: app/orchestrator_v42/budget_tracker.py
```
- [ ] Model bazlı RPD/TPD
- [ ] Key bazlı kullanım
- [ ] Günlük reset
- [ ] Eşik uyarıları

### Adım 1.3: DAG Executor (YENİ - KRİTİK)
```
Dosya: app/orchestrator_v42/dag_executor.py
```
- [ ] TaskSpec parsing
- [ ] Topological sort
- [ ] Cycle detection
- [ ] Paralel/sıralı execution
- [ ] Per-task budgets
- [ ] Partial failure handling

### Adım 1.4: Synthesizer (YENİ - KRİTİK)
```
Dosya: app/orchestrator_v42/synthesizer.py
```
- [ ] Multiple task outputs → single response
- [ ] Consistent tone/persona
- [ ] Section formatting
- [ ] Conflict resolution

### Adım 1.4b: Time & Context Awareness (YENİ)
```
Dosya: app/orchestrator_v42/context_manager.py
```
> Rule-based, LLM gereksiz. Maliyetsiz.

- [ ] **Zaman Farkındalığı**
  - Temporal greeting: "Günaydın" / "İyi akşamlar" (saat bazlı)
  - Current date/time injection to LLM context
  - "Bugün Çarşamba" gibi referanslar

- [ ] **Calendar Awareness**
  - Upcoming events (sonraki 24 saat)
  - Deadline'lar (proaktif uyarı)
  - "10 dk sonra toplantın var" context

- [ ] **Urgency Detection (Rule-based)**
  - Keywords: "ACİL", "HEMEN", "DEADLINE"
  - Priority boost when detected

### Adım 1.5: RDR (Routing Decision Record) - ÜRÜN SÖZLEŞMESİ
```
Dosya: app/orchestrator_v42/rdr.py
```
> RDR sadece debug log değil, ürün sözleşmesidir.

- [ ] **Temel Alanlar**
  - request_id, timestamp, user_id
  - intent, tasks[], tier, model, key
  - safety_flags, tool_calls

- [ ] **Gizlilik Sınıfı**
  - privacy_class: low | medium | high | critical

- [ ] **Dış İçerik Kullanımı**
  - web_sources_count
  - rag_docs_count
  - tool_outputs_count
  - source_ids[]

- [ ] **Kalite Kapısı Skorları**
  - coverage_score (0-1)
  - citation_score (0-1)
  - tr_quality_score (0-1)

- [ ] **Yanıt Sözleşmesi**
  - total_tasks
  - completed_tasks
  - partial_tasks
  - failed_tasks
  - failed_reasons[]

- [ ] DB persistence + query API

### Adım 1.6: Quality Tier Router
```
Dosya: app/orchestrator_v42/tier_router.py
```
- [ ] Tier tanımları
- [ ] 3 model horizontal scaling
- [ ] Fallback chain
- [ ] Output: RDR'ye yazılan tek şema

### Adım 1.7: Circuit Breaker v2 (GELİŞTİRİLDİ)
```
Dosya: app/orchestrator_v42/circuit_breaker.py
```
> 3-state machine: CLOSED → OPEN → HALF_OPEN

- [ ] **State Transitions**
  - CLOSED → OPEN: %10 fail (son 100 req) veya 3 ardışık timeout
  - OPEN → HALF_OPEN: Exponential backoff (30s → 60s → 120s → 300s)
  - HALF_OPEN → CLOSED: 10 test request hepsi başarılı
  - HALF_OPEN → OPEN: 1 fail → tekrar OPEN

- [ ] **Per-Component Breakers**
  - Groq API (model bazlı)
  - PostgreSQL
  - Redis
  - pgvector search
  - Web search
  - Her tool (Gmail, Calendar, etc.)

- [ ] **Static Response (Tüm breakerlar açık)**
  - "Teknik sorun yaşıyoruz. 2 dk içinde otomatik düzelecek."
  - Ticket ID generation + support notification

### Adım 1.8: OpenTelemetry Trace (ERKEN)
```
Dosya: app/observability/tracer.py
```
- [ ] Trace ID injection (Faz 1'de başlasın)
- [ ] Span: intent → tier → model → tool → output
- [ ] Latency breakdown

### Adım 1.9: Golden Set v0 (YENİ - ERKEN BAŞLA)
> Faz 6'yı beklemeden regresyon kapısını kur.

- [ ] **Minimum 50 örnek:**
  - Çoklu görev parçalama (10 örnek)
  - Follow-up referans çözme (10 örnek)
  - Tool injection güvenliği (5 örnek)
  - TR kalite (10 örnek)
  - RAG kanıt kapsaması (10 örnek)
  - "Emin değilim" davranışı (5 örnek)

- [ ] Automated test runner
- [ ] Metrik hesaplama (pass/fail + skor)
- [ ] Regresyon kapısı: skor düşerse CI fail

### Adım 1.10: Graceful Degradation Matrix (GELİŞTİRİLDİ)
> Partial response > No response. Her fail mode için fallback.

| Bileşen Fail | Fallback | Kalite Kaybı |
|--------------|----------|--------------|
| RAG Fail | LLM-only mode | Citation yok, "genel bilgi" uyarısı |
| Citation Verifier Fail | Skip verifier | [Emin değilim] etiketi yok |
| TR Gate Fail | Basic regex only | Kalite %10 düşer |
| Tool Timeout | Continue without tool | "X yapılamadı" notu |
| Redis Fail | DB-backed session | 2x latency |
| pgvector Fail | BM25 keyword only | Semantic search yok |
| All Models Fail | Maintenance mode | "Bakımdayız" sayfası |

- [ ] Her bileşen için fallback handler
- [ ] Kalite kaybı logging (RDR'ye yaz)
- [ ] User notification (ne çalışmadı söyle)

**Definition of Done:** Orchestrator çalışıyor, RDR kaydediliyor, Golden Set v0 hazır, graceful degradation matrix aktif.

---

## 🧠 FAZ 2: INTELLIGENCE + QUALITY SPINE (1 Hafta)

> Kalite kapıları burada "deterministic gate" olarak çalışır.

### Adım 2.1: Intent Classifier (4-TİER CASCADING)
```
Dosya: app/orchestrator_v42/intent_classifier.py
```
> Maliyet %80 düşer, latency %60 azalır.

- [ ] **Tier 0: Rule-Based (0ms, $0)**
  - Regex + keyword matching
  - "Merhaba" → greeting (0.99 confidence)
  - "mail at" → email_send (0.90)
  - **Hedef: %60-70 mesaj buradan çözülsün**

- [ ] **Tier 1: 8B-instant (200ms)**
  - JSON schema output
  - Confidence > 0.85 → kabul
  - **Hedef: %20-25 mesaj**

- [ ] **Tier 2: Scout-17B (500ms)**
  - Chain-of-thought reasoning
  - Belirsiz/çoklu görevler
  - **Hedef: %5-10 mesaj**

- [ ] **Tier 3: 70B (1000ms) - Son Çare**
  - Multi-perspective analysis
  - TR çoklu görev zayıfsa
  - **Hedef: %2-5 mesaj**

- [ ] Turkish Intent Patterns (regex library)
- [ ] Output: TaskSpec

### Adım 2.2: Safety Layer (Paralel)
```
Dosya: app/orchestrator_v42/safety_layer.py
```
- [ ] Prompt-Guard (injection)
- [ ] Llama-Guard (content)
- [ ] DLP/PII regex

### Adım 2.3: Privacy Classifier (YENİ)
```
Dosya: app/orchestrator_v42/privacy_classifier.py
```
- [ ] Fail-closed: belirsizde buluta gitme
- [ ] privacy_class: low, medium, high, critical
- [ ] Redaction raporu
- [ ] Cloud-send onay (kritik sınıfta)

### Adım 2.4: Redaction Service (YENİ)
```
Dosya: app/orchestrator_v42/redaction.py
```
- [ ] Local maskeleme
- [ ] Redaction raporu (ne maskelendi)
- [ ] Redaction recovery (cevapta restore)

### Adım 2.5: Coverage Verifier (YENİ - QUALITY SPINE)
```
Dosya: app/orchestrator_v42/coverage_verifier.py
```
- [ ] Task'leri cevapta eşle
- [ ] Eksik task → tamamlama turu
- [ ] "Kısmi cevap sözleşmesi" (başarısız task açıkça işaretlenir)

### Adım 2.6: Citation Verifier (KADEMELİ + DETERMİNİSTİK)
```
Dosya: app/orchestrator_v42/citation_verifier.py
```
> Maliyet kontrolü + doğruluk için kademeli yaklaşım:

- [ ] **Kademe 1: Deterministik Claim Tespiti**
  - Sayı, tarih, yüzde içeren cümleler
  - "X böyledir", "kesinlikle", "her zaman" kalıpları
  - Heuristic extraction (LLM çağrısı yok)

- [ ] **Kademe 2: Evidence Coverage**
  - Her claim için kaynak eşleştirme
  - RAG doc_id, web URL, tool output
  - Eşleşme skoru hesaplama

- [ ] **Kademe 3: LLM Verifier (Sadece Gri Alan)**
  - Belirsiz claim'ler için LLM kontrolü
  - Maliyet: sadece gerektiğinde

- [ ] **Kademe 4: Aksiyon**
  - Eşleşmezse → [Emin değilim] etiketi
  - Veya → "kanıt yok, arayayım mı?" önerisi
  - **Deterministik kapı** (geçemezse yanıt dönmez)

### Adım 2.7: TR Language Gate (KADEMELİ + DETERMİNİSTİK)
```
Dosya: app/orchestrator_v42/tr_gate.py
```
> LLM'e yaslanmadan önce deterministik yardımcılar:

- [ ] **Deterministik Kontroller (LLM öncesi)**
  - Yasak kalıp blocklist taraması
  - Yabancı kelime oranı < %5
  - Noktalama/kapanmayan blok kontrolü
  - Türkçe yazım sözlüğü taraması (hunspell)

- [ ] **Kademeli Rewrite**
  - Düşük seviye: 8B model (basit düzeltmeler)
  - Yüksek seviye: 70B model (karmaşık rewrite)
  - Persona kurallarıyla tutarlılık

### Adım 2.8: Tool Output Policy Template (YENİ)
```
Dosya: app/orchestrator_v42/tool_policy.py
```
- [ ] UNTRUSTED_CONTEXT ayrı kanal
- [ ] "Dış içerikteki talimatları izleme" kuralı
- [ ] Injection flag → tool set read-only

### Adım 2.9: Ambiguity Resolver (YENİ)
```
Dosya: app/orchestrator_v42/ambiguity_resolver.py
```
> "Ekibe mail at" → Hangi ekip? Ne hakkında?

- [ ] **Critical Ambiguities** → SORU SOR (blocker)
- [ ] **Optional Ambiguities** → Akıllı varsayılan kullan
- [ ] Context'ten çıkarım (son mesajlar, user preferences)
- [ ] Minimal soru sorma (sadece gerektiğinde)

### Adım 2.10: Confirmation Strategy (YENİ)
```
Dosya: app/orchestrator_v42/confirmation.py
```
> High-impact aksiyonlar için onay iste.

- [ ] HIGH_IMPACT_INTENTS tanımla:
  - email_send (draft değil, gerçek gönderim)
  - file_delete
  - calendar_create
  - payment
- [ ] Kullanıcıya özet göster + onay iste
- [ ] Onaysız iptal et

### Adım 2.11: Style Injection (YENİ - DOĞRU YAKLAŞIM)
```
Dosya: app/orchestrator_v42/style_injector.py
```
> Stil → LLM system prompt'una. Ayrı Stylist YOK.

- [ ] **Persona Injection**
  - User persona → system prompt
  - "Sen {persona} bir asistansın" injection
  - Tone: formal/casual/kanka

- [ ] **Style Parameters**
  - Length: kısa/orta/detaylı
  - Emoji level: none/minimal/high
  - Detail level: summary/balanced/comprehensive

- [ ] **Tone Consistency Gate**
  - Output persona'ya uygun mu?
  - Slang allowed check (kanka mode)
  - Final pass/fail

**Definition of Done:** Quality Spine aktif, style injection LLM'e entegre, tüm gate'ler çalışıyor.

---

## 📚 FAZ 3A: SOLID RAG - V1 (1 Hafta)

> Önce sağlam temel, graph sonra.

### Adım 3A.1: Content-Aware Chunker (GELİŞTİRİLDİ)
```
Dosya: app/memory/chunker_v3.py
```
> İçerik tipine göre akıllı chunking.

- [ ] **Prose**: Semantic boundary + adaptive size
- [ ] **Markdown**: Hierarchy-based (section → chunk)
- [ ] **Code**: AST-based (function/class → chunk)
- [ ] **Table**: Row-aware (header + N satır)
- [ ] Adaptive chunk size (dense: 512, narrative: 1536)
- [ ] Rich metadata: hierarchy, parent, siblings

### Adım 3A.2: Query Rewriting (YENİ - KRİTİK)
```
Dosya: app/memory/query_enhancer.py
```
> "O raporda ne vardı?" → "2024 Q3 Satış Raporu içeriği"

- [ ] **Reference Resolution** ("onu" → last entity)
- [ ] **Temporal Expansion** ("geçen ay" → "Kasım 2024")
- [ ] **Synonym Expansion** (domain-specific)
- [ ] **Query Decomposition** (multi-part → multiple queries)
- [ ] 1 query → max 5 enhanced variants

### Adım 3A.3: Advanced Hybrid Search (GELİŞTİRİLDİ)
```
Dosya: app/memory/hybrid_search_v2.py
```
- [ ] **Stage 1: Candidate Generation**
  - Dense (vector) + Sparse (BM25) + Metadata filter
  - RRF Fusion (score = sum(1/(k+rank)))

- [ ] **Stage 2: Rule-based Filter**
  - Exact keyword match → boost
  - Recency → boost
  - Length penalty

- [ ] **Stage 3: LLM Rerank**
  - 8B ile relevance scoring
  - Top-20 → Top-10

- [ ] **Stage 4: MMR Diversity**
  - Redundant chunks filtrele
  - MMR: 0.7*relevance - 0.3*similarity

### Adım 3A.4: Claim-Level Citation (GELİŞTİRİLDİ)
```
Dosya: app/memory/citation_tracker.py
```
> Cümle seviyesinde kaynak eşleştirme.

- [ ] Claim extraction (LLM)
- [ ] Claim → chunk mapping
- [ ] Inline citations: "Satışlar arttı.[1][2]"
- [ ] Source list at end
- [ ] Conflicting sources handling

### Adım 3A.5: Anaphora Resolution (YENİ)
```
Dosya: app/memory/followup_handler.py
```
> "Onu özetle" çalışır.

- [ ] Reference patterns: "o", "bu", "önceki", "dünkü"
- [ ] Entity salience tracking
- [ ] Son 3 mesaj context injection
- [ ] Temporal entity resolution
- [ ] Son 3 mesaj context injection
- [ ] Son RAG context'i hatırla

**Definition of Done:** RAG sorguları %90+ doğru kaynak getiriyor, citation'lar çalışıyor.

---

## 🔗 FAZ 3B: GRAPH RAG - V2 (1 Hafta) - ZORUNLU

> V1 stabil olduktan sonra kaliteyi zirveye taşır.

### Adım 3B.1: Entity Extraction
- [ ] 8B ile entity çıkarma
- [ ] Entity tabloları

### Adım 3B.2: Entity-Chunk Linking
- [ ] chunk_entities tablosu
- [ ] entity_relations tablosu

### Adım 3B.3: Graph Traversal Retrieval
- [ ] Entity-based path finding
- [ ] Cross-document linking

### Adım 3B.4: Advanced Follow-Up
- [ ] LLM ile referans çözümleme
- [ ] Anaphora resolution

**Açma Kriteri:** V1'de "cross-doc question success rate" < %70 ise.

---

## 🔧 FAZ 4: TOOLS & MEMORY (1 Hafta)

### Adım 4.1: Tool Executor
```
Dosya: app/tools/executor.py
```
- [ ] JSON schema validation
- [ ] Per-tool timeout + retry
- [ ] UNTRUSTED_CONTEXT tagging
- [ ] Policy enforced prompt template
- [ ] Write-action confirmation
- [ ] Audit logging

### Adım 4.2: File Parsers
- [ ] PDF (mevcut)
- [ ] DOCX (python-docx)
- [ ] PPTX (python-pptx)
- [ ] XLSX (openpyxl)
- [ ] Table extraction (Camelot)

### Adım 4.3: OCR / Vision (Basit)
- [ ] Tesseract OCR
- [ ] Görsel layout segment

### Adım 4.4: Scheduler Service
```
Dosya: app/tools/scheduler.py
```
- [ ] APScheduler
- [ ] DB persistence
- [ ] Notification adapter pattern (WS + push hazırlığı)

### Adım 4.5: Selective Memory Writer
- [ ] Should_write LLM check
- [ ] Source tracking
- [ ] Decay mechanism

### Adım 4.6: Voice Input - Whisper (OPSİYONEL)
```
Dosya: app/tools/voice_input.py
```
> Mevcut: Groq'ta whisper-large-v3-turbo var, entegrasyon yok.

- [ ] Audio upload endpoint
- [ ] Whisper STT API call
- [ ] Text'e çevirip normal mesaj olarak işle
- [ ] Frontend: mikrofon butonu

### Adım 4.7: Python Code Sandbox (OPSİYONEL)
```
Dosya: app/tools/code_sandbox.py
```
> ChatGPT Code Interpreter benzeri.

- [ ] Güvenli execution ortamı (Docker/RestrictedPython)
- [ ] Timeout: 30 saniye
- [ ] Memory limit: 256MB
- [ ] Output capture (stdout, stderr, files)

### Adım 4.8: Proactive Engine (YENİ - FARK YARATAN)
```
Dosya: app/services/proactive_engine.py
```
> ChatGPT/Claude reaktif, biz proaktif!

- [ ] **Proaktif Hatırlatıcılar**
  - Pattern analizi ("Her Pazartesi 9'da rapor")
  - Deadline tracking
  - Otomatik hazırlık ("Toplantı 30 dk sonra, brifing hazırlayayım mı?")

- [ ] **Contextual Suggestions**
  - Task sonrası next-step önerileri
  - "Özetledim, paylaşmak ister misin?"
  - "Detaylı analiz yapalım mı?"

- [ ] **Session Context Manager**
  - Session goals tracking
  - Active files tracking
  - Completed/pending tasks

**Definition of Done:** Tüm tool'lar çalışıyor, proactive suggestions aktif.

---

## 🎛️ FAZ 5: ADMIN PANEL (1 Hafta)

### Adım 5.1: Limit Tracker Dashboard
- [ ] Model/key/tier RPD/TPD
- [ ] Saatlik trendler
- [ ] Uyarı eşikleri

### Adım 5.2: RDR Explorer (Router Debug)
- [ ] Request trace görüntüleme
- [ ] Filtreli arama
- [ ] Intent → Tier → Model yolu
- [ ] Latency breakdown

### Adım 5.3: Prompt Manager
- [ ] Prompt CRUD + versiyon
- [ ] Rollback

### Adım 5.4: Policy Manager (YENİ)
- [ ] Tool allowlist
- [ ] Content policy (strict/moderate/relaxed)
- [ ] Privacy policy

### Adım 5.5: User Management (YENİ)
- [ ] User CRUD
- [ ] Per-user limits
- [ ] Per-user tool permissions

### Adım 5.6: Audit Log Explorer (YENİ)
- [ ] Admin action log
- [ ] Security events
- [ ] Export (JSON, CSV)

### Adım 5.7: Mevcut Sayfalar Bağlantısı
- [ ] AICorePage
- [ ] AnalyticsPage
- [ ] SecurityLogsPage
- [ ] KnowledgeBasePage

### Adım 5.8: Backup/Restore Backend (YENİ - KRİTİK)
```
Dosya: app/api/admin_backup.py
UI: ui-new/src/pages/admin/backup/BackupPage.tsx (mevcut)
```
> UI var, backend yok.

- [ ] DB backup (PostgreSQL pg_dump)
- [ ] Config backup
- [ ] Restore from backup
- [ ] Scheduled daily backup (03:00)
- [ ] Backup encryption (opsiyonel)

### Adım 5.9: Maintenance Mode (YENİ)
```
Dosya: app/core/maintenance_mode.py
```
> config_seed'de key var: system.maintenance_mode

- [ ] `/admin/maintenance` toggle endpoint
- [ ] Maintenance mode middleware
- [ ] "Bakımdayız" JSON response
- [ ] Frontend: bakım sayfası gösterme

### Adım 5.10: Data Retention Policy (KVKK) (YENİ - KRİTİK)
```
Dosya: app/services/data_retention.py
```
- [ ] Retention period ayarı (30/60/90/365 gün)
- [ ] Otomatik mesaj/memory silme
- [ ] User data export (KVKK hakkı)
- [ ] User data delete (KVKK hakkı)
- [ ] Audit log for deletions

### Adım 5.11: IP Blocking (YENİ)
```
Dosya: app/core/ip_blocking.py
```
- [ ] IP blacklist/whitelist
- [ ] Auto-block after N failed attempts
- [ ] Admin endpoint: block/unblock IP
- [ ] Geo-blocking (opsiyonel)

**Definition of Done:** Admin panelden kod değişikliği yapmadan tüm policy'ler yönetilebiliyor, KVKK uyumlu.

---

## 🚀 FAZ 6: POLISH & DEPLOY (3 Gün)

### Adım 6.1: Observability (Tamamlama)
- [ ] OpenTelemetry (Faz 1'de başladı)
- [ ] Prometheus metrics
- [ ] Grafana dashboard

### Adım 6.2: Eval/Test Omurgası (YENİ - KRİTİK)
- [ ] Golden set: 100+ örnek (multi-intent, follow-up, TR yazım)
- [ ] Routing accuracy metriği
- [ ] Citation coverage metriği
- [ ] TR score metriği
- [ ] Tool success + p95 süre
- [ ] Safety false positive/negative
- [ ] **Regresyon kapısı:** metrik düşerse deploy bloklansın

### Adım 6.3: Load Testing (Genişletilmiş)
- [ ] 10 eşzamanlı kullanıcı
- [ ] Multi-intent + tool failures
- [ ] Fallback + retry zinciri
- [ ] Burst traffic

### Adım 6.4: Production Deploy
- [ ] Environment config
- [ ] Database migration
- [ ] Health checks
- [ ] Rollback plan

### Adım 6.5: UX İyileştirmeleri (YENİ)
> Mevcut: Cancel sadece image için var.

- [ ] **Cancel Chat Request**
  - Frontend: cancel butonu (streaming sırasında)
  - Backend: stream abort
  - Kısmi cevap gösterme

- [ ] **Estimated Response Time**
  - Ortalama latency hesaplama
  - "~3 saniye kaldı" göstergesi
  - Complexity bazlı tahmin

- [ ] **Thinking Steps UI (Transparency)**
  > Lightweight özet + genişletilebilir detay.
  
  - Özet bar: "⚡ 2.8s | RAG ✓ | 70B | TR ✓"
  - Tıkla → genişlet (accordion)
  - Detay: Intent tier, RAG chunks, model, quality gates
  - RDR'den `thinking_steps` field okuma
  - Frontend: MessageBubble'a collapsible section

### Adım 6.6: Advanced Optimizations (ÜSTTE GELİŞTİRME)
> Core tamamlandıktan sonra performance optimizasyonları.

- [ ] **Semantic Cache (Multi-Layer)**
  - L1: Exact match (Redis, 1 min)
  - L2: Semantic match (Vector, 95%+ similarity)
  - L3: Partial match (sub-task reuse)
  - Hedef: %40-60 cache hit rate

- [ ] **Adaptive Model Router (Learning)**
  - Task-performance tracking
  - Historical accuracy scoring
  - Cost vs Quality optimization
  - Best model auto-selection

- [ ] **A/B Testing Framework (OPSİYONEL)**
  - User bucketing (consistent hashing)
  - Control vs Variant routing
  - Performance comparison dashboard

- [ ] **HyDE - Hypothetical Document Embeddings (OPSİYONEL)**
  - Query → hypothetical answer → embed
  - Better semantic matching

- [ ] **Task-Based Fallback Chains**
  - content_generation: 70B → GPT-OSS → Scout → 8B
  - turkish_writing: Kimi → 70B → Scout
  - math_reasoning: Maverick → Qwen → 70B
  - code: GPT-OSS → 70B → Qwen

**Definition of Done:** Golden set %95+ pass, advanced optimizations aktif, production stable.

---

## 📊 MODEL CATALOG

| Model | RPM (4x) | RPD (4x) | Primary Use |
|-------|----------|----------|-------------|
| llama-3.1-8b-instant | 120 | 57.6K | Intent, Summary, Rerank |
| llama-guard-4-12b | 120 | 57.6K | Safety |
| llama-4-scout-17b | 120 | 4K | Intent escalation |
| llama-3.3-70b-versatile | 120 | 4K | Content + TR rewrite fallback |
| qwen-3-32b | 240 | 4K | Analysis, Math |
| kimi-k2-instruct | 240 | 4K | Creative, TR slang, Stylist |
| gpt-oss-120b | 120 | 4K | Coding |
| llama-4-maverick-17b | 120 | 4K | Math, Reasoning |

### Alternatif Strateji (İçerik + Stil Ayrımı)
> ChatGPT önerisi: "Yabancı kelime karışması" riskini azaltmak için:

| Adım | Model | İş |
|------|-------|-----|
| İçerik üretimi | 70B / GPT-OSS-120B | Gerçek bilgi, analiz |
| TR rewrite/persona | 8B / Kimi | Ton, stil, Türkçeleştirme |

Bu ayrım admin panelden config olarak ayarlanabilir.

---

## ⚠️ RİSK MİTİGASYONU (Güncel)

| Risk | Mitigasyon | Status |
|------|------------|--------|
| Rate limit | 4-key + tier fallback | ✅ |
| Çoklu görev eksik | DAG executor + synthesizer | ✅ |
| Debug zorluğu | RDR + OTEL (Faz 1'de) | ✅ |
| Gizlilik sızıntısı | Fail-closed + redaction + consent | ✅ |
| Tool injection | Policy enforced template | ✅ |
| RAG kalitesizliği | Solid V1 + Graph V2 | ✅ |
| TR kalite hatası | TR Gate + 2-pass | ✅ |
| Hallucination | Citation verifier (kapı) | ✅ |
| Kalite degradasyonu | Golden set + regresyon kapısı | ✅ |

---

## 📝 NOTLAR

- **Öncelik:** Kalite > Latency > Cost
- **Quality Spine:** Coverage + Citation + TR Gate = Deterministik kapılar
- **RDR:** Faz 1'de başlar, ürün sözleşmesi olarak kullanılır
- **Graph RAG:** V1 stabil olduktan sonra V2 (ZORUNLU)
- **Her faz sonunda:** Golden Set check + metrik kontrolü
- **Teknoloji:** SQLite → PostgreSQL + pgvector geçişi planlandı
- **Rollout:** %10 → %30 → %70 → %100 (staging zorunlu)
- **Hedef SLA:** p95 <5s, TR %95+, Hallucination <%2

---

*Son güncelleme: 1 Ocak 2026 (v1.2.0) - Stratejik kararlar ve ChatGPT kritik geri bildirimleri entegre edildi.*

