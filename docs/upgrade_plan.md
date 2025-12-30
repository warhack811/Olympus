Mami AI Pro - Kapsamli Yol Haritasi
> Hedef: 10 premium kullanici icin normal AI'lardan farkli, gercek insan hissi veren, proaktif kisisel asistan

> Oncelik: Insansi cevap kalitesi + Modern UI

---

Faz 1: Temel Altyapi & Mimari Donusumu
Sure: 5-7 gun | Oncelik: KRITIK

1.1 Plugin Mimarisi
Tum yeni ozellikler modular plugin olarak eklenebilmeli:

app/plugins/
  __init__.py          # Plugin loader
  base.py              # BasePlugin abstract class
  registry.py          # Plugin kayit sistemi
  reminder/            # Hatirlama plugin'i
  mood_analyzer/       # Moral analiz plugin'i
  proactive/           # Proaktif oneri plugin'i
Her plugin: on_message, on_startup, on_schedule hook'lari

1.2 Global Config Sistemi
Hardcode yerine dinamik yapilandirma:

# app/core/dynamic_config.py
class DynamicConfig:
    # Veritabanindan yuklenen ayarlar
    model_settings: Dict      # Model isimleri, API'ler
    ui_settings: Dict         # Temalar, renkler, metinler
    feature_flags: Dict       # Ozellik on/off
    persona_settings: Dict    # AI kisiligi
Dosyalar:

app/config.py → DynamicConfigService ile genislet
Yeni: app/core/dynamic_config.py
Yeni: app/core/models.py → SystemConfig tablosu
1.3 Veritabani Semalari
Yeni tablolar:

| Tablo | Amac |

|-------|------|

| system_configs | Dinamik ayarlar (key-value + JSON) |

| user_profiles | Kullanici kisiligi, tercihler |

| user_preferences | Ton, emoji, uzunluk ayarlari |

| reminders | Hatirlama/etkinlik kayitlari |

| mood_logs | Kullanici ruh hali gecmisi |

| feedback_logs | Begen/begenme kayitlari |

| api_configs | API anahtarlari, modeller |

| themes | Dinamik tema tanimlari |

---

Faz 2: Insansi Cevap Kalitesi Motoru
Sure: 7-10 gun | Oncelik: KRITIK

2.1 Cognitive Layers (Dusunce Katmanlari)
app/ai/layers/
  __init__.py
  reason.py        # Mantiksal cozumleme
  plan.py          # Gorev adimlari siralama
  critique.py      # Cevap elestirisi
  persona.py       # Kisilik uyumu
  correction.py    # Hata duzeltme
  implicit.py      # Davranis cikarimi
Pipeline:

User Message → Reason → Plan → Generate → Critique → Persona Align → Correct → Output
2.2 Personality Consistency Engine
app/ai/prompts/identity.py genislet:

Tutarli Kisilik: Sabah/aksam, mutlu/uzgun - ayni "kisi"
Dogal Gecisler: "Gecen hafta anlattigin X nasil oldu?"
Contextual Expressions: Duruma gore emoji, ton
Celebration Moments: Basarilari kutlama
2.3 Turkce Dil Kalitesi Modulu
# app/services/turkish_enhancer.py
class TurkishEnhancer:
    def fix_spelling(text: str) -> str          # Yazim hatalari
    def improve_grammar(text: str) -> str       # Cumle dusuklukleri
    def enhance_naturalness(text: str) -> str   # Dogallik
    def adapt_formality(text: str, level: str)  # Resmiyet ayari
2.4 Response Formatter
# app/services/response_formatter.py
class ResponseFormatter:
    def format_code_blocks()      # Syntax highlighted kod
    def format_tables()           # Markdown tablolar
    def format_lists()            # Sirali/sirasiz listeler
    def format_headers()          # Basliklar
    def add_visual_elements()     # Emoji, ayiraclar
2.5 Akilli Model Routing
app/chat/decider.py yeniden tasarla:

Qwen3-8B icin (Sansursuz):

Yetiskin/NSFW icerik
Roleplay, karakter canlandirma
Hassas konular (siyaset, din)
Sevgili/Arkadas modlari
Groq Llama 70B icin:

