# 🚀 Hybrid Model Orchestration Strategy (Limit-Aware Edition)

**Vizyon:** Benchmark sonuçları ve **Günlük Kullanım Limitleri (TPD/TPM)** analiz edilerek optimize edilmiş, "Sürdürülebilir ve Yüksek Zeka" mimarisi.

---

## 🏗️ 4-Katmanlı Akıllı Mimari (The 4-Tier Architecture)

Sistemi sadece "Zeka"ya göre değil, "Maliyet ve Limit" verimliliğine göre 4 katmana ayırdık.

### 🟡 Katman 0: Kapı Bekçisi (The Router) 🚦
**Model:** `Meta Llama-4-Scout-17b`
*   **Kapasite:** 30K TPM (Çok Hızlı) / 500K TPD (Yüksek Hacim)
*   **Görevi:** Gelen isteği anında analiz eder, zorluk puanı verir (1-10) ve uygun katmana yönlendirir.
*   **Neden?** En yüksek anlık jeton işleme kapasitesine sahip. Darboğaz yaratmaz.

### 🟢 Katman 1: Vitrin (The Tongue) 🗣️
**Model:** `MoonshotAI Kimi-k2-Instruct`
*   **Yedek:** `Qwen3-32b`
*   **Kapasite:** 60 RPM (Yüksek İstek Hızı) / 300K TPD
*   **Görevi:** Kullanıcı ile sohbet, yaratıcı yazarlık, kültürel içerik.
*   **Strateji:** Günlük sohbet yükünü (300K TPD) bu model taşır. Limit dolarsa Qwen devreye girer.

### 🔵 Katman 2: İşçi Arı (The Worker/Middle Brain) 🐝
**Model:** `Meta Llama-4-Scout-17b`
*   **Kapasite:** 500K TPD (Devasa Hacim)
*   **Görevi:**
    *   Özetleme (Summarization).
    *   Basit bilgi çıkarma (Extraction).
    *   RAG ön işleme.
*   **Neden?** Zeki modellerin (GPT-OSS) kıymetli limitlerini "özet çıkarma" gibi basit işlerle harcamamak için bu geniş kapasiteli modeli "Hamal" olarak kullanıyoruz.

### 🔴 Katman 3: Ağır Top (The Deep Brain) 🧠
**Model:** `OpenAI GPT-OSS-120b`
*   **Yedek:** `Llama-3.3-70b-Versatile`
*   **Kapasite:** 200K TPD (Sınırlı) / 8K TPM (Yavaş)
*   **Görevi:**
    *   Karmaşık Kodlama (Python/SQL).
    *   Zor Mantık Soruları (Reasoning).
    *   Sadece Router "Zorluk > 7" derse çalışır.
*   **Strateji:** Llama-70B'nin 100K limiti çok düşük olduğu için onu sadece "Acil Durum Yedeği" yaptık. GPT-OSS ana beyin.

---

## 🛠️ Yönlendirme Mantığı (Routing Logic)

```python
def smart_route(user_query):
    # Llama-4-Scout ile analiz
    analysis = scout_classify(user_query)
    
    if analysis.type == "CHAT":
        return kimi_k2.generate(user_query) # Katman 1
        
    elif analysis.type == "TASK":
        if analysis.complexity < 5:
            return scout_17b.solve(user_query) # Katman 2 (Ucuz İşçi)
        else:
            return gpt_oss.solve(user_query) # Katman 3 (Pahalı Beyin)
```

---

## 📈 Neden Bu Mimari?

1.  **Sürdürülebilirlik:** Llama-70B'yi ana model yapsaydık (100K limit), sistem günde 50 kullanıcıdan sonra dururdu. Bu yapıyla binlerce istek karşılanabilir.
2.  **Hız:** Router olarak 30K TPM'li Scout'u seçmek, sistemin "Düşünme Süresini" minimize eder.
3.  **Güvenlik:** Her katmanın bir yedeği (Failover) vardır. Sistem asla "Hizmet Dışı" olmaz.
