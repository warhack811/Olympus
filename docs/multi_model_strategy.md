# Mami AI: Multi-Model Architecture & Orchestration Strategy

**Durum:** Draft Proposal  
**Hedef:** Groq API üzerindeki bağımsız rate limitleri kullanarak proje performansını ve dayanıklılığını (resilience) maksimize etmek.

---

## 1. Mimari Felsefesi: "Right Model for the Right Task"

Tek bir model (One-size-fits-all) yerine, her görevi o alanda en iyi olan ve *kendi bağımsız rate limitine sahip* modele yönlendireceğiz. Bu sayede `llama-3.3-70b` kotamız dolsa bile, kod yazma ve vizyon özellikleri çalışmaya devam edecek.

### Model Rol Dağılımı

| Rol | Birincil Model (Primary) | Yedek Model (Fallback) | Neden? |
| :--- | :--- | :--- | :--- |
| **🧠 General Chat** | `llama-3.3-70b-versatile` | `llama-4-maverick-17b` | 70B en yüksek EQ/IQ dengesine sahip. Llama 4 ise çok hızlı ve zeki. |
| **🧮 Logic & Math** | `qwen/qwen3-32b` | `openai/gpt-oss-120b` | Qwen 3 matematik/mantıkta rakipsiz (%93.8). |
| **💻 Coding** | `qwen/qwen3-32b` | `moonshotai/kimi-k2-instruct` | Qwen kodlamada çok iyi. Kimi ise çok uzun kodları okuyabilir. |
| **👁️ Vision (Görsel)** | `llama-4-maverick-17b` | `llama-4-scout-17b` | Maverick native multimodal ve yüksek detay başarısı var. |
| **📚 Long Context** | `moonshotai/kimi-k2-instruct` | `openai/gpt-oss-120b` | Kimi 256K context ile kitap/belge analizi için tek seçenek. |
| **🚀 Fast/Router** | `llama-4-scout-17b` | `llama-3.1-8b-instant` | Scout, 8b kadar hızlı ama daha zeki (17B MoE). |
| **🛡️ Safety** | `llama-guard-4-12b` | `gpt-oss-safeguard-20b` | Guard 4 hem metin hem resim denetleyebilir. |

---

## 2. Rate Limit Orkestrasyonu

Her modelin dakikalık token (TPM) ve istek (RPM) limiti bağımsızdır. Bu mimariyi şöyle kullanacağız:

1.  **Paralel Yük Dağıtımı:**
    *   Kullanıcı kod sorduğunda -> **Qwen 3** kotasından yer (Llama kotası etkilenmez).
    *   Kullanıcı resim attığında -> **Llama 4** kotasından yer.
    *   Kullanıcı sohbet ettiğinde -> **Llama 3.3** kotasından yer.
    
    *Sonuç:* Toplam kapasite 3-4 katına çıkar.

2.  **Akıllı Fallback Zinciri:**
    *   Eğer `llama-3.3-70b` 429 (Too Many Requests) hatası verirse:
        *   Sistem anında `llama-4-maverick-17b` modeline geçer.
        *   Kullanıcı hissetmez, sadece cevap biraz daha kısalabilir.

---

## 3. Uygulama Planı

### A. Konfigürasyon Güncellemesi (`config.py`)

```python
class Settings(BaseSettings):
    # ... mevcut ayarlar ...
    
    # ROL BAZLI MODEL TANIMLARI
    MODEL_CHAT_PRIMARY: str = "llama-3.3-70b-versatile"
    MODEL_CHAT_FALLBACK: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    
    MODEL_LOGIC_PRIMARY: str = "qwen/qwen3-32b"
    MODEL_LOGIC_FALLBACK: str = "openai/gpt-oss-120b"
    
    MODEL_VISION_PRIMARY: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    
    MODEL_LONG_CONTEXT: str = "moonshotai/kimi-k2-instruct-0905"
```

### B. Akıllı Model Seçici (`model_selector.py`)

Yeni bir servis (`app/chat/model_selector.py`) oluşturulacak. `SmartRouter` sadece amacı (intent) belirleyecek, `ModelSelector` ise o anki duruma ve kotaya göre en iyi modeli seçecek.

**Mantık:**
```python
def select_model(intent, domain, context_length):
    if context_length > 30000:
        return settings.MODEL_LONG_CONTEXT
        
    if intent == "vision":
        return settings.MODEL_VISION_PRIMARY
        
    if domain in ["math", "code", "logic"]:
        return settings.MODEL_LOGIC_PRIMARY
        
    return settings.MODEL_CHAT_PRIMARY
```

### C. Fallback Dekoratörü (`decider.py`)

API çağrıları, model bazlı fallback destekleyecek şekilde güncellenecek.

```python
FALLBACK_MAP = {
    settings.MODEL_CHAT_PRIMARY: settings.MODEL_CHAT_FALLBACK,
    settings.MODEL_LOGIC_PRIMARY: settings.MODEL_LOGIC_FALLBACK,
}

async def call_groq_safe(...):
    try:
        # Ana modeli dene
    except RateLimitError:
        # Fallback tablosuna bak ve yedek modeli dene
        backup_model = FALLBACK_MAP.get(current_model)
        if backup_model:
            # Yedek modelle tekrar dene
```

---

## 4. Özet Faydalar

1.  **Kesintisiz Deneyim:** Bir model dursa bile diğerleri çalışır.
2.  **Uzmanlık:** Matematik sorularını matematikçiye (Qwen), sohbeti konuşmacıya (Llama) yönlendiririz.
3.  **Kapasite Artışı:** Groq'un sunduğu toplam "ücretsiz" kapasiteyi sonuna kadar kullanırız.
