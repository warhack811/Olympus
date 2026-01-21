# Docker Production Readiness - Gereksinimler Belgesi

## Giriş

Bu belge, Mami AI projesinin Docker ortamında (local development ve production) sorunsuz çalışmasını sağlamak için gerekli tüm gereksinimleri tanımlar. Proje, FastAPI backend, React frontend, ve çok sayıda harici servisi (Redis, Neo4j, Qdrant, Elasticsearch, Prometheus, Grafana) içermektedir.

Hedef:
- Local development ortamında Docker Desktop ile tam işlevsellik
- Production ortamında GitHub Actions + Server ile tutarlı davranış
- Tüm bağımlılıkların uyumluluğu ve sürüm tutarlılığı
- CI/CD pipeline'ının hazır olması

## Sözlük

- **Docker Compose**: Çok konteynerli uygulamaları tanımlamak ve çalıştırmak için araç
- **Multi-stage Build**: Dockerfile'da birden fazla FROM kullanarak optimize edilmiş imaj oluşturma
- **Health Check**: Konteyner sağlığını periyodik olarak kontrol eden mekanizma
- **Environment Variable**: Ortam değişkeni (.env dosyasından veya sistem ortamından okunur)
- **Volume**: Docker konteynerinde kalıcı veri depolama
- **Network**: Docker konteynerler arasında iletişim sağlayan ağ
- **CI/CD**: Continuous Integration / Continuous Deployment - otomatik test ve deployment
- **Hybrid Architecture**: CORE (bulut) ve WORKER (yerel GPU) modları
- **Atlas Memory System**: Neo4j (Graph), Qdrant (Vector), Redis (Cache) kombinasyonu
- **LLM Provider**: Groq, Gemini, Ollama gibi dil modeli sağlayıcıları
- **Fallback Chain**: Hata durumunda sırasıyla denenen alternatif modeller

## Gereksinimler

### Gereksinim 1: Docker İmajı Uyumluluğu

**Kullanıcı Hikayesi:** Bir geliştirici olarak, Docker imajının tüm Python bağımlılıklarını doğru şekilde içermesini istiyorum, böylece konteyner başladığında hiçbir eksik kütüphane hatası almayım.

#### Kabul Kriterleri

1. WHEN Docker imajı build edildiğinde, THE Build Process SHALL tüm requirements.txt bağımlılıklarını başarıyla yüklesin
2. WHEN Docker imajı build edildiğinde, THE Multi-stage Build SHALL builder stage'de wheel'ları oluşturarak runtime imajını optimize etsin
3. WHEN Docker konteyner başlatıldığında, THE Container SHALL tüm Python modüllerini başarıyla import edesin (import hatası olmadan)
4. WHEN Docker imajı build edildiğinde, THE Build Process SHALL sistem bağımlılıklarını (build-essential, curl) doğru şekilde yüklesin
5. WHEN Docker konteyner çalıştığında, THE Container SHALL non-root kullanıcı (mami) ile çalışsın (güvenlik için)

### Gereksinim 2: Ortam Değişkenleri Tutarlılığı

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, .env dosyasındaki tüm ortam değişkenlerinin Docker konteynerinde doğru şekilde okunmasını ve uygulanmasını istiyorum, böylece local ve production ortamları tutarlı olsun.

#### Kabul Kriterleri