Genel sohbet, bilgi
Teknik, kod
Arastirma, analiz
Internet aramasi gerektiren
2.6 Mod Sistemi
| Mod | Davranis | Model |

|-----|----------|-------|

| Standart | Dengeli, profesyonel | Groq |

| Arastirmaci | Detayli, kaynakli | Groq + Internet |

| Yakin Arkadas | Samimi, destekleyici | Qwen3 |

| Sevgili | Romantik, ozel | Qwen3 |

| Sanatci | Yaratici, ilham verici | Her ikisi |

| Yazar | Edebi, detayli | Her ikisi |

| Roleplay | Karakter bazli | Qwen3 |

| Is Adami | Profesyonel, ozlu | Groq |

| Coder | Teknik, kod odakli | Groq |

---

Faz 3: Modern Frontend Tasarimi
Sure: 10-14 gun | Oncelik: KRITIK

3.1 Teknoloji Secimi
React 18 + TypeScript + TailwindCSS + Framer Motion

ui/
  src/
    components/
      Chat/
        ChatArea.tsx
        MessageBubble.tsx
        MessageActions.tsx     # Kopyala, Paylas, Begen
        ThinkingPanel.tsx      # Dusunme sureci
        TypingIndicator.tsx
      Sidebar/
      Settings/
      Admin/
    hooks/
    stores/           # Zustand state management
    themes/           # 6 tema
    utils/
3.2 Chat Mesaj Ozellikleri
Her mesajda:

✅ Kopyala butonu
✅ Paylas butonu
✅ Begen / Begenme
✅ Yeniden olustur
✅ Dusunme sureci (tiklanabilir acilir panel)
✅ Hangi model/sistem kullanildi bilgisi
✅ Zaman damgasi
3.3 Tema Sistemi (6 Tema)
Dark Mode - Koyu, goz yormayan
Light Mode - Aydinlik, temiz
Cosmic - Uzay temalı, mor/mavi
Ocean - Deniz mavisi tonları
Sunset - Sicak, turuncu/pembe
Custom - Admin'den tanimlanan
Admin panelden kod degisikligi olmadan tema ekleme/duzenleme.

3.4 Kullanici Tercihleri Sayfasi
/settings
  /profile        - Temel bilgiler
  /preferences    - Ton, emoji, uzunluk
  /memory         - Hatirlama yonetimi
  /reminders      - Etkinlikler
  /appearance     - Tema, font
  /notifications  - Bildirim ayarlari
  /privacy        - Gizlilik
3.5 Galeri Yenileme
Grid gorunum
Lightbox onizleme
Indir / Paylas / Sil butonlari
Prompt & ayar bilgisi
Filtreleme (tarih, prompt)
3.6 Teknik Gereksinimler
✅ PWA (Service Worker)
✅ 60 FPS animasyonlar
✅ Mobil responsive
✅ Offline temel destek
✅ Web Push Notifications
✅ Keyboard shortcuts
---

Faz 4: Gelismis Hafiza & Kisiselleştirme
Sure: 7-10 gun | Oncelik: YUKSEK

4.1 Hafiza Mimarisi
# app/memory/advanced_store.py
class AdvancedMemoryStore:
    # Kategoriler
    IDENTITY = "identity"       # isim, yas, meslek
    PREFERENCES = "preferences" # hobi, tercihler
    FACTS = "facts"            # aile, olaylar
    GOALS = "goals"            # hedefler
    RELATIONSHIPS = "relationships"  # yakinlari
    EVENTS = "events"          # gelecek etkinlikler
    
    # Temporal
    SHORT_TERM = "short"       # Session icinde (moral vb.)
    MEDIUM_TERM = "medium"     # Haftalik
    LONG_TERM = "long"         # Kalici
4.2 Implicit Memory Layer
Kullanici davranislarindan cikarim:

Konusma saatleri → Uygun bildirim zamani
Sik sorulan konular → Ilgi alanlari
Tepki patternleri → Kisilik profili
Emoji kullanimi → Iletisim tercihi
4.3 Conflict Resolution
Celisen bilgileri yonetme:

