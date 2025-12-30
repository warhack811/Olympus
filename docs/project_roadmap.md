# 🗺️ Mami AI v4 - "Big Chatbot" Transformation Roadmap

**Vizyon:** Projeyi basit bir LLM wrapper'ından, **bilişsel yetenekleri (Cognitive Capabilities)** olan, hafızalı, ve araç kullanabilen (Agentic) bir ekosisteme dönüştürmek.

---

## 📅 Faz 1: The Core Engine (Hibrit Mimari)
**Hedef:** Modelin cevap kalitesini ve samimiyetini maksimize etmek.
*Süre Tahmini: 1 Hafta*

- [ ] **Smart Router (Llama-4-Scout)**
    - 30K TPM kapasiteli model ile gelişmiş niyet analizi ve zorluk derecelendirmesi (1-10).
- [ ] **4-Tier Engine Entegrasyonu**
    - **Katman 1 (Tongue):** Kimi-k2 (Chat).
    - **Katman 2 (Middle Brain):** Llama-4-Scout (Özet/Basit İşler).
    - **Katman 3 (Deep Brain):** GPT-OSS-120b (Complex Logic).
- [ ] **Persona Yönetimi**
    - Sistem promptlarının dinamikleşmesi (Kullanıcıya göre "Abla", "Kanka" veya "Beyefendi" moduna geçiş).

## 🧠 Faz 2: The Memory (Hafıza & RAG v2.5)
**Hedef:** Kullanıcıyı tanıyan ve geçmişi hatırlayan bir sistem. *Mevcut `rag_v2` altyapısı üzerine inşa edilecek.*
*Süre Tahmini: 2 Hafta*

- [ ] **Vector Store Optimizasyonu (ChromaDB)**
    - Mevcut `paraphrase-multilingual` modelinin performansının artırılması.
    - Metadata filtreleme (Tarih, kişi, konu bazlı hatırlama).
- [ ] **Long-Term Memory (Özetleme)**
    - Konuşma bitince LLM'in o günü özetleyip "Kullanıcı Profili"ne kaydetmesi (Örn: "Ahmet vejetaryen, kedisi var").
- [ ] **Context Window Yönetimi**
    - Token limitine takılmadan sonsuz hafıza hissi yaratmak için "Sliding Window" ve "Özet Çağırma" teknikleri.

## 🛠️ Faz 3: The Hands (Araç Kullanımı & Ajanlar)
**Hedef:** Sadece konuşan değil, "iş yapan" bir asistan.
*Süre Tahmini: 2-3 Hafta*

- [ ] **Function Calling Altyapısı**
    - LLM'in kendi kendine "Bu soru için Google araması yapmalıyım" diyebilmesi.
- [ ] **Entegre Araçlar**
    - 🌐 **Web Search:** Güncel olaylar (Dolar kuru, maç sonucu) için.
    - 📅 **Calendar:** Randevu oluşturma.
    - 🖼️ **Image Gen:** Sohbet içinde resim üretme (Flux/Midjourney API).
- [ ] **Self-Correction (Otokontrol)**
    - Modelin kendi cevabını "Bu güvenli mi? Doğru mu?" diye kontrol etmesi (Guardrails).

## 🖥️ Faz 4: The Body (UI & Production)
**Hedef:** Bu zekayı son kullanıcıya şık bir paketle sunmak.
*Süre Tahmini: 2 Hafta*

- [ ] **Next.js / React Frontend**
    - WhatsApp benzeri, akıcı, "Typing..." animasyonlu modern arayüz.
    - Sesli asistan modu (STT/TTS).
- [ ] **API Gateway (FastAPI)**
    - Rate limiting, User Auth (JWT), Loglama.
- [ ] **Deployment (Docker/K8s)**
    - Ölçeklenebilir, tek tıkla kurulum yapısı.

---

## 🚀 Kritik Başarı Faktörleri (KPIs)

1.  **Samimiyet Skoru:** Kullanıcı "Botla konuşuyorum" hissinden ne kadar uzak? (Kimi-k2 ile çözülecek).
2.  **Hafıza Doğruluğu:** "Geçen hafta sana ne anlatmıştım?" sorusuna doğru cevap verme oranı.
3.  **Hız (Latency):** Cevap süresinin 2 saniyenin altında tutulması (Router optimizasyonu ile).

**Sonuç:** Bu yol haritası, projenizi sıradan bir RAG botundan, **Jarvis benzeri kişisel bir asistana** dönüştürecektir. İlk adım olarak "Core Engine" ile başlamayı öneriyorum.