1. WHEN Docker konteyner başlatıldığında, THE Container SHALL .env dosyasından tüm ortam değişkenlerini okumuş olsun
2. WHEN app/config.py çalıştırıldığında, THE Settings Class SHALL Pydantic BaseSettings kullanarak ortam değişkenlerini validasyon ile yüklesin
3. WHEN ortam değişkeni tanımlanmadığında, THE Settings Class SHALL varsayılan değerleri kullanarak fallback yapsin
4. WHEN REDIS_URL ortam değişkeni tanımlandığında, THE Settings Class SHALL bunu kullansin, aksi takdirde REDIS_HOST, REDIS_PORT, REDIS_PASSWORD'den URL oluştursun
5. WHEN Docker konteyner başlatıldığında, THE Container SHALL PYTHONUNBUFFERED=1 ile çalışsın (log'lar gerçek zamanda görünsün)

### Gereksinim 3: Multi-Container Orchestration

**Kullanıcı Hikayesi:** Bir sistem mimarı olarak, Docker Compose ile tüm servislerin (API, Worker, Frontend, Elasticsearch, Prometheus, Grafana) koordineli şekilde başlamasını ve iletişim kurmasını istiyorum.

#### Kabul Kriterleri

1. WHEN docker-compose up komutu çalıştırıldığında, THE Docker Compose SHALL tüm servisleri (mami-ai, mami-worker, mami-ui, elasticsearch, prometheus, grafana) başlatsin
2. WHEN mami-ai servisi başlatıldığında, THE Service SHALL mami-network ağında çalışsin ve diğer servisler tarafından erişilebilir olsun
3. WHEN mami-ui servisi başlatıldığında, THE Service SHALL VITE_API_URL=http://mami-ai:8000 ortam değişkeni ile çalışsin (container adı ile DNS çözümlemesi)
4. WHEN mami-worker servisi başlatıldığında, THE Service SHALL mami-ai servisine bağlı olsun (depends_on) ve başlamadan önce API'nin hazır olmasını beklesin
5. WHEN docker-compose down komutu çalıştırıldığında, THE Docker Compose SHALL tüm konteynerları ve ağları temizlesin

### Gereksinim 4: Health Check Mekanizması

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, her servisin sağlığını periyodik olarak kontrol etmek istiyorum, böylece başarısız servisler otomatik olarak yeniden başlasın.

#### Kabul Kriterleri

1. WHEN mami-ai servisi çalıştığında, THE Health Check SHALL her 30 saniyede bir /health endpoint'ini kontrol etsin
2. WHEN /health endpoint'i başarısız olduğunda, THE Health Check SHALL 3 kez retry yapsin ve sonra konteyner'ı unhealthy olarak işaretlesin
3. WHEN elasticsearch servisi çalıştığında, THE Health Check SHALL _cluster/health endpoint'ini kontrol etsin
4. WHEN prometheus servisi çalıştığında, THE Health Check SHALL /-/healthy endpoint'ini kontrol etsin
5. WHEN grafana servisi çalıştığında, THE Health Check SHALL /api/health endpoint'ini kontrol etsin

### Gereksinim 5: Volume ve Veri Kalıcılığı

**Kullanıcı Hikayesi:** Bir geliştirici olarak, Docker konteyner yeniden başlatıldığında veri (logs, images, database) kaybolmamasını istiyorum.

#### Kabul Kriterleri

1. WHEN Docker konteyner yeniden başlatıldığında, THE Volumes SHALL ./data ve ./logs dizinlerini host'ta kalıcı tutsin
2. WHEN elasticsearch servisi çalıştığında, THE Volume SHALL elasticsearch_data adında named volume kullansin
3. WHEN prometheus servisi çalıştığında, THE Volume SHALL prometheus_data adında named volume kullansin
4. WHEN grafana servisi çalıştığında, THE Volume SHALL grafana_data adında named volume kullansin
5. WHEN docker-compose down komutu çalıştırıldığında, THE Named Volumes SHALL silinmemesi için korunmuş olsun (docker volume ls ile görülebilsin)

### Gereksinim 6: Network İzolasyonu ve İletişim

**Kullanıcı Hikayesi:** Bir sistem mimarı olarak, Docker konteynerlerinin kendi ağında (mami-network) izole şekilde çalışmasını ve sadece gerekli portları expose etmesini istiyorum.

#### Kabul Kriterleri

1. WHEN Docker Compose başlatıldığında, THE Network SHALL mami-network adında bridge network oluşturulsun
2. WHEN mami-ai servisi çalıştığında, THE Service SHALL sadece 8000 portunu expose etsin (host'ta 8000:8000)
3. WHEN mami-ui servisi çalıştığında, THE Service SHALL sadece 5173 portunu expose etsin (host'ta 5173:5173)
4. WHEN elasticsearch servisi çalıştığında, THE Service SHALL 9200 ve 9300 portlarını expose etsin
5. WHEN mami-ui servisi mami-ai'ye erişmek istediğinde, THE Network SHALL container adı (mami-ai) ile DNS çözümlemesi yapsin

### Gereksinim 7: Frontend Build ve Vite Dev Server

**Kullanıcı Hikayesi:** Bir frontend geliştirici olarak, Docker'da Vite dev server'ının hot reload ile çalışmasını istiyorum, böylece dosya değişiklikleri anında yansısın.

#### Kabul Kriterleri

1. WHEN mami-ui servisi başlatıldığında, THE Service SHALL npm install çalıştırarak bağımlılıkları yüklesin
2. WHEN mami-ui servisi başlatıldığında, THE Service SHALL npm run dev -- --host komutu ile Vite dev server'ını başlatsin
3. WHEN Vite dev server çalıştığında, THE Server SHALL 5173 portunda erişilebilir olsun
4. WHEN TypeScript dosyası değiştirildiğinde, THE Dev Server SHALL hot reload yapsin (sayfa yenilenmeden güncellenmesi)
5. WHEN node_modules volume'ü tanımlandığında, THE Volume SHALL /app/node_modules'u host'tan izole etsin (performance için)

### Gereksinim 8: Python Bağımlılıkları Uyumluluğu

**Kullanıcı Hikayesi:** Bir backend geliştirici olarak, requirements.txt'teki tüm Python paketlerinin belirtilen sürümlerde uyumlu olmasını istiyorum.

#### Kabul Kriterleri

1. WHEN requirements.txt okunduğunda, THE File SHALL FastAPI 0.115.0, uvicorn 0.30.3, pydantic >=2.0.0 içersin
2. WHEN requirements.txt okunduğunda, THE File SHALL SQLModel, Neo4j, Qdrant, Redis, Groq, Gemini bağımlılıklarını içersin
3. WHEN Docker imajı build edildiğinde, THE Build Process SHALL pip wheel kullanarak wheel'ları oluştursun (hız için)
4. WHEN Docker imajı build edildiğinde, THE Build Process SHALL --no-cache-dir flag'i kullansin (imaj boyutunu azaltmak için)
5. WHEN requirements.txt'te sürüm çakışması olduğunda, THE Build Process SHALL hata vermesi ve build'i başarısız kılması gerekir

### Gereksinim 9: Node.js Bağımlılıkları Uyumluluğu

**Kullanıcı Hikayesi:** Bir frontend geliştirici olarak, package.json'daki tüm npm paketlerinin React 19, TypeScript, Vite ile uyumlu olmasını istiyorum.

#### Kabul Kriterleri

1. WHEN package.json okunduğunda, THE File SHALL React 19.2.0, TypeScript 5.9.3, Vite 7.2.4 içersin
2. WHEN package.json okunduğunda, THE File SHALL TailwindCSS 4.1.18, Zustand 5.0.9, React Router 6.30.2 içersin
3. WHEN npm install çalıştırıldığında, THE Package Manager SHALL package-lock.json'ı kullanarak deterministic kurulum yapsin
4. WHEN npm run build çalıştırıldığında, THE Build Process SHALL TypeScript'i derlesin ve Vite ile optimize edilmiş bundle oluştursun
5. WHEN npm run dev çalıştırıldığında, THE Dev Server SHALL hot reload ve source maps ile çalışsin

### Gereksinim 10: Elasticsearch ve Logging Entegrasyonu

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, tüm uygulama loglarının Elasticsearch'e gönderilmesini ve Kibana/Grafana'da görüntülenmesini istiyorum.

#### Kabul Kriterleri

1. WHEN elasticsearch servisi başlatıldığında, THE Service SHALL single-node cluster modunda çalışsin
2. WHEN elasticsearch servisi başlatıldığında, THE Service SHALL xpack.security.enabled=false ile çalışsin (geliştirme için)
3. WHEN elasticsearch servisi başlatıldığında, THE Service SHALL ES_JAVA_OPTS=-Xms512m -Xmx512m ile bellek sınırı koyulsun
4. WHEN FastAPI uygulaması çalıştığında, THE Application SHALL logları Elasticsearch'e göndermesi için yapılandırılmış olsun
5. WHEN Elasticsearch health check başarısız olduğunda, THE Container SHALL unhealthy olarak işaretlenmesi ve yeniden başlatılması gerekir

### Gereksinim 11: Prometheus ve Metrik Toplama

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, FastAPI uygulamasının metriklerini (request count, latency, errors) Prometheus'a göndermesini istiyorum.

#### Kabul Kriterleri

1. WHEN prometheus servisi başlatıldığında, THE Service SHALL ./docker/prometheus.yml konfigürasyonunu okumuş olsun
2. WHEN prometheus servisi başlatıldığında, THE Service SHALL ./docker/alert_rules.yml alert kurallarını okumuş olsun
3. WHEN prometheus servisi çalıştığında, THE Service SHALL 30 gün veri tutsin (--storage.tsdb.retention.time=30d)
4. WHEN FastAPI uygulaması çalıştığında, THE Application SHALL /metrics endpoint'ini expose etsin (Prometheus scraping için)
5. WHEN prometheus health check başarısız olduğunda, THE Container SHALL unhealthy olarak işaretlenmesi ve yeniden başlatılması gerekir

### Gereksinim 12: Grafana Dashboard ve Görselleştirme

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, Grafana'da Prometheus metriklerini görselleştiren dashboard'lar görmek istiyorum.

#### Kabul Kriterleri

1. WHEN grafana servisi başlatıldığında, THE Service SHALL admin/admin kullanıcı ile başlatılsin
2. WHEN grafana servisi başlatıldığında, THE Service SHALL ./docker/grafana/provisioning konfigürasyonlarını okumuş olsun
3. WHEN grafana servisi başlatıldığında, THE Service SHALL Prometheus data source'u otomatik olarak eklemesi gerekir
4. WHEN grafana servisi çalıştığında, THE Service SHALL 3000 portunda erişilebilir olsun
5. WHEN grafana health check başarısız olduğunda, THE Container SHALL unhealthy olarak işaretlenmesi ve yeniden başlatılması gerekir

### Gereksinim 13: GitHub Actions CI/CD Pipeline

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, GitHub'a push yapıldığında otomatik olarak Docker imajı build edilmesini, test edilmesini ve registry'ye push edilmesini istiyorum.

#### Kabul Kriterleri

1. WHEN GitHub'a push yapıldığında, THE GitHub Actions SHALL .github/workflows/docker-build.yml workflow'unu çalıştırsin
2. WHEN workflow çalıştığında, THE Workflow SHALL Docker imajını build etsin ve test etsin
3. WHEN workflow çalıştığında, THE Workflow SHALL Docker imajını Docker Hub veya GitHub Container Registry'ye push etsin
4. WHEN workflow çalıştığında, THE Workflow SHALL Python ve Node.js bağımlılıklarını test etsin
5. WHEN workflow başarısız olduğunda, THE GitHub SHALL PR'a fail status göstermesi gerekir

### Gereksinim 14: Production Deployment Hazırlığı

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, Docker imajının production sunucusunda (Linux VM) sorunsuz çalışmasını istiyorum.

#### Kabul Kriterleri

1. WHEN Docker imajı production sunucusunda çalıştırıldığında, THE Container SHALL tüm ortam değişkenlerini production .env dosyasından okumuş olsun
2. WHEN Docker imajı production sunucusunda çalıştırıldığında, THE Container SHALL restart: unless-stopped policy'si ile çalışsin (otomatik yeniden başlatma)
3. WHEN Docker imajı production sunucusunda çalıştırıldığında, THE Container SHALL health check'i geçmesi gerekir
4. WHEN Docker imajı production sunucusunda çalıştırıldığında, THE Container SHALL non-root kullanıcı (mami) ile çalışsin
5. WHEN production sunucusunda docker-compose up -d komutu çalıştırıldığında, THE Services SHALL background'da çalışsin ve otomatik yeniden başlasın

### Gereksinim 15: Hybrid Architecture Uyumluluğu

**Kullanıcı Hikayesi:** Bir sistem mimarı olarak, CORE (bulut) ve WORKER (yerel GPU) modlarının Docker'da sorunsuz çalışmasını istiyorum.

#### Kabul Kriterleri

1. WHEN NODE_MODE=CORE ortam değişkeni ayarlandığında, THE Application SHALL bulut modunda çalışsin (API sunucu)
2. WHEN NODE_MODE=WORKER ortam değişkeni ayarlandığında, THE Application SHALL worker modunda çalışsin (görsel işleme)
3. WHEN mami-worker servisi çalıştığında, THE Service SHALL python -m app.image.worker_local komutu ile başlatılsin
4. WHEN mami-worker servisi çalıştığında, THE Service SHALL mami-ai servisine bağlı olsun ve API'ye veri göndermesi gerekir
5. WHEN INTERNAL_UPLOAD_TOKEN ortam değişkeni ayarlandığında, THE Worker SHALL bu token'ı kullanarak API'ye güvenli şekilde veri göndermesi gerekir

### Gereksinim 16: LLM Provider Fallback Mekanizması

**Kullanıcı Hikayesi:** Bir backend geliştirici olarak, Groq API başarısız olduğunda otomatik olarak Gemini'ye fallback yapmasını istiyorum.

#### Kabul Kriterleri

1. WHEN Groq API çağrısı başarısız olduğunda, THE Application SHALL FALLBACK_CHAINS konfigürasyonunu kullanarak alternatif modele geçmesi gerekir
2. WHEN Gemini API çağrısı başarısız olduğunda, THE Application SHALL Ollama yerel modeline fallback yapsin
3. WHEN get_groq_api_keys() metodu çağrıldığında, THE Method SHALL tüm geçerli Groq API anahtarlarını liste olarak döndürmesi gerekir
4. WHEN get_gemini_api_keys() metodu çağrıldığında, THE Method SHALL tüm geçerli Gemini API anahtarlarını liste olarak döndürmesi gerekir
5. WHEN Docker konteyner başlatıldığında, THE Container SHALL tüm LLM provider API anahtarlarını .env dosyasından okumuş olsun

### Gereksinim 17: Redis Bağlantı Yönetimi

**Kullanıcı Hikayesi:** Bir backend geliştirici olarak, Redis'e bağlantının farklı database indeksleri ile yönetilmesini istiyorum.

#### Kabul Kriterleri

1. WHEN get_redis_url(db=0) metodu çağrıldığında, THE Method SHALL Celery Task Queue için Redis URL'sini döndürmesi gerekir
2. WHEN get_redis_url(db=1) metodu çağrıldığında, THE Method SHALL Working Memory için Redis URL'sini döndürmesi gerekir
3. WHEN REDIS_DSN ortam değişkeni ayarlandığında, THE Settings SHALL bunu kullansin (Upstash gibi managed Redis için)
4. WHEN REDIS_HOST, REDIS_PORT, REDIS_PASSWORD ortam değişkenleri ayarlandığında, THE Settings SHALL bunlardan URL oluştursun
5. WHEN Docker konteyner başlatıldığında, THE Container SHALL Redis'e bağlanabilmesi gerekir (health check)

### Gereksinim 18: Veri Tabanı Migrasyonları

**Kullanıcı Hikayesi:** Bir backend geliştirici olarak, Docker konteyner başlatıldığında Alembic migrasyonlarının otomatik olarak çalışmasını istiyorum.

#### Kabul Kriterleri

1. WHEN Docker konteyner başlatıldığında, THE Container SHALL app/core/database.py'daki init_database_with_defaults() fonksiyonunu çalıştırsin
2. WHEN init_database_with_defaults() çalıştırıldığında, THE Function SHALL Alembic migrasyonlarını uygulaması gerekir
3. WHEN DATABASE_URL ortam değişkeni tanımlanmadığında, THE Settings SHALL sqlite:///data/app.db kullansin
4. WHEN Docker konteyner başlatıldığında, THE Container SHALL data/ dizinini oluşturmuş olsun
5. WHEN Alembic migrasyonu başarısız olduğunda, THE Container SHALL startup hatası vermesi ve başarısız olması gerekir

### Gereksinim 19: CORS ve Security Headers

**Kullanıcı Hikayesi:** Bir backend geliştirici olarak, CORS ayarlarının Docker'da doğru şekilde yapılandırılmasını istiyorum.

#### Kabul Kriterleri

1. WHEN FastAPI uygulaması başlatıldığında, THE Application SHALL CORS_ORIGINS ortam değişkenini okumuş olsun
2. WHEN get_cors_origins_list() metodu çağrıldığında, THE Method SHALL CORS_ORIGINS string'ini virgülle ayrılmış liste olarak parse etmesi gerekir
3. WHEN frontend (http://localhost:5173) API'ye istek gönderdiğinde, THE API SHALL CORS headers'ı döndürmesi gerekir
4. WHEN production ortamında API çağrısı yapıldığında, THE API SHALL production domain'ini CORS_ORIGINS'e eklemesi gerekir
5. WHEN Docker konteyner başlatıldığında, THE Container SHALL CORS_ORIGINS ortam değişkenini .env dosyasından okumuş olsun

### Gereksinim 20: Logging ve Monitoring Entegrasyonu

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, tüm uygulama loglarının merkezi olarak toplanmasını ve Elasticsearch'te aranabilir olmasını istiyorum.

#### Kabul Kriterleri

1. WHEN FastAPI uygulaması çalıştığında, THE Application SHALL app/core/logger.py'daki get_logger() fonksiyonunu kullanarak log'ları oluştursun
2. WHEN log oluşturulduğunda, THE Logger SHALL log'u stdout'a yazsin (Docker tarafından toplanabilmesi için)
3. WHEN log oluşturulduğunda, THE Logger SHALL log'u Elasticsearch'e göndermesi gerekir (eğer yapılandırılmışsa)
4. WHEN Docker konteyner çalıştığında, THE Container SHALL PYTHONUNBUFFERED=1 ile çalışsin (log'lar gerçek zamanda görünsün)
5. WHEN Prometheus scraping yapıldığında, THE Application SHALL /metrics endpoint'ini expose etmesi gerekir

### Gereksinim 21: Proje Temizliği ve Çöp Dosya Yönetimi

**Kullanıcı Hikayesi:** Bir DevOps mühendisi olarak, Docker'a geçmeden önce projeyi temizlemek istiyorum, böylece Docker imajı boyutu minimize edilsin ve proje yapısı daha temiz olsun.

#### Kabul Kriterleri

1. WHEN proje temizliği yapıldığında, THE Cleanup Process SHALL tüm eski dokümantasyon dosyalarını (FAZE_*.md, DOCKER_*.md vb.) silin
2. WHEN proje temizliği yapıldığında, THE Cleanup Process SHALL tüm yedek klasörlerini (backups/, _ui_backup/) silin
3. WHEN proje temizliği yapıldığında, THE Cleanup Process SHALL tüm test debug dosyalarını (check_*.py, debug_*.py vb.) silin
4. WHEN proje temizliği yapıldığında, THE Cleanup Process SHALL node_modules/ ve .venv/ klasörlerini silin (Docker'da yeniden oluşturulacak)
5. WHEN proje temizliği yapıldığında, THE Cleanup Process SHALL Docker imajı boyutunu %71 azaltması gerekir (~1.55 GB → ~450 MB)
6. WHEN proje temizliği yapıldığında, THE Cleanup Process SHALL .gitignore ve .dockerignore dosyalarını güncellemesi gerekir
7. WHEN proje temizliği yapıldığında, THE Cleanup Process SHALL Git commit yapması gerekir: "chore: cleanup project for Docker production readiness"

