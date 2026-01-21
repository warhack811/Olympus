# Logging & Monitoring Infrastructure Setup

Bu dokümantasyon, Mami AI'ın logging ve monitoring infrastructure'ını Docker Compose ile kurulumunu açıklar.

## Genel Bakış

Logging & Monitoring sistemi aşağıdaki bileşenlerden oluşur:

- **Elasticsearch**: Merkezi log depolama ve arama
- **Prometheus**: Metrik toplama ve depolama
- **Grafana**: Metrik görselleştirme ve dashboard
- **Sentry**: Frontend error tracking (opsiyonel)

## Kurulum

### 1. Environment Konfigürasyonu

`.env` dosyasını `.env.example` dosyasından kopyalayın ve gerekli değerleri doldurun:

```bash
cp .env.example .env
```

Aşağıdaki environment variable'ları ayarlayın:

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

# Sentry (opsiyonel)
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Slack (opsiyonel)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email (opsiyonel)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_TO=admin@example.com
```

### 2. Docker Compose Başlatma

Tüm servisleri başlatmak için:

```bash
docker-compose up -d
```

Servislerin durumunu kontrol etmek için:

```bash
docker-compose ps
```

### 3. Servislere Erişim

Kurulum tamamlandıktan sonra aşağıdaki URL'lere erişebilirsiniz:

- **Elasticsearch**: http://localhost:9200
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Elasticsearch

### Özellikler

- Merkezi log depolama
- Full-text search
- Log retention policy (90 gün)
- Gzip sıkıştırma

### Log Index'i Oluşturma

```bash
curl -X PUT "localhost:9200/logs-mami-ai-$(date +%Y.%m.%d)" \
  -H 'Content-Type: application/json' \
  -d '{
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "timestamp": { "type": "date" },
        "level": { "type": "keyword" },
        "module": { "type": "keyword" },
        "message": { "type": "text" },
        "context": { "type": "object" }
      }
    }
  }'
```

### Log Sorgulama

```bash
curl -X GET "localhost:9200/logs-mami-ai-*/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": {
        "message": "error"
      }
    }
  }'
```

## Prometheus

### Özellikler

- Metrik toplama (15 saniye aralıklarla)
- Alert kuralları (kapsamlı sistem ve performans alertleri)
- 30 gün retention policy
- Otomatik scrape mekanizması

### Konfigürasyon Dosyaları

- `docker/prometheus.yml`: Ana konfigürasyon
  - Global ayarlar (scrape interval, evaluation interval)
  - Scrape konfigürasyonları (mami-ai, elasticsearch, prometheus)
  - Alert rules dosyası referansı
  
- `docker/alert_rules.yml`: Alert kuralları
  - API Performance Alerts (error rate, response time)
  - System Resource Alerts (disk, memory, CPU)
  - Service Availability Alerts (endpoint down, service health)
  - Database Alerts (connection pool, query time)
  - Cache Alerts (hit rate)
  - Queue Alerts (request queue length)
  - Error Tracking Alerts (Sentry error rate)

### Retention Policy

Prometheus metrikleri 30 gün boyunca saklanır. Bu ayar `docker-compose.yml`'de yapılandırılmıştır:

```yaml
command:
  - "--storage.tsdb.retention.time=30d"
```

Retention policy'sini değiştirmek için `docker-compose.yml`'de `--storage.tsdb.retention.time` parametresini güncelleyin.

### Metriklere Erişim

Prometheus UI'ında (http://localhost:9090) aşağıdaki metrikleri sorgulayabilirsiniz:

```promql
# API request rate
rate(http_requests_total[5m])

# API error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# API response time (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# System CPU usage
1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))

# System memory usage
1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)

