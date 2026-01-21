# Logging & Monitoring System - Implementation Plan

## Genel Bakış

Logging & Monitoring System'i adım adım implement etmek için tasarlanmış bir implementation plan. Her task, önceki task'lar üzerine inşa edilir ve incremental progress sağlar.

## Tasks

- [x] 1. Backend Logging Infrastructure - JSON Formatter & Structured Logging
  - Mevcut `app/core/logger.py` modülünü genişlet
  - JSON formatter ekle (timestamp, level, module, message, context)
  - Structured logging helper fonksiyonları ekle (log_request, log_response, log_error, log_event)
  - Request ID tracking ekle (correlation ID)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] 1.1 Write unit tests for JSON logger

  - Test JSON formatter'ın doğru format üretip üretmediği
  - Test structured logging helper'larının doğru çalışıp çalışmadığı
  - Test request ID tracking'in doğru çalışıp çalışmadığı
  - **Property 1: Log Entry Yapısı**
  - **Validates: Requirements 1.6**

- [x] 2. Backend Logging Middleware Enhancement
  - `app/main.py` middleware'ini genişlet
  - Request başlangıcında request ID oluştur
  - Request/response logging'i JSON formatında yap
  - Error logging'i middleware'de ekle
  - Performance timing'i ekle (request duration)
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2.1 Write integration tests for logging middleware

  - Test middleware'in request'leri doğru log'ladığı
  - Test middleware'in response'ları doğru log'ladığı
  - Test middleware'in error'ları doğru log'ladığı
  - **Property 1: Log Entry Yapısı**
  - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 3. Performance Metrics Collection - Prometheus Integration
  - `app/core/metrics.py` modülü oluştur
  - Prometheus client library'sini ekle (prometheus-client)
  - API request duration histogram'ı ekle
  - API request count counter'ı ekle
  - API error count counter'ı ekle
  - System metrics (CPU, memory, disk) collector'ı ekle
  - Database query time histogram'ı ekle
  - `/metrics` endpoint'i ekle (Prometheus format)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 3.1 Write unit tests for metrics collector

  - Test histogram'ın doğru çalışıp çalışmadığı
  - Test counter'ın doğru çalışıp çalışmadığı
  - Test system metrics'in doğru toplandığı
  - **Property 2: Metric Format**
  - **Validates: Requirements 3.6**

- [x] 4. Metrics Middleware Integration
  - `app/main.py` middleware'ine metrics collection ekle
  - Her request'in duration'ını ölç ve histogram'a ekle
  - Her request'in status code'unu counter'a ekle
  - Error'ları error counter'a ekle
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 4.1 Write integration tests for metrics middleware

  - Test middleware'in duration'ı doğru ölçüp ölçmediği
  - Test middleware'in status code'u doğru saydığı
  - Test middleware'in error'ları doğru saydığı
  - **Property 6: Metrics Consistency**
  - **Validates: Requirements 3.2**

- [x] 5. API Monitoring & Health Checks
  - `app/api/system_routes.py` modülünü genişlet
  - `/health` endpoint'ini iyileştir (database, cache, external services check)
  - `/health/detailed` endpoint'i ekle (detaylı sistem bilgisi)
  - Health check'i 30 saniye aralıklarla çalıştıracak background task ekle
  - Health check sonuçlarını log'a yaz
  - Response time threshold'u aşıldığında alert gönder (5 saniye)
  - Error rate threshold'u aşıldığında alert gönder (%5)
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

- [x] 5.1 Write unit tests for health checks

  - Test health check'in database'i kontrol ettiği
  - Test health check'in cache'i kontrol ettiği
  - Test health check'in external services'i kontrol ettiği
  - **Property 7: Health Check Idempotence**
  - **Validates: Requirements 4.6**

