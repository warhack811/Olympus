FAZ 1: "Eller" - Tool Registry ve Genişletilebilir Altyapı
Amaç: Router'ın sadece metin üretmesini değil, dış dünyayla (API'lar) konuşmasını sağlamak. Kodun içine tool gömmek yerine, dışarıdan yönetilebilir bir yapı kurmak.

Tool Klasör Yapısı (/tools):

tools/definitions/: Her tool için bir JSON Manifest dosyası oluşturulacak (Örn: weather.json, finance.json).

tools/handlers/: Bu JSON'ların arkasındaki Python fonksiyonları (Serper API wrapper, Flux API wrapper).

Universal Tool Loader (dag_executor.py Güncellemesi):

dag_executor.py artık sadece LLM çağırmayacak; tools/definitions klasörünü tarayıp mevcut yetenekleri hafızaya alacak.

Yeni Tool'lar Eklenecek:

search_agent: Serper API (Agentic Search - Çoklu sorgu + Scraping).

finance_tracker: Borsa/Kripto verisi.

visual_artist: Flux (Local/Forge) görsel üretimi.

calendar_manager: Google Calendar entegrasyonu (Mock veya gerçek).

local_genius: Gemma 2 9B (Sansürsüz yerel model) bağlantısı.





FAZ 2: "Hafıza" - Neo4j ve GraphRAG Entegrasyonu
Amaç: JSON tabanlı basit hafızadan, ilişkisel ve proaktif "Bilişsel Bellek" yapısına geçiş.

Neo4j Kurulumu (Altyapı):

Neo4j AuraDB (Free) hesabı açılacak ve bağlantı stringleri .env dosyasına eklenecek.

Extractor 2.0 (extractor.py Güncellemesi):

Mevcut Llama-3-8B yerine Groq üzerindeki Llama-3.3-70B kullanılacak.

Çıktı formatı key-value'dan Subject-Predicate-Object (Üçlüler) yapısına dönüştürülecek.

Veriler Neo4j'ye MERGE komutuyla (tekrarsız) yazılacak.

Context Builder 2.0 (context.py Güncellemesi):

Sadece son mesajlar değil; kullanıcının mesajındaki anahtar kelimelerle Neo4j'de Sub-Graph (Alt Ağ) araması yapılıp prompt'a eklenecek.






FAZ 3: "Beyin" - Agentic Orchestrator ve ReAct Döngüsü
Amaç: Tek seferlik yönlendirme yerine, planlayan ve sonuçları kontrol eden zeka.

Task Decomposition Şeması (orchestrator.py Güncellemesi):

Gemini Flash'ın çıktısı, seninle konuştuğumuz o detaylı JSON şemasına (Tasks, Depends_on, Criticality) dönüştürülecek.

Döngüsel Çalışma (Looping):

api.py içindeki ana chat_endpoint, dag_executor'dan gelen sonuçları alıp "Görev bitti mi?" diye orchestrator'a tekrar soracak bir while döngüsüne alınacak.

Hata Toleransı (Resilience):

Groq anahtarları için "Round Robin" (Sırayla kullanım) yük dengeleme sistemi key_manager.py içine eklenecek.





FAZ 4: "Ses" - Dinamik Modlar ve Persona
Amaç: Her kullanıcı tipine (Ev hanımı, Siyasetçi vb.) uygun iletişim tonu.

Mod Seçici Entegrasyonu (api.py):

Request body'ye mode parametresi eklenecek: Standard, Professional, Sincere, Concise, Creative.

Standard Mod (Adaptive Logic):

Eğer mod Standard seçilirse; orchestrator, Neo4j'deki "User Profile" verisine bakarak tonu kendi belirleyecek.

Synthesizer Güncellemesi (synthesizer.py):

Prompt şablonları bu 5 moda göre güncellenecek.

"Mirroring" (Aynalama) özelliği eklenecek (Kullanıcı kısa yazıyorsa kısa cevap ver).






FAZ 5: "Refleksler" - Proaktif Gözlemci (Observer)
Amaç: Kullanıcı sormadan harekete geçen arka plan zekası.

Observer Modülü (observer.py - Yeni Dosya):

FastAPI BackgroundTasks veya APScheduler kullanılarak periyodik (örn: 15 dakikada bir) çalışan bir job tanımlanacak.

Sinyal Takibi:

Zaman (time_context), Takvim (Tool) ve Neo4j'deki "Bekleyen İşler" taranacak.

Tetikleyici:

Eğer aksiyon gerekiyorsa, Observer sanki kullanıcıymış gibi orchestrator'a "Internal System Message" gönderecek ve kullanıcıya bildirim üretecek.






FAZ 6: "Kalkan" - Güvenlik ve Final Stabilizasyon
Amaç: Aylar sürecek test sürecine girmeden önce sistemi kurşun geçirmez yapmak.

Zarif Çöküş (Graceful Degradation):

Tool'lar hata verirse sistemin çökmemesi, "Alternatif cevap" üretmesi için generator.py içine try-except blokları güçlendirilecek.

Gizlilik İzolasyonu:

Neo4j sorgularına WHERE user_id = $session_id şartı mutlak kural olarak eklenecek.

Logging ve İzleme:

RDR (Routing Decision Record) sistemi, tool kullanımlarını ve maliyetlerini de loglayacak şekilde genişletilecek.