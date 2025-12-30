# Groq Model Analiz ve Entegrasyon Raporu

**Tarih:** 23 Aralık 2025  
**Konu:** Llama 4, Qwen 3, Kimi k2 ve Diğer Groq Modellerinin İncelemesi  
**Durum:** `Preview` ve `Production` Modelleri

Bu rapor, Groq platformunda listelenen belirli AI modellerinin teknik özelliklerini, kullanım amaçlarını ve **Mami AI** projesine entegrasyon potansiyellerini detaylandırmaktadır.

---

## 📋 Yönetici Özeti

İncelenen liste, özellikle **Llama 4 (Preview)**, **Qwen 3** ve **Kimi k2** gibi çok yeni ve güçlü modelleri içermektedir. Bu modeller, mevcut `1upgrade_plan.md` içerisindeki hedeflerle (özellikle Reasoning, Coding ve Multimodal kapasite) doğrudan örtüşmektedir.

| Model Ailesi | Öne Çıkan Özellik | Projedeki Olası Rolü | Durum |
| :--- | :--- | :--- | :--- |
| **Llama 4 (Maverick/Scout)** | Multimodal (Resim+Metin), MoE Mimarisi | Vision analizi, Genel sohbet | 🚧 Preview |
| **Qwen 3** | Üstün Mantık (Reasoning) ve Matematik | Kodlama, Karmaşık mantık soruları | 🚧 Preview |
| **Kimi k2** | 1 Trilyon Parametre + 256K Context | Uzun belge analizi (RAG Deep), Ajan (Agent) işleri | 🚧 Preview |
| **Llama Guard 4** | Multimodal Güvenlik | Görsel ve metin moderasyonu (Sansür/Güvenlik) | ✅ Production |
| **Whisper V3 Turbo** | Aşırı Hızlı STT (216x) | Gerçek zamanlı sesli asistan (Faz 6) | ✅ Production |

---

## 1. Model Analizleri

### 🤖 Generative & Reasoning Modelleri

#### 1.1. Moonshot AI - Kimi k2 (Instruct & 0905)
*   **Model:** `moonshotai/kimi-k2-instruct-0905`
*   **Boyut:** ~1 Trilyon Parametre (MoE - Mixture of Experts)
*   **Context Window:** **256,000 Token** (Çok Geniş)
*   **Kullanım Amacı:** Uzun bağlam gerektiren analizler, kodlama, karmaşık ajan görevleri.
*   **Güçlü Yönleri:** 
    *   Scoding (Kodlama) başarısı (LiveCodeBench: %53.7).
    *   Çok uzun belgeleri (kitap, tüm kod tabanı) hafızada tutabilme.
    *   MoE yapısı sayesinde devasa boyutuna rağmen hızlı çıkarım.
*   **Proje Kullanımı:** 
    *   **Uzun Belge RAG:** `docs/1upgrade_plan.md` içinde belirtilen "Page-aware PDF ingestion" sonrası, kitabın tamamını context'e atıp soru sormak için ideal.
    *   **Kod Asistanı:** Projede kod yazma görevleri için DeepSeek alternatifi olabilir.

#### 1.2. Qwen 3 (32B)
*   **Model:** `qwen/qwen3-32b`
*   **Boyut:** 32 Milyar Parametre
*   **Context Window:** 128,000 Token
*   **Kullanım Amacı:** Matematik, Mantık Yürütme (Reasoning), ve Bilimsel problemler.
*   **Güçlü Yönleri:**
    *   **Reasoning:** "Thinking Mode" desteği ile adım adım düşünerek cevap verir.
    *   **Performans:** ArenaHard testinde %93.8 gibi olağanüstü bir skor (GPT-4 seviyesi rakiplerle yarışır).
*   **Proje Kullanımı:**
    *   **Logic Router:** `smart_router.py` güncellenerek matematik, fizik veya mantık soruları (`domain="math"`) bu modele yönlendirilmeli.
    *   **Mevcut Plan:** Upgrade planındaki "Reasoning (qwen-32b)" maddesi için en güncel ve doğru aday budur.

#### 1.3. Llama 4 (Maverick & Scout) - **PREVIEW**
Meta'nın henüz tam lansmanını yapmadığı (veya Groq'a özel/erken erişim) yeni nesil model ailesi.
*   **Varyasyonlar:**
    *   `meta-llama/llama-4-maverick-17b-128e-instruct`: 17B parametre, **128 Expert** (MoE). Daha yüksek kapasite.
    *   `meta-llama/llama-4-scout-17b-16e-instruct`: 17B parametre, **16 Expert** (MoE). Daha hafif/hızlı.