- [x] 6. Frontend Error Tracking - Sentry Integration
  - `ui-new/src/lib/errorTracking.ts` modülü oluştur
  - Sentry SDK'sını initialize et
  - Global error handler ekle (window.onerror)
  - Unhandled promise rejection handler ekle
  - API error interceptor ekle
  - Network error handler ekle
  - User context setter ekle (user ID, username)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 6.1 Write unit tests for error tracking

  - Test error handler'ın exception'ları yakaladığı
  - Test error handler'ın API error'larını yakaladığı
  - Test error handler'ın network error'larını yakaladığı
  - **Property 5: Error Tracking Round-Trip**
  - **Validates: Requirements 2.5**

- [x] 7. Frontend Error Tracking Integration
  - `ui-new/src/api/client.ts` modülüne error tracking ekle
  - API error'larını Sentry'ye gönder
  - Network error'larını Sentry'ye gönder
  - Error context'i ekle (endpoint, method, status code)
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [x] 7.1 Write integration tests for frontend error tracking

  - Test API error'larının Sentry'ye gönderildiği
  - Test network error'larının Sentry'ye gönderildiği
  - Test error context'in doğru eklendiği
  - **Property 5: Error Tracking Round-Trip**
  - **Validates: Requirements 2.2, 2.3, 2.5**

- [x] 8. User Analytics & Behavior Tracking
  - `app/core/analytics.py` modülü oluştur
  - Event tracking fonksiyonları ekle (track_event)
  - Event batch collection ekle (100 event veya 5 dakika)
  - Event flushing mekanizması ekle
  - PII anonymization fonksiyonları ekle
  - Event'leri PostgreSQL'e kaydet
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [x] 8.1 Write unit tests for analytics

  - Test event tracking'in doğru çalışıp çalışmadığı
  - Test batch collection'ın doğru çalışıp çalışmadığı
  - Test PII anonymization'ın doğru çalışıp çalışmadığı
  - **Property 3: Event Completeness**
  - **Validates: Requirements 5.5**
  - **Property 8: Analytics Anonymization**
  - **Validates: Requirements 5.8**

- [x] 9. Frontend Analytics Integration
  - `ui-new/src/lib/analytics.ts` modülü oluştur
  - Frontend event tracking fonksiyonları ekle
  - Login event'i ekle
  - Chat message event'i ekle
  - Image generation event'i ekle
  - Event'leri backend'e gönder
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 9.1 Write integration tests for frontend analytics

  - Test login event'inin backend'e gönderildiği
  - Test chat event'inin backend'e gönderildiği
  - Test image event'inin backend'e gönderildiği
  - **Property 3: Event Completeness**
  - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

- [x] 10. Checkpoint - Ensure all tests pass
  - Tüm unit test'lerin geçtiğini kontrol et
  - Tüm integration test'lerin geçtiğini kontrol et
  - Tüm property test'lerin geçtiğini kontrol et
  - Sorun varsa kullanıcıya sor

- [x] 11. Docker Compose Setup - Elasticsearch, Prometheus, Grafana
  - `docker-compose.yml` dosyası oluştur
  - Elasticsearch service'i ekle (port 9200)
  - Prometheus service'i ekle (port 9090)
  - Grafana service'i ekle (port 3000)
  - Volume'ler ekle (data persistence)
  - Network'ü konfigüre et
  - _Requirements: 6.1, 6.2, 7.1, 8.1_

- [x] 12. Elasticsearch Integration - Log Storage
  - `app/core/elasticsearch_client.py` modülü oluştur
  - Elasticsearch client'ı initialize et
  - Log index'i oluştur (daily rotation)
  - Log'ları Elasticsearch'e gönder
  - Log retention policy'sini ekle (90 gün)
  - Log'ları backup'la (disaster recovery)
  - Log'ları gzip ile sıkıştır
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

- [x] 12.1 Write integration tests for Elasticsearch

  - Test log'ların Elasticsearch'e yazıldığı
  - Test log'ların doğru index'e yazıldığı
  - Test log'ların query'lendiği
  - **Property 4: Log Retention**
  - **Validates: Requirements 6.3**

