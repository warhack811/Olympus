# Mami AI v4 - Logging & Monitoring Sistemi

Mami AI, production ortamında sorunları hızlı bir şekilde debug edebilmek, performans darboğazlarını tespit edebilmek ve sistem sağlığını izleyebilmek için kapsamlı bir logging ve monitoring sistemi sunar.

## İçindekiler

- [Genel Bakış](#genel-bakış)
- [Kurulum](#kurulum)
- [Konfigürasyon](#konfigürasyon)
- [Bileşenler](#bileşenler)
- [Kullanım](#kullanım)
- [Sorun Giderme](#sorun-giderme)

## Genel Bakış

Logging & Monitoring sistemi aşağıdaki bileşenlerden oluşur:

### Backend Logging
- **JSON Formatter**: Yapılandırılmış log mesajları
- **Request ID Tracking**: Correlation ID ile request takibi
- **Structured Logging**: Tutarlı log formatı

### Frontend Error Tracking
- **Sentry Integration**: Otomatik hata takibi
- **Error Context**: Hata detayları ve browser bilgisi
- **Real-time Reporting**: Hataların anında raporlanması

### Performance Metrics
- **Prometheus**: Metrik toplama ve depolama
- **API Metrics**: Response time, request count, error rate
- **System Metrics**: CPU, memory, disk kullanımı

### Centralized Logging
- **Elasticsearch**: Log depolama ve arama
- **Log Aggregation**: Tüm logların merkezi yerde toplanması
- **Full-text Search**: Log'ları arama ve filtreleme

### Alerting & Notifications
- **Email Alerts**: Kritik sorunlar için e-posta bildirimleri
- **Slack Integration**: Slack kanallarına alert gönderme
- **Alert Escalation**: Cevap yoksa alert'leri escalate etme

### Dashboard & Visualization
- **Grafana**: Real-time dashboard'lar
- **Custom Dashboards**: Özel metrik görselleştirmesi
- **Alert Management**: Alert'leri yönetme ve konfigüre etme

### User Analytics
- **Event Tracking**: Kullanıcı davranışı takibi
- **Batch Processing**: Event'leri batch halinde işleme
- **PII Anonymization**: Kullanıcı privacy'sini koruma

## Kurulum

### Ön Koşullar

- Docker ve Docker Compose
- Python 3.9+
- Node.js 16+
- PostgreSQL (veya mevcut veritabanı)

### 1. Environment Konfigürasyonu

`.env.example` dosyasını `.env` olarak kopyalayın ve gerekli değerleri doldurun:

```bash
cp .env.example .env
```

Aşağıdaki değişkenleri düzenleyin:

```bash
# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=changeme

# Prometheus
PROMETHEUS_URL=http://localhost:9090

# Grafana
GRAFANA_URL=http://localhost:3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# Sentry
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_TO=admin@example.com
```

### 2. Docker Compose ile Hizmetleri Başlatma

```bash
cd docker
docker-compose up -d
```

Bu komut aşağıdaki hizmetleri başlatacaktır:

- **Elasticsearch** (port 9200)
- **Prometheus** (port 9090)
- **Grafana** (port 3000)

### 3. Backend Kurulumu

```bash
# Python bağımlılıklarını yükleyin
pip install -r requirements.txt

# Veritabanı migrasyonlarını çalıştırın
alembic upgrade head

# Backend'i başlatın
python -m uvicorn app.main:app --reload
```

### 4. Frontend Kurulumu

```bash
cd ui-new

# Node bağımlılıklarını yükleyin
npm install

# Frontend'i başlatın
npm run dev
```

## Konfigürasyon

### Elasticsearch Konfigürasyonu

Elasticsearch, tüm log'ları merkezi bir yerde depolar. Günlük index'ler oluşturulur ve 90 gün saklanır.

**Index Adlandırması**: `logs-mami-ai-YYYY.MM.DD`

**Retention Policy**: 90 gün (opsiyonel olarak değiştirilebilir)

```bash
# Elasticsearch'e bağlanın
curl -X GET "localhost:9200/_cat/indices?v"

# Log'ları arayın
curl -X GET "localhost:9200/logs-mami-ai-*/_search?q=error"
```

### Prometheus Konfigürasyonu

Prometheus, API ve sistem metriklerini toplar. Konfigürasyon dosyası `docker/prometheus.yml` konumundadır.

**Scrape Interval**: 15 saniye

**Retention**: 30 gün

**Alert Rules**: `docker/alert_rules.yml` dosyasında tanımlanır

```bash
# Prometheus'a erişin
http://localhost:9090

# Metrikleri sorgulayın
http://localhost:9090/api/v1/query?query=http_requests_total
```

### Grafana Konfigürasyonu

Grafana, Prometheus ve Elasticsearch'ten veri alarak dashboard'lar oluşturur.

**Varsayılan Giriş**: admin / admin

**Data Sources**:
- Prometheus: http://localhost:9090
- Elasticsearch: http://localhost:9200

**Dashboards**:
- API Performance
- Error Rate
- System Metrics
- Top Errors

```bash
# Grafana'ya erişin
http://localhost:3000
```

### Sentry Konfigürasyonu

Sentry, frontend'de oluşan hataları otomatik olarak takip eder.

1. https://sentry.io/ adresine gidin
2. Yeni bir proje oluşturun
3. DSN'yi kopyalayın
4. `.env` dosyasında `VITE_SENTRY_DSN` değişkenini güncelleyin

```bash
VITE_SENTRY_DSN=https://your-key@sentry.io/your-project-id
```

### Slack Konfigürasyonu

Slack, kritik alert'leri belirtilen kanala gönderir.

1. https://api.slack.com/messaging/webhooks adresine gidin
2. Yeni bir Incoming Webhook oluşturun
3. Webhook URL'sini kopyalayın
4. `.env` dosyasında `SLACK_WEBHOOK_URL` değişkenini güncelleyin

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Email Konfigürasyonu

Email, alert'leri belirtilen adrese gönderir.

**Gmail Kullanıyorsanız**:

1. https://myaccount.google.com/apppasswords adresine gidin
2. Uygulama şifresi oluşturun
3. `.env` dosyasında aşağıdaki değişkenleri güncelleyin:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_TO=admin@example.com
```

## Bileşenler

### 1. Backend Logging (`app/core/logger.py`)

Yapılandırılmış JSON log'ları oluşturur ve Elasticsearch'e gönderir.

**Özellikler**:
- JSON formatter
- Request ID tracking
- Structured logging helpers
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Kullanım**:

```python
from app.core.logger import get_logger

logger = get_logger(__name__)

# Basit log
logger.info("İşlem başladı")

# Structured log
logger.info("API isteği alındı", extra={
    "request_id": "123",
    "method": "GET",
    "path": "/api/chat"
})

# Error log
logger.error("Hata oluştu", exc_info=True)
```

### 2. Logging Middleware (`app/main.py`)

Her API isteğini ve yanıtını log'a yazar.

**Özellikler**:
- Request ID oluşturma
- Request/response logging
- Error logging
- Performance timing

### 3. Metrics Collection (`app/core/metrics.py`)

API ve sistem metriklerini toplar.

**Metrikleri**:
- `http_requests_total`: Toplam API isteği sayısı
- `http_request_duration_seconds`: API isteği süresi
- `http_requests_errors_total`: Toplam hata sayısı
- `system_cpu_usage_percent`: CPU kullanımı
- `system_memory_usage_percent`: Memory kullanımı
- `system_disk_usage_percent`: Disk kullanımı

### 4. Health Monitoring (`app/core/health_monitor.py`)

Sistem sağlığını izler ve alert'ler gönderir.

**Kontroller**:
- Database bağlantısı
- Cache (Redis) bağlantısı
- External services
- Disk alanı
- Memory kullanımı

### 5. Frontend Error Tracking (`ui-new/src/lib/errorTracking.ts`)

Frontend'de oluşan hataları Sentry'ye gönderir.

**Özellikler**:
- Global error handler
- Unhandled promise rejection handler
- API error interceptor
- Network error handler

**Kullanım**:

```typescript
import { initializeErrorTracking } from '@/lib/errorTracking';

// Uygulamayı başlatırken
initializeErrorTracking();

// Hata yakalama
try {
  // kod
} catch (error) {
  captureException(error);
}
```

### 6. Analytics (`app/core/analytics.py` ve `ui-new/src/lib/analytics.ts`)

Kullanıcı davranışını takip eder.

**Event'ler**:
- `login`: Kullanıcı giriş yaptı
- `chat_start`: Sohbet başladı
- `message_sent`: Mesaj gönderildi
- `image_generated`: Resim oluşturuldu

**Kullanım**:

```python
from app.core.analytics import track_event

track_event(
    user_id="user123",
    event_type="message_sent",
    metadata={"chat_id": "chat123"}
)
```

```typescript
import { trackEvent } from '@/lib/analytics';

trackEvent('message_sent', {
  chat_id: 'chat123',
  message_length: 100
});
```

### 7. Alerting (`app/core/alerting.py`)

Kritik sorunlar için alert'ler gönderir.

**Alert Kuralları**:
- Error rate %5'i aşarsa
- Response time 5 saniyeyi aşarsa
- Disk alanı %80'i aşarsa
- Memory kullanımı %90'ı aşarsa
- API endpoint'i 5 dakika down olursa

### 8. Log Cleanup (`app/core/log_cleanup.py`)

Eski log'ları otomatik olarak siler.

**Özellikler**:
- Günde bir kere çalışır (gece saatlerinde)
- 90 günden eski log'ları siler
- Silme işleminden önce backup'lar
- Silme işlemini log'a yazar

## Kullanım

### Log'ları Görüntüleme

#### Elasticsearch ile

```bash
# Tüm log'ları listele
curl -X GET "localhost:9200/logs-mami-ai-*/_search?size=100"

# Error log'larını ara
curl -X GET "localhost:9200/logs-mami-ai-*/_search?q=level:ERROR"

# Belirli bir request ID'ye göre ara
curl -X GET "localhost:9200/logs-mami-ai-*/_search?q=request_id:123"
```

#### Grafana ile

1. Grafana'ya gidin: http://localhost:3000
2. "Explore" sekmesine tıklayın
3. Data source olarak Elasticsearch'i seçin
4. Log'ları filtreleyip arayın

### Metrik'leri Görüntüleme

#### Prometheus ile

1. Prometheus'a gidin: http://localhost:9090
2. "Graph" sekmesine tıklayın
3. Metrik adını yazın (örn: `http_requests_total`)
4. "Execute" butonuna tıklayın

#### Grafana ile

1. Grafana'ya gidin: http://localhost:3000
2. Önceden oluşturulmuş dashboard'lardan birini seçin
3. Real-time metrik'leri görüntüleyin

### Alert'leri Yönetme

#### Prometheus Alert Rules

`docker/alert_rules.yml` dosyasında alert kuralları tanımlanır:

```yaml
groups:
  - name: mami_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Yüksek error rate"
```

#### Grafana Alert'leri

1. Grafana'ya gidin
2. "Alerting" sekmesine tıklayın
3. Yeni alert kuralı oluşturun
4. Notification channel'ı seçin (Email, Slack, vb.)

### Event'leri Takip Etme

#### Backend Analytics

```python
from app.core.analytics import track_event

# Event'i takip et
track_event(
    user_id="user123",
    event_type="chat_start",
    metadata={"model": "gpt-4"}
)
```

#### Frontend Analytics

```typescript
import { trackEvent } from '@/lib/analytics';

// Event'i takip et
trackEvent('image_generated', {
  model: 'flux',
  size: '1024x1024'
});
```

## Sorun Giderme

### Elasticsearch Bağlantı Hatası

```bash
# Elasticsearch'in çalışıp çalışmadığını kontrol edin
curl -X GET "localhost:9200/"

# Docker container'ını kontrol edin
docker ps | grep elasticsearch

# Log'ları görüntüleyin
docker logs <container_id>
```

### Prometheus Metrikleri Toplanmıyor

```bash
# Prometheus'a erişin
http://localhost:9090/targets

# Scrape status'unu kontrol edin
# Eğer "DOWN" ise, backend'in çalışıp çalışmadığını kontrol edin
```

### Grafana Dashboard'ları Boş

```bash
# Data source'ları kontrol edin
# Grafana > Configuration > Data Sources

# Prometheus ve Elasticsearch'in erişilebilir olduğundan emin olun
```

### Sentry Hataları Alınmıyor

```bash
# DSN'nin doğru olduğundan emin olun
# .env dosyasında VITE_SENTRY_DSN değişkenini kontrol edin

# Frontend console'unda hata olup olmadığını kontrol edin
# Browser developer tools > Console
```

### Slack Alert'leri Gönderilmiyor

```bash
# Webhook URL'sinin doğru olduğundan emin olun
# .env dosyasında SLACK_WEBHOOK_URL değişkenini kontrol edin

# Backend log'larında hata olup olmadığını kontrol edin
```

### Email Alert'leri Gönderilmiyor

```bash
# SMTP konfigürasyonunu kontrol edin
# .env dosyasında SMTP_* değişkenlerini kontrol edin

# Gmail kullanıyorsanız, uygulama şifresi oluşturduğundan emin olun
# https://myaccount.google.com/apppasswords

# Backend log'larında hata olup olmadığını kontrol edin
```

## Performans İpuçları

### Log Boyutunu Azaltma

- Gereksiz context bilgilerini log'lamayın
- Sensitive data'yı mask'leyin
- Log level'ını production'da INFO veya WARNING olarak ayarlayın

### Metrik Toplama Performansı

- Scrape interval'ını artırın (varsayılan: 15 saniye)
- Gereksiz metrik'leri devre dışı bırakın
- Retention süresi'ni azaltın (varsayılan: 30 gün)

### Elasticsearch Performansı

- Index'leri optimize edin
- Eski index'leri silin
- Shard sayısını ayarlayın

## Güvenlik

### Sensitive Data Masking

Log'larda sensitive data'yı mask'lemek için:

```python
from app.core.logger import mask_sensitive_data

# Otomatik masking
logger.info("API key: " + mask_sensitive_data("sk_live_123456"))
```

### Access Control

- Elasticsearch'e erişimi kısıtlayın (firewall, VPN)
- Prometheus'a erişimi kısıtlayın
- Grafana'da kullanıcı rolleri tanımlayın
- Sentry'de team'ler ve permission'ları ayarlayın

### Data Privacy

- PII data'yı anonymize edin
- GDPR uyumluluğunu sağlayın
- Log retention policy'sini belirleyin
- Backup'ları şifreleyin

## Kaynaklar

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Sentry Documentation](https://docs.sentry.io/)
- [Slack API Documentation](https://api.slack.com/)

## Destek

Sorunlar veya sorularınız varsa, lütfen GitHub issues'ı kullanın veya ekiple iletişime geçin.

---

**Son Güncelleme**: Ocak 2026
**Versiyon**: 1.0