# Disk usage
1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)
```

### Alert Kuralları Detayları

#### API Performance Alerts

1. **HighErrorRate**: Error rate %5'i aşarsa (5 dakika boyunca)
   - Severity: Critical
   - Açıklama: API'de yüksek hata oranı tespit edildi

2. **HighResponseTime**: 95th percentile response time 5 saniyeyi aşarsa (5 dakika boyunca)
   - Severity: Warning
   - Açıklama: API response time'ı yüksek

#### System Resource Alerts

3. **HighDiskUsage**: Disk alanı %80'i aşarsa (5 dakika boyunca)
   - Severity: Warning
   - Açıklama: Disk alanı tükeniyor

4. **HighMemoryUsage**: Memory kullanımı %90'ı aşarsa (5 dakika boyunca)
   - Severity: Warning
   - Açıklama: Memory kullanımı yüksek

5. **HighCPUUsage**: CPU kullanımı %85'i aşarsa (5 dakika boyunca)
   - Severity: Warning
   - Açıklama: CPU kullanımı yüksek

#### Service Availability Alerts

6. **APIEndpointDown**: API endpoint down (5 dakika boyunca)
   - Severity: Critical
   - Açıklama: Mami AI API erişilemez

7. **ElasticsearchDown**: Elasticsearch down (5 dakika boyunca)
   - Severity: Critical
   - Açıklama: Elasticsearch erişilemez

8. **PrometheusDown**: Prometheus down (5 dakika boyunca)
   - Severity: Critical
   - Açıklama: Prometheus erişilemez

9. **RedisDown**: Redis down (5 dakika boyunca)
   - Severity: Critical
   - Açıklama: Redis erişilemez

#### Database Alerts

10. **DatabaseConnectionPoolExhausted**: Connection pool %80'i aşarsa (5 dakika boyunca)
    - Severity: Warning
    - Açıklama: Database connection pool tükeniyor

11. **HighDatabaseQueryTime**: 95th percentile query time 1 saniyeyi aşarsa (5 dakika boyunca)
    - Severity: Warning
    - Açıklama: Database query time'ı yüksek

#### Cache Alerts

12. **LowCacheHitRate**: Cache hit rate %50'nin altına düşerse (10 dakika boyunca)
    - Severity: Warning
    - Açıklama: Cache hit rate düşük

#### Queue Alerts

13. **HighRequestQueueLength**: Request queue 100'ü aşarsa (5 dakika boyunca)
    - Severity: Warning
    - Açıklama: Request queue uzunluğu yüksek

#### Error Tracking Alerts

14. **HighSentryErrorRate**: Sentry error rate saniye başına 10'u aşarsa (5 dakika boyunca)
    - Severity: Warning
    - Açıklama: Frontend error rate yüksek

### Scrape Konfigürasyonları

Prometheus aşağıdaki hedefleri monitor eder:

1. **prometheus**: Prometheus kendisini monitor eder (localhost:9090)
2. **mami-ai**: Mami AI backend uygulaması (mami-ai:8000)
3. **elasticsearch**: Elasticsearch (elasticsearch:9200)

Her scrape konfigürasyonu 15 saniye aralıklarla çalışır ve 10 saniye timeout'a sahiptir.

## Grafana

### Özellikler

- Metrik görselleştirme
- Dashboard'lar
- Alert'ler
- Veri kaynakları (Prometheus, Elasticsearch)

### Veri Kaynakları

Grafana otomatik olarak aşağıdaki veri kaynaklarını yükler:

- **Prometheus**: http://prometheus:9090
- **Elasticsearch**: http://elasticsearch:9200

### Dashboard'lar

Aşağıdaki dashboard'lar otomatik olarak yüklenir:

- **API Performance Dashboard**: API response time, error rate, request rate

### Custom Dashboard Oluşturma

1. Grafana UI'ında (http://localhost:3000) oturum açın
2. "+" butonuna tıklayın ve "Dashboard" seçin
3. Panel ekleyin ve Prometheus veya Elasticsearch'ten veri seçin
4. Dashboard'u kaydedin

## Alert Kuralları

Aşağıdaki alert kuralları otomatik olarak yapılandırılır ve `docker/alert_rules.yml` dosyasında tanımlanmıştır:

### API Performance Alerts

1. **HighErrorRate**
   - **Koşul**: Error rate %5'i aşarsa
   - **Süre**: 5 dakika
   - **Severity**: Critical
   - **Açıklama**: API'de yüksek hata oranı tespit edildi

2. **HighResponseTime**
   - **Koşul**: 95th percentile response time 5 saniyeyi aşarsa
   - **Süre**: 5 dakika
   - **Severity**: Warning
   - **Açıklama**: API response time'ı yüksek

### System Resource Alerts

3. **HighDiskUsage**
   - **Koşul**: Disk alanı %80'i aşarsa
   - **Süre**: 5 dakika
   - **Severity**: Warning
   - **Açıklama**: Disk alanı tükeniyor

4. **HighMemoryUsage**
   - **Koşul**: Memory kullanımı %90'ı aşarsa
   - **Süre**: 5 dakika
   - **Severity**: Warning
   - **Açıklama**: Memory kullanımı yüksek

5. **HighCPUUsage**
   - **Koşul**: CPU kullanımı %85'i aşarsa
   - **Süre**: 5 dakika
   - **Severity**: Warning
   - **Açıklama**: CPU kullanımı yüksek

### Service Availability Alerts

6. **APIEndpointDown**
   - **Koşul**: API endpoint down
   - **Süre**: 5 dakika
   - **Severity**: Critical
   - **Açıklama**: Mami AI API erişilemez

7. **ElasticsearchDown**
   - **Koşul**: Elasticsearch down
   - **Süre**: 5 dakika
   - **Severity**: Critical
   - **Açıklama**: Elasticsearch erişilemez

8. **PrometheusDown**
   - **Koşul**: Prometheus down
   - **Süre**: 5 dakika
   - **Severity**: Critical
   - **Açıklama**: Prometheus erişilemez

9. **RedisDown**
   - **Koşul**: Redis down
   - **Süre**: 5 dakika
   - **Severity**: Critical
   - **Açıklama**: Redis erişilemez

### Database Alerts

10. **DatabaseConnectionPoolExhausted**
    - **Koşul**: Connection pool %80'i aşarsa
    - **Süre**: 5 dakika
    - **Severity**: Warning
    - **Açıklama**: Database connection pool tükeniyor

11. **HighDatabaseQueryTime**
    - **Koşul**: 95th percentile query time 1 saniyeyi aşarsa
    - **Süre**: 5 dakika
    - **Severity**: Warning
    - **Açıklama**: Database query time'ı yüksek

### Cache Alerts

12. **LowCacheHitRate**
    - **Koşul**: Cache hit rate %50'nin altına düşerse
    - **Süre**: 10 dakika
    - **Severity**: Warning
    - **Açıklama**: Cache hit rate düşük

### Queue Alerts

13. **HighRequestQueueLength**
    - **Koşul**: Request queue 100'ü aşarsa
    - **Süre**: 5 dakika
    - **Severity**: Warning
    - **Açıklama**: Request queue uzunluğu yüksek

### Error Tracking Alerts

14. **HighSentryErrorRate**
    - **Koşul**: Sentry error rate saniye başına 10'u aşarsa
    - **Süre**: 5 dakika
    - **Severity**: Warning
    - **Açıklama**: Frontend error rate yüksek

## Troubleshooting

### Elasticsearch bağlantı hatası

```bash
# Elasticsearch sağlığını kontrol edin
curl http://localhost:9200/_cluster/health

