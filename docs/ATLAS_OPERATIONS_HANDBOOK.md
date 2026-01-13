# 🛡️ ATLAS OPERATIONS HANDBOOK

**Versiyon:** 1.0.0  
**Tarih:** 1 Ocak 2026  
**Hedef:** Production sistemin stabil ve güvenli çalışması

> Bu doküman `ATLAS_CORE_IMPLEMENTATION_PLAN.md`'nin operasyonel tamamlayıcısıdır.

---

## 📋 İÇİNDEKİLER

1. [Hata Toleransı](#-1-hata-toleransı)
2. [Validation Pipeline](#-2-validation-pipeline)
3. [Test Stratejisi](#-3-test-stratejisi)
4. [Observability](#-4-observability)
5. [Güvenlik](#-5-güvenlik)
6. [Veri Kalitesi](#-6-veri-kalitesi)
7. [Operasyonel Prosedürler](#-7-operasyonel-prosedürler)

---

## 🔄 1. HATA TOLERANSI

### 1.1 Circuit Breaker v2 State Machine

```
┌─────────┐  success ┌────────────┐
│ CLOSED  │◄────────│ HALF_OPEN  │
└────┬────┘         └─────┬──────┘
     │                    │
     │ fail               │ fail
     ▼                    │
┌────────┐  timeout       │
│  OPEN  │───────────────►┘
└────────┘
```

**State Transition Rules:**

| From | To | Condition |
|------|----|-----------|
| CLOSED | OPEN | %10 fail (son 100 req) VEYA 3 ardışık timeout |
| OPEN | HALF_OPEN | Exponential backoff: 30s → 60s → 120s → 300s |
| HALF_OPEN | CLOSED | 10 test request hepsi başarılı |
| HALF_OPEN | OPEN | 1 fail |

**Per-Component Breakers:**
- Groq API (model bazlı: 70B, Scout, 8B ayrı)
- PostgreSQL
- Redis  
- pgvector search
- Web search (Brave, Perplexity)
- Her tool (Gmail, Calendar, etc.)

### 1.2 Graceful Degradation Matrix

| Bileşen Fail | Fallback | Kalite Kaybı | User Notification |
|--------------|----------|--------------|-------------------|
| RAG Fail | LLM-only mode | Citation yok | "Kaynaklara ulaşamadım, genel bilgi veriyorum" |
| Citation Verifier Fail | Skip verifier | Güven azalır | [Doğrulanmadı] etiketi |
| TR Gate Fail | Basic regex only | Kalite %10 düşer | Silent (log only) |
| Tool Timeout | Continue without | Eksik bilgi | "X aracına ulaşamadım" |
| Redis Fail | DB-backed session | 2x latency | Silent |
| pgvector Fail | BM25 keyword only | Semantic yok | Silent |
| All Models Fail | Maintenance mode | %100 | "Bakımdayız" sayfası |

**Öncelikler:**
1. User experience bozulmasın (partial response > no response)
2. Data consistency korunsun (write fail → rollback)
3. Açık iletişim (ne çalışmıyor söyle)

---

## ✅ 2. VALIDATION PIPELINE

### 2.1 Input Validation (5 Kademe)

```
Request → Kademe 1 → Kademe 2 → Kademe 3 → Kademe 4 → Kademe 5 → Process
           (0ms)      (10ms)     (50ms)     (100ms)    (200ms)
```

**Kademe 1: Schema Validation (0ms)**
- JSON structure check
- Required fields
- Data types
- Field lengths

**Kademe 2: Semantic Validation (10ms)**
- Date logic ("2023-13-01" invalid)
- Email format
- Phone format (TR: +90 5XX XXX XX XX)
- URL validation

**Kademe 3: Business Rule Validation (50ms)**
- User quota check
- Permission check
- Rate limit check
- Content policy pre-filter

**Kademe 4: Security Validation (100ms)**
- SQL injection patterns
- XSS patterns
- Path traversal
- Command injection
- Prompt injection detection

**Kademe 5: Contextual Validation (200ms)**
- Ambiguity detection ("Dosyayı sil" → hangi dosya?)
- Missing context ("Ekibe mail at" → hangi ekip?)
- High-impact action confirmation needed?

**Fail Response Example:**
```
Input: "2023-13-45 tarihinde toplantı"
Fail: Kademe 2 (Semantic Validation)
Response: 
"⚠️ Tarih formatı hatalı: '2023-13-45'
Ay 1-12 arası olmalı. Şunu mu demek istediniz?
- 2023-12-31 (Aralık ayı son günü)
- 2024-01-15 (Yeni yıl)"
```

### 2.2 Output Quality Gates (5 Kapı)

**Gate 1: Coverage Check**
- Her task cevaplandı mı?
- Partial task detection ("3/5 task completed")
- Task dependency check

**Gate 2: Groundedness Check**
- Citation matching
- Hallucination detection (NLI model)
- Named entity verification
- Numerical consistency
- Low confidence → "Emin değilim" + kaynak göster

**Gate 3: Tool Safety Check**
- Injection detection
- Tool output sanitization
- PII redaction from tool responses
- Side-effect analysis ("write yapacak → user approval")

**Gate 4: TR Quality Gate**
- Yasak kalıp check
- Yabancı kelime oranı < %5
- Semantic coherence (cümle bağlantıları)
- Readability score (Grade 8-10 hedef)

**Gate 5: Consistency Check**
- Internal contradiction detection
- Multi-turn consistency
- Persona adherence

**Fail Action:** Auto-rewrite (max 2 attempt) → sonra "düzeltemedim" itirafı

---

## 🧪 3. TEST STRATEJİSİ

### 3.1 Test Piramidi

```
            ▲ E2E (5%) - 50 test
           / \
          /   \
         / Int \ (25%) - 500 test
        /_______\
       /         \
      /   Unit    \ (70%) - 2000+ test
     /_______________\
```

**Coverage Target:** %85+

### 3.2 Differential Testing

| Test Tipi | Açıklama | Ne Zaman |
|-----------|----------|----------|
| Golden Set Regression | 100+ test case, pass < %95 → blocker | Her deploy |
| Shadow Mode Testing | %10 traffic yeni versiyona, karşılaştır | Major changes |
| A/B Diff Testing | Aynı query, eski vs yeni model | Model updates |
| Adversarial Testing | 100+ prompt injection, edge cases | Weekly |

### 3.3 Chaos Engineering (Haftalık)

**Senaryolar:**
1. **Dependency Failure:** PostgreSQL 5s down, Redis flush, Groq 429
2. **Load Spikes:** 10x traffic, slow client
3. **Data Corruption:** Malformed JSON, invalid UTF-8
4. **Resource Exhaustion:** Memory leak, disk full, CPU 100%
5. **Time Issues:** Clock skew, timezone, DST
6. **Security Attacks:** SQL injection, prompt injection, DDoS

**Schedule:** Cumartesi 03:00 (automated)

### 3.4 Canary Deployment v2

```
Stage 0: Pre-Production (1 user, 24h)
    ↓ Manual QA pass
Stage 1: Canary %5 (24h)
    ↓ Error rate < %1
Stage 2: Canary %15 (48h)
    ↓ Cost/latency stable
Stage 3: Canary %50 (72h)
    ↓ Golden Set pass
Stage 4: Full Rollout %100
    ↓ Old version standby (1 week)
```

**Auto-Rollback Triggers:**
- Error rate > %2 (baseline'dan)
- p95 latency > 10s
- Golden set pass rate < %90
- User complaints > 5 (1 saatte)
- Cost spike > %50

---

## 📊 4. OBSERVABILITY

### 4.1 Distributed Tracing (OTEL)

```
request_id: uuid_123
├─ [0ms] API Gateway
│   └─ rate_limit_check: 5ms
├─ [10ms] Intent Classifier
│   ├─ tier_0_rules: 0ms (CACHED)
│   ├─ tier_1_8b: 200ms
│   └─ confidence: 0.92
├─ [210ms] DAG Executor
│   ├─ task_1: search (450ms)
│   └─ task_2: generate (3200ms)
├─ [3660ms] Quality Spine
│   ├─ coverage_check: PASS
│   ├─ citation_check: PASS
│   └─ tr_gate: REWRITE_NEEDED
└─ [4800ms] Response Sent

Breakdown: Intent=5%, RAG=10%, LLM=70%, Quality=15%
```

### 4.2 Alerting (3 Tier)

**🔴 P0 - Critical (5 dk müdahale)**
- API down (3 consecutive health fail)
- Database connection lost
- All models failing
- Error rate > %5
- Data loss detected

**🟡 P1 - High (30 dk)**
- p95 latency > 10s
- Rate limit hit > %10
- Golden set < %90
- Cost spike > %100
- Disk usage > %80

**🟢 P2 - Medium (2 saat)**
- Cache hit rate < %40
- Tool failure > %5
- Quality gate rewrite > %20
- User feedback < 4.0/5

**Alert Channels:**
- P0: PagerDuty + SMS
- P1: Slack #atlas-alerts
- P2: Email

### 4.3 Dashboards

**1. Executive Dashboard**
- SLA compliance, User satisfaction, Cost per message, Active users

**2. Engineering Dashboard**
- p50/p95/p99 latency, Error rates, Model success, Circuit states

**3. Quality Dashboard**
- TR quality score, Hallucination rate, Citation coverage, Gate pass rates

**4. Cost Optimization Dashboard**
- Cost by model/intent, Cache savings, Optimization opportunities

### 4.4 Log Aggregation (ELK)

```json
{
  "timestamp": "2026-01-01T09:15:23.123Z",
  "request_id": "uuid_123",
  "level": "ERROR",
  "component": "citation_verifier",
  "user_id": "user_456",
  "message": "Citation source not found",
  "metadata": {...}
}
```

**Retention:**
- DEBUG: 7 gün
- INFO: 30 gün
- ERROR: 1 yıl
- RDR: 1 yıl (KVKK)

---

## 🔒 5. GÜVENLİK

### 5.1 Defense in Depth (7 Katman)

1. **Network:** WAF + DDoS (Cloudflare)
2. **API Gateway:** Rate limiting + JWT
3. **Input Validation:** 5 kademe
4. **Business Logic:** RBAC
5. **Data Access:** PostgreSQL RLS
6. **Output Sanitization:** XSS, PII redaction
7. **Monitoring:** Anomaly + intrusion detection

### 5.2 Secret Management

❌ **Yapma:**
- .env'de API key
- Hardcoded secret
- Git'te credential

✅ **Yap:**
- HashiCorp Vault / AWS Secrets Manager
- Runtime injection
- 30 gün rotation
- Encrypt at rest + in transit

### 5.3 KVKK/GDPR User Rights

| Hak | Endpoint | SLA |
|-----|----------|-----|
| Access | /api/user/data-export | 24 saat |
| Erasure | /api/user/data-delete | 30 gün grace |
| Rectification | /api/user/data-update | Instant |
| Portability | JSON export | 24 saat |
| Object | AI opt-out | Instant |

### 5.4 Vulnerability Management

**Automated (Günlük):**
- Snyk: Dependency CVEs
- Trivy: Container scan
- TruffleHog: Secret scan
- Bandit: SAST

**Manual:**
- Quarterly pen test
- Yearly red team

**Patch SLA:**
- Critical: 24 saat
- High: 7 gün
- Medium: 30 gün

---

## 📈 6. VERİ KALİTESİ

### 6.1 Ingestion Validation

**Stage 1:** Format (PDF, DOCX, 50MB max)
**Stage 2:** Quality (readability, language)
**Stage 3:** Metadata (title, author, entities)
**Stage 4:** Semantic (topic, relevance score)

### 6.2 Data Lineage

Her response için "nereden geldi?" tracking:
```
response: "2.4M TL"
├─ source: "Q3-Sales-Report.pdf"
│   ├─ page: 3
│   └─ chunk_id: "chunk_789"
├─ calculation: "LLM reasoning"
└─ verification: "Cross-checked"
```

### 6.3 Drift Detection

**Monitor:**
- Input patterns (query length, intent distribution)
- Output trends (response length, citation rate)
- Concept drift (intent meaning changes)

**Action:** Alert → retrain/prompt update

---

## 📋 7. OPERASYONEL PROSEDÜRLER

### 7.1 Runbook: Sistem Çöktü (P0)

1. Health check endpoint test
2. PostgreSQL bağlantı kontrol
3. Redis ping
4. Groq API health check
5. Son 5 dk log incele
6. Recent deployment? → Rollback
7. Traffic spike? → Scale up
8. External fail? → Activate backup
9. Çözülmedi? → War room

### 7.2 Runbook: Yavaş Yanıtlar (P1)

1. Grafana dashboard aç
2. Hangi component yavaş? (trace)
3. DB slow query? → Index
4. Model timeout? → Fallback aktif mi?
5. Cache hit düşük? → Warm-up
6. Scale horizontally

### 7.3 Runbook: Maliyet Patladı (P1)

1. Cost dashboard aç
2. Hangi model pahalı?
3. Kullanıcı bazlı rate limit
4. Unnecessary tool calls fix
5. Cache optimization
6. Model downgrade

### 7.4 Postmortem Template

```markdown
## Incident Summary
- Ne oldu?
- Etkilenen user sayısı
- Business impact

## Root Cause (5 Why's)
Neden 1 → Neden 2 → ... → Kök neden

## Timeline
- T+0: Incident başladı
- T+5: Alert geldi
- T+45: Mitigation
- T+120: Resolution

## What Went Well / Wrong

## Action Items
- [ ] Fix X (owner, due date)
```

### 7.5 Disaster Recovery

**RTO:** 1 saat  
**RPO:** 15 dakika

**Backup Strategy:**
- PostgreSQL: WAL + daily full (30 gün retention)
- Redis: RDB + AOF (7 gün)
- Files: S3 versioning (90 gün)

**DR Scenarios:**
| Senaryo | Strategy | RTO |
|---------|----------|-----|
| Data Center Loss | Secondary region failover | 30 dk |
| DB Corruption | Point-in-time recovery | 45 dk |
| Ransomware | Immutable backup restore | 2 saat |

**DR Drill:** 6 ayda bir

### 7.6 Capacity Planning (Aylık)

**Monitor:**
- Current: users, messages/day, latency, CPU, memory, cost
- Growth projection (6 ay)
- Bottleneck analysis

**Scale Actions:**
- Month 2: PostgreSQL read replica
- Month 3: Add Groq keys
- Month 4: Redis cluster
- Month 5: Horizontal API scaling

---

## 📊 ÖZET: CHECKLIST

| Kategori | Önlemler | Hedef Metrik |
|----------|----------|--------------|
| Mimari | Circuit Breaker v2, Degradation Matrix | Error < %0.5 |
| Validation | 5-kademe input, 5-kapı output | Bad request < %0.1 |
| Testing | Chaos, Property-based, Regression | Regression < %1 |
| Observability | OTEL tracing, 3-tier alerts | MTTR < 15 dk |
| Güvenlik | 7-layer defense, vault, pen test | Zero breach |
| Veri | Lineage, drift detection | Hallucination < %1 |
| Operasyon | Runbooks, DR, capacity | RTO < 1 saat |

---

*Son güncelleme: 1 Ocak 2026*
