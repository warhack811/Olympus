# ATLAS Router - Web Search Mimarisi

> **Versiyon:** 1.0  
> **Tarih:** 2026-01-03  
> **Durum:** Onaylandı - Implementasyon bekliyor

---

## Genel Bakış

Bu belge, ATLAS Router'ın web search ve tool kullanım mimarisini tanımlar. Tasarım; Perplexity AI, ChatGPT Browse ve modern RAG sistemlerinden ilham alarak oluşturulmuştur.

### Hedefler
- Kullanıcı sorularına doğru ve güncel bilgi sağlamak
- Minimum LLM çağrısı ile maksimum kalite
- Serper API maliyetini optimize etmek
- Uzun vadede bakım gerektirmeyen sağlam altyapı

---

## Mimari Akış

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                              │
│                    "Bugün dolar kaç?"                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      1. ORCHESTRATOR                            │
│                                                                 │
│  Girdiler:                                                      │
│  - User message                                                 │
│  - Available tools: [web_search, currency_api, weather_api]    │
│                                                                 │
│  Çıktılar:                                                      │
│  - intent: "search"                                             │
│  - tool: "currency_api" veya "web_search"                      │
│  - complexity: "simple" | "medium" | "complex"                 │
│  - search_queries: ["USD TRY kur", "dolar TL bugün"] (1-5)     │
│  - freshness: "hour" | "day" | "week" | "none"                 │
│                                                                 │
│  Model: Gemini 2.0 Flash                                        │
│  LLM Çağrısı: 1                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     2. TOOL ROUTING                             │
│                                                                 │
│  Kural Tabanlı Routing:                                         │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ currency_api│  │ weather_api │  │ web_search  │              │
│  │             │  │             │  │             │              │
│  │ Döviz kuru  │  │ Hava durumu │  │ Genel arama │              │
│  │ Kripto      │  │ Sıcaklık    │  │ Haberler    │              │
│  │             │  │             │  │ Analiz      │              │
│  │ Cache: 1dk  │  │ Cache: 30dk │  │ Cache: 1h   │              │
│  │ Fallback:   │  │ Fallback:   │  │             │              │
│  │ web_search  │  │ web_search  │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                 │
│  LLM Çağrısı: 0 (kural tabanlı)                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    3. WEB SEARCH TOOL                           │
│                                                                 │
│  3.1 Cache Kontrolü                                             │
│  ├── Key: hash(sorted(queries))                                 │
│  ├── TTL: Döviz=1dk, Hava=30dk, Genel=1h                       │
│  └── Hit → Direkt sonuç dön                                     │
│                                                                 │
│  3.2 Rate Limit Kontrolü                                        │
│  ├── Günlük max: 1500 sorgu (Serper %90)                        │
│  └── Aşılırsa → Hata dön                                        │
│                                                                 │
│  3.3 Parallel Query Execution                                   │
│  ├── Complexity: simple → 1-2 query                            │
│  ├── Complexity: medium → 2-3 query                            │
│  ├── Complexity: complex → 3-5 query                           │
│  └── Serper API: tbs parametresi ile freshness                 │
│                                                                 │
│  3.4 Result Processing                                          │
│  ├── Blacklist filtering (spam/reklam siteleri)                │
│  ├── Reciprocal Rank Fusion (RRF) algoritması                  │
│  └── Top 5-7 sonuç seçimi                                       │
│                                                                 │
│  LLM Çağrısı: 0                                                 │
│  Serper Çağrısı: 1-5 (complexity'ye göre)                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     4. SYNTHESIZER                              │
│                                                                 │
│  Girdiler:                                                      │
│  - Original user query                                          │
│  - Tool results (top 5-7 sources)                              │
│  - Freshness indicator                                          │
│                                                                 │
│  Çıktılar:                                                      │
│  - Kaynak bazlı özet yanıt                                      │
│  - Citation format: [1], [2], etc.                             │
│  - Freshness prefix: "3 Ocak 2025 verilerine göre..."          │
│                                                                 │
│  Model: Kimi-k2 veya Llama-70B                                  │
│  LLM Çağrısı: 1                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FINAL RESPONSE                             │
│                                                                 │
│  "3 Ocak 2025 verilerine göre 1 USD = 35.18 TL [1].            │
│   Gün içinde 35.22'ye kadar yükseldi [2]."                      │
│                                                                 │
│  Kaynaklar:                                                     │
│  [1] TCMB - tcmb.gov.tr                                         │
│  [2] Bloomberg - bloomberg.com                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Özellik Detayları

### 1. Adaptive Query Expansion

Orchestrator, sorunun karmaşıklığına göre kaç arama sorgusu üreteceğine karar verir:

| Karmaşıklık | Örnek Soru | Query Sayısı |
|-------------|------------|--------------|
| **Simple** | "Dolar kaç?" | 1-2 |
| **Medium** | "Türkiye enflasyonu son 3 ay" | 2-3 |
| **Complex** | "ABD faiz kararının altına etkisi" | 3-5 |

### 2. Freshness Filter

Serper API `tbs` parametresi ile:

| Değer | Anlam | Kullanım |
|-------|-------|----------|
| `qdr:h` | Son 1 saat | Anlık haberler |
| `qdr:d` | Son 24 saat | Döviz, hava |
| `qdr:w` | Son 1 hafta | Güncel konular |
| (yok) | Tüm zamanlar | Evergreen bilgi |

**Fallback:** Sonuç yetersizse otomatik genişlet (hour → day → week)

### 3. Reciprocal Rank Fusion (RRF)

Birden fazla sorgu sonucunu akıllıca birleştirir:

```python
def reciprocal_rank_fusion(results_per_query, k=60):
    scores = {}
    for results in results_per_query:
        for rank, doc in enumerate(results):
            url = doc['url']
            scores[url] = scores.get(url, 0) + 1 / (rank + k)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Avantaj:** Aynı URL birden fazla sorguda çıkıyorsa skoru artar → daha alakalı.

### 4. Kaynak Blacklist

Kalitesiz kaynakleri filtrele:

```python
BLACKLIST_DOMAINS = [
    "pinterest.com",
    "quora.com", 
    "facebook.com",
    "twitter.com",
    "instagram.com",
    # + spam/reklam siteleri
]
```

### 5. Specialized API'ler

Spesifik veriler için dedicated API'ler:

| Veri Türü | API | Ücretsiz Limit |
|-----------|-----|----------------|
| Döviz | ExchangeRate-API | 1500/ay |
| Hava Durumu | OpenWeatherMap | 1000/gün |
| Kripto | CoinGecko | Unlimited |

**Fallback:** API down → web_search'e düş

---

## Maliyet Özeti

| Senaryo | LLM Çağrısı | Serper | Maliyet |
|---------|-------------|--------|---------|
| Web search (basit) | 2 | 1-2 | ~$0.003 |
| Web search (kompleks) | 2 | 3-5 | ~$0.006 |
| Currency API | 2 | 0 | ~$0.001 |
| Weather API | 2 | 0 | ~$0.001 |

**Günlük tahmini maliyet:** 10 müşteri × 25 sorgu × $0.004 = **~$1/gün**

---

## Implementasyon Sırası

| # | İş | Dosya | Öncelik |
|---|---|-------|---------|
| 1 | Tool Registry oluştur | `tool_registry.py` | 🔴 Yüksek |
| 2 | Web Search Tool | `tools/web_search.py` | 🔴 Yüksek |
| 3 | Currency API Tool | `tools/currency_api.py` | 🔴 Yüksek |
| 4 | Weather API Tool | `tools/weather_api.py` | 🟡 Orta |
| 5 | TaskSpec entegrasyonu | `dag_executor.py` | 🔴 Yüksek |
| 6 | Orchestrator güncellemesi | `orchestrator.py` | 🔴 Yüksek |
| 7 | Synthesizer citation format | `synthesizer.py` | 🟡 Orta |

---

## Referanslar

- Perplexity AI: RAG + Hybrid Search + Multi-stage Reranking
- ChatGPT Browse: Tool fonksiyonları + recency_days
- LangChain: Agent patterns + production best practices
- RAG Architecture: Query expansion + RRF + Cross-encoder

---

## Onay

| İsim | Rol | Tarih | Onay |
|------|-----|-------|------|
| [Kullanıcı] | Proje Sahibi | 2026-01-03 | Bekliyor |