# Elasticsearch loglarını kontrol edin
docker logs mami-elasticsearch
```

### Prometheus metrikleri toplanmıyor

```bash
# Prometheus konfigürasyonunu kontrol edin
curl http://localhost:9090/api/v1/targets

# Prometheus loglarını kontrol edin
docker logs mami-prometheus
```

### Grafana dashboard'ları yüklenmedi

```bash
# Grafana loglarını kontrol edin
docker logs mami-grafana

# Veri kaynaklarını kontrol edin
curl -u admin:admin http://localhost:3000/api/datasources
```

## Temizleme

Tüm servisleri durdurmak ve kaldırmak için:

```bash
docker-compose down

# Volume'leri de silmek için
docker-compose down -v
```

## Üretim Ortamı Notları

Üretim ortamında aşağıdaki ayarlamaları yapmalısınız:

1. **Elasticsearch**: Güvenlik etkinleştirin (xpack.security.enabled=true)
2. **Grafana**: Admin şifresini değiştirin
3. **Prometheus**: Retention policy'sini artırın (30 gün yerine 90 gün)
4. **Backup**: Elasticsearch ve Prometheus verilerini düzenli olarak backup'layın
5. **Monitoring**: Monitoring sistemi kendisini monitor etmeli (meta-monitoring)

## Kaynaklar

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
