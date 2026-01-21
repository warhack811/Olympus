# Mami AI Sovereign Brain Engine (v4.4) - Router Akış Analizi

Bu doküman, bir kullanıcı mesajının sistemdeki yolculuğunu ve bu süreçte görev alan yapay zeka modellerini teknik kanıtlarıyla açıklar.

## 1. Mesaj Akış Hiyerarşisi

### A. Giriş Katmanı (API Entry)
Mesaj sisteme `app/api/routes/chat.py` üzerinden girer.
- **Streaming:** `atlas_chat_stream` fonksiyonu `brain_engine.process_request_stream` jeneratörünü başlatır.
- **Non-Streaming:** `chat` fonksiyonu `brain_engine.process_request` metotunu çağırır.
- **Kanıt:** [chat.py:L33-59](file:///d:/ai/mami_ai_v4/app/api/routes/chat.py#L33-L59)

### B. Hidrasyon Katmanı (Memory Retrieval)
`BrainEngine` yanıta başlamadan önce bağlamı hazırlar:
1.  **Prospective Memory:** Neo4j üzerinden zamanı gelmiş hatırlatıcılar taranır. [engine.py:L368](file:///d:/ai/mami_ai_v4/app/services/brain/engine.py#L368)
2.  **Semantic Memory (Vektör):** Qdrant üzerinde anlamsal arama yapılır.
    - **Model:** `text-embedding-004` (Gemini). [constants.py:L103](file:///d:/ai/mami_ai_v4/app/core/constants.py#L103)
3.  **Logical Memory (Graf):** Neo4j üzerinden kullanıcıya ait ilişkisel "Gerçekler" (Facts) çekilir. [engine.py:L109](file:///d:/ai/mami_ai_v4/app/services/brain/engine.py#L109)
4.  **Hot Memory (History):** Redis (`session:{id}:history`) veya SQL üzerinden son mesajlar çekilir. [engine.py:L190-204](file:///d:/ai/mami_ai_v4/app/services/brain/engine.py#L190-204)

### C. Orkestrasyon Katmanı (Planning)
`IntentManager` mesajın ne yapılacağına dair bir **OrchestrationPlan** (DAG) hazırlar:
- **Tier 1 (Regex):** Hızlı aksiyonlar (resim çiz, ara) LLM'e gitmeden yakalanır. [intent.py:L62-103](file:///d:/ai/mami_ai_v4/app/services/brain/intent.py#L62-103)
- **Tier 3 (LLM Planner):** Karmaşık sorgular için LLM'den bir işlem planı istenir.
- **Modeller:** Öncelikle `gemini-2.0-flash`, yedek olarak `llama-3.3-70b-versatile`. [constants.py:L48-49](file:///d:/ai/mami_ai_v4/app/core/constants.py#L48-49)

### D. Yürütme Katmanı (Task Execution)
`TaskRunner` plandaki görevleri paralel/ardışık çalıştırır:
- **Araçlar:** Google Search veya Flux tetiklenir. [task_runner.py:L331-342](file:///d:/ai/mami_ai_v4/app/services/brain/task_runner.py#L331-342)
- **Uzmanlar (Specialists):**
    - **Kodlama:** `qwen/qwen3-32b` veya `llama-3.3-70b-versatile`. [constants.py:L56-59](file:///d:/ai/mami_ai_v4/app/core/constants.py#L56-L59)
    - **Mantık/Genel:** `llama-3.3-70b-versatile`. [constants.py:L64-67](file:///d:/ai/mami_ai_v4/app/core/constants.py#L64-L67)

### E. Sentez ve Persona Katmanı (Synthesis)
`Synthesizer` uzman çıktılarını ve hafıza bağlamını son yanıta dönüştürür:
- **Vocalizer:** Persona (Karakter) ve stil direktiflerini (Mirroring, Memory Voice) uygular. [vocalizer.py:L20-72](file:///d:/ai/mami_ai_v4/app/services/brain/vocalizer.py#L20-72)
- **Modeller:** Öncelikle `moonshotai/kimi-k2-instruct`, yedek olarak `llama-3.3-70b-versatile`. [constants.py:L72-75](file:///d:/ai/mami_ai_v4/app/core/constants.py#L72-75)

### F. Arka Plan Katmanı (Learning)
Yanıt ulaştırılırken arka planda mesajdan bilgi ayıklanır:
- **Model:** `llama-3.3-70b-versatile` (0.1 Temperature). [engine.py:L537-541](file:///d:/ai/mami_ai_v4/app/services/brain/engine.py#L537-541)

---

## 2. Model Yönetişim Matrisi (Sovereign Governance)

| Görev | Birincil Model | Sağlayıcı | Kanıt |
| :--- | :--- | :--- | :--- |
| **Gömme (Embedding)** | `text-embedding-004` | Gemini | `constants.py:L103` |
| **Planlama (Orchestrator)** | `gemini-2.0-flash` | Gemini | `constants.py:L48` |
| **Kodlama (Coding)** | `qwen/qwen3-32b` | Groq | `constants.py:L58` |
| **Mantık (Logic)** | `llama-3.3-70b-versatile` | Groq | `constants.py:L65` |
| **Sentez/Persona** | `kimi-k2-instruct` | Moonshot | `constants.py:L73` |
| **Bilgi Çıkarımı (Learning)** | `llama-3.3-70b-versatile` | Groq | `engine.py:L537` |
