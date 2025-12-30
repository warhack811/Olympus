# 🏆 Turkish Language Benchmark v2 (Short 30) - Scorecard

**Tarih:** 23 Aralık 2025  
**Değerlendirilen Soru Sayısı:** 30  
**Kategoriler:** Akıl Yürütme, Yaratıcılık, Roleplay, Genel Kültür  
**Hakem:** Antigravity (Agent)

## 📊 Genel Puan Durumu (100 Üzerinden)

| Model | Puan | Derece | Özet Performans |
| :--- | :---: | :---: | :--- |
| **moonshotai/kimi-k2-instruct** | **92** | 🥇 **1.** | Türkçesi "native" seviyesinde. Deyimleri, argoyu ve kültürel referansları (Nasrettin Hoca, Tavşan kanı) mükemmel anlıyor. |
| **openai/gpt-oss-120b** | **88** | 🥈 **2.** | Mantık sorularında kusursuz. Yaratıcılıkta çok iyi ama "Roleplay" kısmında bazen fazla "resmi" veya "yapay" kalabiliyor. |
| **meta-llama/llama-4-maverick-17b**| **70** | 🥉 **3.** | Genel kültürü iyi ama mantık sorularında (Q41 Ayak sorusu) basit hatalara düştü. Roleplay yeteneği ortalama. |
| **qwen/qwen3-32b** | **60** | 4. | Türkçesi akıcı ama "Tavşan kanı" gibi kültürel deyimlerde tamamen yanlış bilgi (halüsinasyon) üretti. Mantık yürütmesi iyi. |

---

## 🧐 Kategori Bazlı Analiz

### 1. 🧠 Akıl Yürütme ve Mantık (8 Soru)
*Modelin zekasını ve dikkatini ölçen sorular.*

- **Kimi-k2:** "Ayak sayısı" sorusunda (Q1) yatak ayaklarını da sayarak en dikkatli cevabı verdi. "Mary'nin babası" (Q4) gibi şaşırtmacalı sorularda hata yapmadı.
- **GPT-OSS:** Mantık zinciri çok sağlam. "Kurt-Kuzu-Ot" (Q5) problemini adım adım ve hatasız çözdü.
- **Llama-4:** "Ayak sayısı" sorusunda uçan tavukların ayaklarını saymayarak gereksiz bir yorum yaptı, basit mantık hatasına düştü.
- **Qwen:** Mantık sorularında genelde başarılıydı ancak bazen açıklamaları gereksiz uzattı.

### 2. 🎨 Yaratıcılık ve Edebi Yetenek (7 Soru)
*Hikaye, şiir ve betimleme yeteneği.*

- **Kimi-k2:** "Zamanın durduğu saat dükkanı" (Q9) hikayesi atmosferik ve duygusaldı. "6 kelimelik hikaye" (Q11) örneği ("Bebek ayakkabıları satıldı...") Hemingway'in orijinaline sadık kaldı ancak çeviri yaptı.
- **GPT-OSS:** "Yeni gezegen" (Q15) tasviri çok detaylı ve bilimkurgu öğeleriyle doluydu. Yaratıcılığı çok yüksek.
- **Llama-4:** Şiirleri (Q10 Martı şiiri) biraz basit kafiyelere dayanıyor, derinlik eksik.
- **Qwen:** 6 kelimelik hikaye yerine daha uzun bir cümle kurarak kısıtlamayı ihlal etti.

### 3. 🎭 Roleplay ve Sokak Ağzı (7 Soru)
*Argoyu, raconu ve farklı personaları taklit yeteneği.*

- **Kimi-k2 (Yıldız):** "Racon kesen delikanlı" (Q16) ve "Kapalıçarşı esnafı" (Q18) rollerine mükemmel girdi. "Acı olmasın" diyen müşteriye verdiği tepki (Q19) tam Adana ağzıydı.
- **GPT-OSS:** Plaza dili (Q20) konusunda çok başarılıydı ("Toplantı set edelim"). Ancak sokak ağzında biraz "fazla kibar" kaldı.
- **Llama-4:** Roleplay denemeleri zayıf. Racon keserken bile ansiklopedik bir dil kullandı.
- **Qwen:** Z kuşağı (Q17) taklidinde emojileri iyi kullandı ama cümle yapıları bazen bozuktu.

### 4. 🌍 Genel Kültür (8 Soru)
*Türkiye'ye özgü kültürel bilgi.*

- **Kimi-k2:** "Tavşan kanı" (Q25) deyimini doğru bildi (çayın rengi). İmam Bayıldı tarifini eksiksiz verdi.
- **Qwen (Büyük Hata):** "Tavşan kanı" deyimini "tavşan kanının süzülmesi" gibi korkunç bir halüsinasyonla açıkladı. Bu büyük bir eksi puan sebebi.
- **Llama-4:** Genel kültür sorularında (İnce Memed, Rize çayı) doğru bilgiler verdi.

---

## 🚀 Sonuç ve Tavsiye

Bu 30 soruluk "Short Benchmark" sonucunda:

1.  **MoonshotAI Kimi-k2**, Türkçe'nin inceliklerine, kültürel kodlarına ve sokak ağzına en hakim model olarak **şampiyon** olmuştur. Özellikle yerelleştirme (localization) gerektiren projelerde kesinlikle tercih edilmelidir.
2.  **OpenAI GPT-OSS**, mantıksal derinlik ve akademik/kurumsal dil gerektiren işlerde Kimi ile yarışır düzeyde ve çok güvenilirdir.
3.  **Qwen**, kültürel sorularda (Tavşan kanı hatası) güvenilmez olduğunu kanıtladı, dikkatli kullanılmalı.

**Öneri:** Projeniz "halka inen", samimi bir dil gerektiriyorsa **Kimi-k2**. Daha teknik ve analitik bir iş ise **GPT-OSS**.