- [x] 13. Prometheus Configuration - Metrics Storage
  - `prometheus.yml` konfigürasyon dosyası oluştur
  - Scrape interval'ı ayarla (15 saniye)
  - Alert rules'ları ekle:
    - Error rate %5'i aşarsa
    - Response time 5 saniyeyi aşarsa
    - Disk alanı %80'i aşarsa
    - Memory kullanımı %90'ı aşarsa
    - API endpoint'i 5 dakika down olursa
  - Retention policy'sini ayarla (30 gün)
  - _Requirements: 3.7, 3.8, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 14. Grafana Dashboard Setup
  - Grafana data source'ları konfigüre et (Prometheus, Elasticsearch)
  - API response time dashboard'ı oluştur
  - Error rate dashboard'ı oluştur
  - System metrics dashboard'ı oluştur
  - Top errors dashboard'ı oluştur
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [x] 14.1 Write integration tests for Grafana

  - Test dashboard'ların oluşturulduğu
  - Test dashboard'ların data gösterdiği
  - Test alert'lerin konfigüre edildiği

- [x] 15. Alerting & Notifications - Email & Slack
  - `app/core/alerting.py` modülü oluştur
  - Alert kurallarını tanımla (error rate, response time, disk space, memory)
  - Email notification'ı ekle
  - Slack notification'ı ekle
  - Alert history'sini kaydet
  - Alert escalation mekanizması ekle (ilk alert'e cevap yoksa)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

- [x] 15.1 Write integration tests for alerting

  - Test alert'lerin tetiklendiği
  - Test email notification'ının gönderildiği
  - Test Slack notification'ının gönderildiği

- [x] 16. Log Retention & Cleanup - Automated Deletion
  - `app/core/log_cleanup.py` modülü oluştur
  - Cleanup job'ını oluştur (günde bir kere, gece saatlerinde)
  - 90 günden eski log'ları sil
  - Silme işleminden önce backup'la
  - Silme işlemini log'a yaz
  - Admin'e email ile bildir
  - Dry-run modunda test edebilme ekle
  - Başarısız olursa retry mekanizması ekle
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [x] 16.1 Write integration tests for log cleanup

  - Test cleanup job'ının çalıştığı
  - Test eski log'ların silindiği
  - Test backup'ın alındığı

- [x] 17. Integration with Existing Systems
  - Mevcut `app/core/logger.py` ile uyumluluğu kontrol et
  - Mevcut `app/main.py` middleware'i ile uyumluluğu kontrol et
  - Mevcut error handling mekanizması ile uyumluluğu kontrol et
  - Backward compatibility test'leri yaz
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

- [x] 17.1 Write integration tests for backward compatibility

  - Test eski logger'ın hala çalışıp çalışmadığı
  - Test eski error handling'in hala çalışıp çalışmadığı
  - Test eski API route'larının hala çalışıp çalışmadığı

- [x] 18. Environment Configuration & Documentation
  - `.env.example` dosyasına Sentry DSN ekle
  - `.env.example` dosyasına Elasticsearch URL'si ekle
  - `.env.example` dosyasına Prometheus URL'si ekle
  - `.env.example` dosyasına Grafana URL'si ekle
  - `.env.example` dosyasına Slack webhook URL'si ekle
  - `.env.example` dosyasına email konfigürasyonu ekle
  - README.md'ye setup instructions'ı ekle
  - _Requirements: 10.8_

- [x] 19. Final Checkpoint - Ensure all tests pass
  - Tüm unit test'lerin geçtiğini kontrol et
  - Tüm integration test'lerin geçtiğini kontrol et
  - Tüm property test'lerin geçtiğini kontrol et
  - Production readiness checklist'ini tamamla
  - Sorun varsa kullanıcıya sor

## Notlar

- Task'lar marked with `*` optional'dır ve MVP için atlanabilir
- Her task, önceki task'lar üzerine inşa edilir
- Checkpoint task'ları, incremental validation sağlar
- Property test'ler, universal correctness'i doğrular
- Unit test'ler, specific examples ve edge cases'i doğrular
