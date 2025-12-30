# 🏆 Turkish Language Benchmark v2 - Final Scorecard

**Tarih:** 23 Aralık 2025  
**Değerlendirilen Soru Sayısı:** 12 (Yazım Kuralları ve Dilbilgisi Kategorisi)  
**Hakem:** Antigravity (Agent)

## 📊 Genel Puan Durumu (100 Üzerinden)

| Model | Puan | Derece | Özet Performans |
| :--- | :---: | :---: | :--- |
| **moonshotai/kimi-k2-instruct** | **85** | 🥇 **1.** | Yazım kuralları, ekler ve TDK normlarında en tutarlı ve doğru model. |
| **openai/gpt-oss-120b** | **75** | 🥈 **2.** | Dilbilgisi açıklamaları çok güçlü ancak bazı spesifik yazım sorularında (örneğin Q10 capitalization) ufak eksikler veya kesilmeler yaşandı. |
| **meta-llama/llama-4-maverick-17b**| **55** | 🥉 **3.** | Bazı soruları doğru bildi (Q9) ancak "kesme işareti" ve "öge" gibi konularda bilgi hataları yaptı. |
| **qwen/qwen3-32b** | **30** | 4. | Potansiyeli var ancak cevapları teknik sorunlar nedeniyle sürekli yarıda kesildi (incomplete responses). |

---

## 🧐 Detaylı Analiz ve Örnekler

Değerlendirme, modelin cevabının doğruluğu, TDK kurallarına uygunluğu ve açıklama kalitesine göre yapılmıştır.

### 1. Yazım ve Dilbilgisi (Q1 - Q12 Analizi)

#### **En Başarılı Oldukları Alanlar:**
- **Kimi-k2-instruct:**
    - **TDK Kuralları:** "Şarj" (Q2), "Hoş geldin" (Q8), "Hukuku" (Q7) gibi konularda TDK'yı referans göstererek nokta atışı doğru cevaplar verdi.
    - **Detaylı Açıklama:** Özellikle "Akşam, yine akşam" (Q6) şiirsel analizinde ve "Hoş geldin" ayrımında gerekçeleri çok iyi açıkladı.
    - **Hata Düzeltme:** "Klavuz" -> "Kılavuz" gibi düzeltmelerde büyük/küçük harf duyarlılığına dikkat etti (Q10).

- **GPT-OSS-120b:**
    - **Akademik Açıklama:** "Ki" bağlacı (Q5) ve "Öge/Öğe" (Q11) farkını tablolarla ve kök bilgisiyle harika açıkladı.
    - **Mantık Çıkarımı:** Anlatım bozukluğu (Q3) konusunda "kazanacağız" düzeltmesiyle en mantıklı çözümü sundu.

#### **Gözlemlenen Hatalar:**
- **Llama-4-Maverick:**
    - **Yanlış Bilgi:** "Öge" ve "Öğe" farkını (Q11) karıştırarak yanlış terimi savundu. Kesme işareti sorusunda (Q12) çekim ekleri yerine yapım eklerini örnek göstererek konuyu karıştırdı.
    - **Doğru Yanıtları:** "de/da" ayrımı (Q9) konusunda en pratik ve doğru yöntemi ("cümleden çıkarma testi") önerdi.

- **Kimi-k2-instruct (Nadir Hatalar):**
    - **Halüsinasyon:** "Art arda" sorusunda (Q4) TDK'nın aksine yanlış olan "Art arda" yazımını savundu (Doğrusu: Ard arda).

---

## 🏅 Kategori Birincileri

| Kategori | Kazanan | Neden? |
| :--- | :--- | :--- |
| **TDK & İmla** | **Kimi-k2** | Resmi kurallara en sadık model. İstisnaları (şarj, hukuku) iyi biliyor. |
| **Dilbilgisi Analizi**| **GPT-OSS** | "Ki" bağlacı ve kelime kökeni analizlerinde çok derinlikli. |
| **Pratik Çözüm** | **Llama-4** | Karmaşık kurallar yerine pratik testler (de/da testi) sunmada başarılı. |

## 🚀 Sonuç ve Öneri

Türkçe dil görevleri, redaksiyon ve TDK uyumluluğu gerektiren işler için **MoonshotAI Kimi-k2** şu anki test setinde (12 soru) en güvenilir model olarak öne çıkmıştır. Mantıksal analiz ve derinlemesine açıklama gerektiren durumlarda **OpenAI GPT-OSS** güçlü bir alternatiftir.

*Not: Test seti 12 soru ile sınırlı kalmıştır, daha kapsamlı bir testte (100 soru) sıralama değişebilir ancak Kimi'nin Türkçe hakimiyeti dikkat çekicidir.*