# "Adim Ali" vs "Adim Ahmet" → Kullaniciya sor veya en yeniyi al
def resolve_conflict(old_memory, new_memory):
    if new_memory.confidence > old_memory.confidence:
        invalidate(old_memory)
        save(new_memory)
4.4 Adaptif Davranis Sistemi
Oncelik Sirasi:
1. Kullanici acik tercihi (Settings'den)
2. Mod secimi davranisi
3. Implicit cikarimlar
4. Varsayilan

Hard vs Soft Override:
- Standart mod: Kullanici tercihi %100 uygulanir
- Diger modlar: Mod ruhu korunur, tercih %60 etkiler
---

Faz 5: Kapsamli Admin Panel
Sure: 7-10 gun | Oncelik: YUKSEK

5.1 Dashboard
Aktif kullanici sayisi
Gunluk mesaj istatistikleri
Model kullanim dagilimi
Sistem sagligi (CPU/RAM)
Hata loglari ozeti
5.2 Yapilandirma Yonetimi
Model Ayarlari:

Groq modelleri ve API keys
Ollama/Qwen ayarlari
Fallback zinciri
Temperature, token limitleri
Forge/Gorsel Uretim:

Checkpoint modelleri
LoRA listesi
Varsayilan uretim ayarlari
Sampler, steps, CFG
API Yonetimi:

API key ekleme/silme/duzenleme
Kullanim limitleri
Rate limiting ayarlari
5.3 Kullanici Yonetimi
Kullanici listesi
Dondurma / Aktif etme
Limit degistirme
Uyari gonderme
Ban / Unban
Izin ve kisitlamalar
Sansur seviyesi (kullanici bazli)
5.4 Icerik Yonetimi
Tema Duzenleyici:

Renk paleti
Font ayarlari
Tema ismi
Onizleme
Metin Duzenleyici:

AI tanitim metinleri
Hosgeldin mesajlari
Hata mesajlari
UI metinleri
Persona Duzenleyici:

AI ismi
Kisilik ozellikleri
Varsayilan ton
Yasak kelimeler
5.5 Sistem Izleme
CPU / RAM / Disk kullanimi
Servis durumlari (API, DB, ChromaDB, Ollama)
Job kuyrugu durumu
Hata loglari (filtrelenebilir)
Audit log (admin islemleri)
---

Faz 6: Proaktif Asistan Ozellikleri
Sure: 7-10 gun | Oncelik: ORTA

6.1 Zaman Farkindaligi
# Her prompt'a eklenir
ZAMAN_CONTEXT = f"""
Şu an: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Gün: {day_name_turkish}
Lokasyon: İstanbul, Türkiye
"""
6.2 Hatirlama Sistemi
Otomatik Tespit:

"Yarin toplantim var" → Event olustur
"Dogum gunum 15 Mart" → Yillik etkinlik
"Bu hafta sonu tatile gidiyorum" → Kisa vadeli
Manuel Ekleme:

Tercihler > Hafiza > Etkinlik Ekle
Tarih, saat, tekrar, bildirim suresi
6.3 Bildirim Sistemi
# Celery Beat ile zamanlanmis gorevler
@celery.task
def check_reminders():
    upcoming = get_upcoming_events(hours=24)
    for event in upcoming:
        send_push_notification(event.user_id, event.message)
6.4 Moral Analizi & Takip
class MoodAnalyzer:
    def analyze_message(text: str) -> MoodScore:
        # Sentiment analysis
        # Keywords: uzgun, mutlu, stresli, yorgun...
        
    def should_follow_up(user_id: int) -> bool:
        # Son mood negatifse ve 2+ saat gectiyse
        
    def generate_check_in(mood_history: List) -> str:
        # "Nasil hissediyorsun simdi?"
6.5 Oneri Motoru
Kullanici davranislarina gore proaktif oneriler
"Gecen hafta bahsettigin kitabi okudun mu?"
"Bugun hava guzel, yuruyuse cikmak ister misin?"
6.6 Daily Check-in (Opsiyonel)
Kullanici isterse:

Sabah motivasyon mesaji
Aksam gun ozeti
Haftalik degerlendirme
---

Faz 7: Internet Arama Iyilestirmesi
Sure: 5-7 gun | Oncelik: ORTA

7.1 Multi-Source Search
class SearchOrchestrator:
    sources = [
        GoogleSearchAPI(),      # Genel arama
        NewsAPI(),              # Haberler
        WeatherAPI(),           # Hava durumu
        FinanceAPI(),           # Doviz/Borsa
        WikipediaAPI(),         # Ansiklopedi
    ]
    
    async def search(query: str, intent: str):
        # Intent'e gore uygun kaynaklari sec
        # Paralel sorgula
        # Sonuclari birlestir ve ozetle
7.2 Result Synthesis
Ham sonuclari birlestirme
Kaynak gostererek ozet olusturma
Celiskileri belirleme
Guvenilirlik skoru
---

Faz 8: Ileri Ozellikler (Gelecek)
Sure: Belirsiz | Oncelik: DUSUK

8.1 Multimodal
Vision: Gorsel analiz (GPT-4V veya local model)
TTS: Sesli cikti (Edge TTS / Local)
STT: Sesli giris (Whisper)
Text-to-Video: Kisa klipler
8.2 Analytics Dashboard
Kullanici memnuniyet metrikleri
Cevap kalite skorlari
Model performans karsilastirma
A/B test sonuclari
8.3 Mobil/Desktop App Hazirligi
API-first mimari (zaten yapilacak)
Push notification altyapisi
Cross-platform sync
Offline data management
---

Uygulama Takvimi
| Faz | Sure | Baslangic | Bitis |

|-----|------|-----------|-------|

| Faz 1: Altyapi | 5-7 gun | Hafta 1 | Hafta 1 |

| Faz 2: Cevap Kalitesi | 7-10 gun | Hafta 2 | Hafta 3 |

| Faz 3: Frontend | 10-14 gun | Hafta 2 | Hafta 4 |

| Faz 4: Hafiza | 7-10 gun | Hafta 4 | Hafta 5 |

| Faz 5: Admin Panel | 7-10 gun | Hafta 5 | Hafta 6 |

| Faz 6: Proaktif | 7-10 gun | Hafta 6 | Hafta 7 |

| Faz 7: Arama | 5-7 gun | Hafta 7 | Hafta 8 |

Toplam Tahmini Sure: 8-10 Hafta

---

Teknik Gereksinimler
Backend:

Python 3.10+
FastAPI
SQLModel + PostgreSQL (onerilir)
ChromaDB
Redis (cache + pub/sub)
Celery (background jobs)
Frontend:

React 18 + TypeScript
TailwindCSS
Framer Motion
Zustand (state)
React Query (data fetching)
AI/ML:

Ollama + Qwen3-8B
Groq API (Llama 3.3 70B)
ChromaDB embeddings
DevOps:

Docker Compose
Nginx reverse proxy
SSL/TLS
19 To-dos · Completed In Order
New
Faz 1.1: Plugin mimarisi tasarimi ve base class
Faz 1.2: Global dinamik config sistemi
Faz 1.3: Yeni veritabani semalari ve migration
Faz 2.1: Cognitive layers (Reason, Plan, Critique, Persona)
Faz 2.2: Personality consistency engine
Faz 2.3: Turkce dil kalitesi modulu
Faz 2.4: Response formatter (kod, tablo, liste)
Faz 2.5: Akilli model routing (Qwen3 + Groq)
Faz 2.6: Mod sistemi (Standart, Arkadas, Sevgili, vb.)
Faz 3.1: React + TypeScript + Tailwind kurulum
Faz 3.2: Modern chat UI ve mesaj aksiyonlari
Faz 3.3: 6 tema sistemi
Faz 3.4: Kullanici tercihleri sayfasi
Faz 3.5: Gelismis galeri sistemi
Faz 3.6: PWA ve push notifications
Faz 4: Gelismis hafiza ve kisiselleştirme
Faz 5: Kapsamli admin panel
Faz 6: Proaktif asistan ozellikleri
Faz 7: Internet arama iyilestirmesi
Referenced by 1 Agent
Initial greeting · Author
