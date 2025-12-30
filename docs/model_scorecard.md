# AI Model Scorecard (Benchmark Analysis)

Bu rapor, `docs/benchmark_results.md` dosyasındaki detaylı benchmark sonuçlarına dayanarak oluşturulmuştur. Modeller; Matematik, Kodlama, Mantık, Türk Kültürü ve diğer alanlardaki performanslarına göre 100 üzerinden puanlanmıştır.

## 🏆 Genel Özet (Leaderboard)

| Model İsmi | Ortalama Puan | Güçlü Olduğu Alanlar | Zayıf Olduğu Alanlar |
| :--- | :---: | :--- | :--- |
| **moonshotai/kimi-k2-instruct** | **94** | Türk Kültürü, Tarih, Yaratıcı Yazarlık, Rol Yapma | Matematik (bazı durumlarda) |
| **meta-llama/llama-4-maverick** | **91** | Mantık, Felsefe, Fizik, Coğrafya | Matematik (temel aritmetik hataları) |
| **openai/gpt-oss-120b** | **89** | Genel Bilgi, Tutarlılık, Fizik | Bazen çok uzun/karışık cevaplar |
| **qwen/qwen3-32b** | **87** | Çeviri, Matematik | Rol Yapma (Prompt sızıntısı) |
| **llama-3.3-70b-versatile** | **85** | Özetleme, Sinema (Matrix) | Detaylı kültürel konularda yüzeysellik |

---

## 📊 Kategori Bazlı Puanlama ve Analiz

### 1. 🇹🇷 Türk Kültürü ve Tarih
*Modellerin Türk tarihi, gelenekleri ve dil nüanslarına hakimiyeti.*

| Model | Puan | Gerekçe |
| :--- | :---: | :--- |
| **moonshotai/kimi-k2-instruct** | **99** | **Mükemmel.** İstanbul'un fethinin "bir çağın kapanıp yenisinin açılması" gibi derin tarihsel ve kültürel önemini kusursuz bir dille anlattı. Ayasofya ve Türk kahvesi konularında da en doğru ve detaylı bilgiyi verdi. |
| **openai/gpt-oss-20b** | **90** | İyi yapılandırılmış, maddeli anlatımlar sundu ancak Kimi-k2 kadar "ruhlu" ve derinlikli değildi. |
| **meta-llama/llama-4-maverick** | **85** | Bilgiler doğru ancak anlatım biraz daha ansiklopedik ve kuru kaldı. |

### 2. 🧠 Mantık ve Akıl Yürütme
*Zor mantık soruları (Knights/Knaves, Bloop/Zark) ve felsefi kavramlar.*

| Model | Puan | Gerekçe |
| :--- | :---: | :--- |
| **meta-llama/llama-4-maverick** | **98** | **Lider.** "Bloop/Zark" mantık sorusunu ve "Stoacılık" kavramını en net ve doğru şekilde açıkladı. Karmaşık mantıksal çıkarımlarda çok başarılı. |
| **llama-3.3-70b-versatile** | **92** | Mantık sorularında güçlü, ancak açıklamaları Maverick kadar özlü değil. |
| **qwen/qwen3-32b** | **85** | Genellikle doğru, ancak mantık yürütme sürecini (chain-of-thought) bazen kullanıcıya yansıtarak yanıtı karmaşıklaştırıyor. |

### 3. ✍️ Yaratıcı Yazarlık ve Rol Yapma
*Şiir yazma, hikaye oluşturma ve belirli bir karakterle (persona) konuşma.*

| Model | Puan | Gerekçe |
| :--- | :---: | :--- |
| **moonshotai/kimi-k2-instruct** | **97** | **Çok Yaratıcı.** "Öfkeli korsan kaptanı" rolünü mükemmel oynadı; dil kullanımı, argosu ve tonlaması çok inandırıcıydı. "Sonbahar" şiirinde duygusal derinliği en iyi yansıtan modeldi. |
| **openai/gpt-oss-120b** | **92** | Rol yapma yeteneği yüksek, korsan rolünde başarılıydı ancak Kimi-k2 kadar doğal değildi. |
| **qwen/qwen3-32b** | **70** | Rol yapma sorusunda `<think>` bloklarını sızdırdı ve doğrudan role girmek yerine süreci anlattı. |

### 4. 🔬 Bilim (Fizik, Tıp, Coğrafya)
*Bilimsel kavramları açıklama ve doğruluk.*

| Model | Puan | Gerekçe |
| :--- | :---: | :--- |
| **meta-llama/llama-4-maverick** | **96** | **En İyi Açıklayıcı.** "Schrödinger'in Kedisi"ni 10 yaşındaki bir çocuğa en iyi anlatan modeldi. Japonya depremleri ve Einstein'ın kütle-enerji ilişkisi konularında da çok netti. |
| **moonshotai/kimi-k2-instruct** | **94** | Tıp alanında (Diyabet belirtileri) en kapsamlı ve doğru listeyi sundu. |
| **openai/gpt-oss-120b** | **90** | Bilimsel olarak doğru ancak açıklamalar bazen gereğinden fazla teknik detay içeriyor. |

### 5. 🧮 Matematik ve Kodlama
*Matematiksel işlemler ve kod snippet'leri.*

| Model | Puan | Gerekçe |
| :--- | :---: | :--- |
| **qwen/qwen3-32b** | **95** | Matematiksel işlemlerde tutarlı ve doğru. Python ile üs alma sorusunda en temiz kodu verdi. |
| **moonshotai/kimi-k2-instruct** | **92** | Matematikte güçlü, ancak bazen işlem basamaklarını gereksiz uzatabiliyor. |
| **meta-llama/llama-4-maverick** | **80** | Basit aritmetik işlemlerde (1234 * 5678 gibi) bazen hata yapabiliyor, ancak kodlama mantığı sağlam. |

### 6. 🌐 Çeviri ve Dil Yeteneği
*İngilizce-Türkçe ve diğer diller (Fransızca) arası çeviri.*

| Model | Puan | Gerekçe |
| :--- | :---: | :--- |
| **qwen/qwen3-32b** | **98** | **En İyi Çevirmen.** "Başarının anahtarı tutarlılıktır" cümlesinin İngilizce çevirisinde kelime seçimleri ve gramer yapısı mükemmeldi (`In any endeavor...`). Düşünce sürecini detaylı analiz ederek en doğru kelimeyi seçiyor. |
| **moonshotai/kimi-k2-instruct** | **95** | Fransızca çeviride (`Où est la bibliothèque la plus proche ?`) tam isabet sağladı. |
| **llama-3.3-70b-versatile** | **90** | Çeviriler doğru ancak bazen çok literal (kelimesi kelimesine) kalabiliyor. |

---

## 📝 Sonuç

* **Genel Kullanım ve Türkçe İçerik İçin:** **`moonshotai/kimi-k2-instruct`** tartışmasız en iyi seçenek. Özellikle Türkiye'ye özgü kültürel konular, tarih ve yaratıcı yazarlıkta rakiplerine fark atıyor.
* **Akademik, Mantıksal ve Bilimsel Sorgular İçin:** **`meta-llama/llama-4-maverick`** tercih edilmeli. Karmaşık kavramları basitleştirme ve mantıksal çıkarım yapma konusunda çok yetenekli.
* **Çok Dilli ve Teknik Görevler İçin:** **`qwen/qwen3-32b`** matematik ve çeviri konularında çok sağlam bir alternatif.