*   **Boyut:** 17 Milyar (Base), ancak MoE yapısı ile efektif kapasite çok daha yüksek.
*   **Özellik:** **Natively Multimodal** (Metin + Resim girdisi kabul eder).
*   **Performans:** DocVQA (Belge üzerinden soru cevaplama) skoru **94.4** ile çok yüksek.
*   **Proje Kullanımı:**
    *   **Vision/Görsel Analiz:** Projede şu an eksik olan "Resim yükleyip soru sorma" özelliği için kullanılmalı. Llama 3.2 Vision yerine bu modeller (daha yeni mimari) denenebilir.
    *   **Genel Sohbet:** Hızlı ve zeki bir orta-boyut model olarak Llama 3.3 70B'ye alternatif (daha düşük maliyet/hız dense) olabilir.

#### 1.4. OpenAI GPT-OSS (Groq Entegrasyonu)
*   **Model:** `openai/gpt-oss-safeguard-20b` (ve 120B versiyonu)
*   **Boyut:** 20B (Safeguard versiyonu)
*   **Amaç:** OpenAI'ın açık ağırlıklı (open-weights) modelleri üzerine kurulu güvenlik ve politika takip modeli.
*   **Özellik:** "Harmony format" ile yapılandırılmış güvenlik gerekçeleri sunar.

---

### 🛡️ Güvenlik ve Moderasyon Modelleri

Bu modeller son kullanıcıya cevap vermek için değil, giren/çıkan mesajı denetlemek içindir.

*   **`meta-llama/llama-guard-4-12b`**:
    *   **Önemi:** En güncel Llama güvenlik modeli.
    *   **Yetenek:** Hem metin hem **görsel** (Image inputs) güvenliğini denetleyebilir.
    *   **Proje:** `router` katmanında "NSFW Image" kontrolü için regex yerine bu model kullanılabilir. Daha akıllı ve "context-aware" sansür sağlar.

*   **`meta-llama/llama-prompt-guard-2` (86m & 22m)**:
    *   **Boyut:** Çok küçük (86 Milyon / 22 Milyon).
    *   **Amaç:** **Prompt Injection** ve **Jailbreak** saldırılarını tespit etmek.
    *   **Hız:** Çok küçük olduğu için milisaniyeler sürer, ana akışı yavaşlatmaz.
    *   **Proje:** Kullanıcı girdisi LLM'e gitmeden önce bu modelden geçirilmeli (`Stage 1: Intent & Guard` aşaması).

---

### 🎙️ Ses Modelleri

*   **`whisper-large-v3-turbo`**:
    *   **Amaç:** Speech-to-Text (Konuşmayı yazıya dökme).
    *   **Farkı:** Standart V3'ten çok daha hızlı (216x speed factor).
    *   **Proje:** Faz 6'da planlanan "Voice Input" özelliği için **kesinlikle** bu model kullanılmalı. Kullanıcı konuşurken bekleme süresini (latency) minimize eder.

*   **`playai-tts`**:
    *   **Amaç:** Text-to-Speech (Yazıyı sese çevirme).
    *   **Not:** Groq dökümanlarında doğrudan yer almasa da (genellikle partner modeldir), yüksek kaliteli ve duygusal tonlamalı ses üretimi için kullanılır. ElevenLabs alternatifidir.

---

## 2. Karşılaştırma ve Öneriler

### Kodlama ve Mantık İçin:
*   **Kazanan:** `qwen/qwen3-32b`
*   **Alternatif:** `moonshotai/kimi-k2-instruct-0905` (Eğer çok uzun dosya okunacaksa)
*   **Neden:** Qwen 3'ün matematik ve mantık skorları (ArenaHard %93.8) rakiplerinden çok önde.

### Genel Sohbet ve Hız İçin:
*   **Kazanan:** `meta-llama/llama-3.3-70b-versatile` (Halen en dengeli production modeli)
*   **Denenmeli:** `meta-llama/llama-4-maverick-17b` (Daha düşük gecikme ve multimodal yetenek gerekirse).

### Güvenlik İçin:
*   Mevcut Regex yapısı (`smart_router.py`) hızlı ama yetersizdir.
*   **Öneri:** `llama-prompt-guard-2-86m` modelini router'ın en başına ekleyin. Maliyeti ve süresi ihmal edilebilir düzeydedir ancak güvenliği enterprise seviyesine taşır.

## 3. Proje Entegrasyon Planı (Özet)

Mevcut `1upgrade_plan.md` güncellenerek şu modeller plana dahil edilmelidir:

1.  **Router Aşaması:** Regex -> `llama-prompt-guard-2-86m` (Injection Koruması).
2.  **Logic/Math İstekleri:** -> `qwen/qwen3-32b` (DeepSeek yerine düşünülebilir).
3.  **Vision (Resimden Soru):** -> `meta-llama/llama-4-maverick-17b` (Yeni özellik).
4.  **Sesli Asistan:** -> `whisper-large-v3-turbo` (Hız için).

### Örnek `decider.py` Güncellemesi (Konsept)

```python
# Matematik sorusu ise Qwen 3 kullan
if domain == "math" or domain == "code":
    model = "qwen/qwen3-32b"
# Resim analizi ise Llama 4 kullan
elif intent == "vision":
    model = "meta-llama/llama-4-maverick-17b-128e-instruct"
# Genel sohbet
else:
    model = "llama-3.3-70b-versatile"
```
