# Logging & Monitoring System - Gereksinimler

## Giriş

Mami AI'ın production ortamında sorunları hızlı bir şekilde debug edebilmek, performans darboğazlarını tespit edebilmek ve sistem sağlığını izleyebilmek için kapsamlı bir logging ve monitoring sistemi gereklidir. Bu sistem, backend ve frontend'den gelen logları merkezi bir yerde toplar, hataları otomatik olarak takip eder ve performans metriklerini ölçer.

## Sözlük

- **Logger**: Log mesajlarını toplayan ve işleyen bileşen
- **Handler**: Log mesajlarını belirli bir hedefe (dosya, console, uzak sunucu) gönderen bileşen
- **Formatter**: Log mesajlarını belirli bir formata dönüştüren bileşen
- **Centralized Logging**: Tüm logların merkezi bir yerde toplanması
- **Error Tracking**: Hataların otomatik olarak takip edilmesi ve raporlanması
- **Performance Metrics**: Sistem performansını ölçen metrikler (response time, throughput, vb.)
- **API Monitoring**: API endpoint'lerinin performansını ve sağlığını izleme
- **User Analytics**: Kullanıcı davranışını ve etkileşimlerini takip etme
- **Structured Logging**: JSON formatında yapılandırılmış log mesajları
- **Log Aggregation**: Birden fazla kaynaktan gelen logların toplanması
- **Sentry**: Hata takip ve monitoring platformu
- **Prometheus**: Metrik toplama ve monitoring sistemi
- **Grafana**: Metrik görselleştirme ve dashboard platformu

---

## Gereksinimler

### Gereksinim 1: Backend Logging Infrastructure

**Kullanıcı Hikayesi**: Bir backend geliştirici olarak, tüm API isteklerini, hataları ve sistem olaylarını merkezi bir yerde görmek istiyorum, böylece production'da sorunları hızlı bir şekilde debug edebilirim.

#### Kabul Kriterleri

1. WHEN bir API isteği alındığında, THE Backend Logger SHALL tüm istek detaylarını (method, path, user, timestamp) log'a yazmalı
2. WHEN bir API isteği tamamlandığında, THE Backend Logger SHALL yanıt detaylarını (status code, response time, user) log'a yazmalı
3. WHEN bir hata oluştuğunda, THE Backend Logger SHALL hata mesajını, stack trace'i ve context bilgisini log'a yazmalı
4. WHEN sistem başlatıldığında, THE Backend Logger SHALL başlatma mesajlarını ve konfigürasyon bilgilerini log'a yazmalı
5. WHEN sistem kapatıldığında, THE Backend Logger SHALL kapatma mesajlarını log'a yazmalı
6. THE Backend Logger SHALL log mesajlarını JSON formatında yapılandırılmış olarak yazmalı
7. THE Backend Logger SHALL log dosyalarını dönen şekilde (rotating) yönetmeli ve maksimum dosya boyutunu aşmamalı
8. THE Backend Logger SHALL farklı log seviyeleri (DEBUG, INFO, WARNING, ERROR, CRITICAL) desteklemeli

---

### Gereksinim 2: Frontend Error Tracking

**Kullanıcı Hikayesi**: Bir frontend geliştirici olarak, kullanıcıların karşılaştığı hataları otomatik olarak takip etmek istiyorum, böylece production'da oluşan sorunları hızlı bir şekilde tespit edebilirim.

#### Kabul Kriterleri

1. WHEN frontend'de bir hata oluştuğunda, THE Frontend Error Tracker SHALL hatayı otomatik olarak yakalayıp log'a yazmalı
2. WHEN bir API isteği başarısız olduğunda, THE Frontend Error Tracker SHALL hata detaylarını (status code, error message) log'a yazmalı
3. WHEN bir network hatası oluştuğunda, THE Frontend Error Tracker SHALL network hatası detaylarını log'a yazmalı
4. THE Frontend Error Tracker SHALL hata mesajlarını, stack trace'i ve browser bilgilerini içermeli
5. THE Frontend Error Tracker SHALL hataları merkezi bir sunucuya göndermeli (Sentry veya benzer)
6. THE Frontend Error Tracker SHALL kullanıcı oturumu ve sayfa bilgilerini hata raporuna eklemeli
7. THE Frontend Error Tracker SHALL hataları real-time olarak göndermeli veya batch halinde toplayıp göndermeli

---

### Gereksinim 3: Performance Metrics Collection

**Kullanıcı Hikayesi**: Bir sistem yöneticisi olarak, API response time'ını, throughput'unu ve diğer performans metriklerini izlemek istiyorum, böylece sistem performansını optimize edebilirim.

#### Kabul Kriterleri

1. WHEN bir API isteği tamamlandığında, THE Metrics Collector SHALL response time'ını ölçüp kaydetmeli
2. WHEN bir API isteği tamamlandığında, THE Metrics Collector SHALL request count'unu artırmalı
3. WHEN bir hata oluştuğunda, THE Metrics Collector SHALL error count'unu artırmalı
4. THE Metrics Collector SHALL CPU, memory ve disk kullanımını ölçmeli
5. THE Metrics Collector SHALL database query time'ını ölçmeli
6. THE Metrics Collector SHALL metrikleri Prometheus formatında toplamalı
7. THE Metrics Collector SHALL metrikleri 1 dakika aralıklarla toplamalı
8. THE Metrics Collector SHALL metrikleri en az 30 gün saklamalı

---

### Gereksinim 4: API Monitoring & Health Checks

**Kullanıcı Hikayesi**: Bir DevOps mühendisi olarak, API endpoint'lerinin sağlığını ve kullanılabilirliğini izlemek istiyorum, böylece sistem downtime'ını minimize edebilirim.

#### Kabul Kriterleri

1. THE API Monitor SHALL her API endpoint'inin response time'ını izlemeli
2. THE API Monitor SHALL her API endpoint'inin error rate'ini izlemeli
3. THE API Monitor SHALL her API endpoint'inin availability'sini izlemeli
4. WHEN bir endpoint'in response time'ı threshold'u aşarsa, THE API Monitor SHALL alert göndermeli
5. WHEN bir endpoint'in error rate'i threshold'u aşarsa, THE API Monitor SHALL alert göndermeli
6. THE API Monitor SHALL health check endpoint'i sağlamalı (/health)
7. THE API Monitor SHALL health check'i 30 saniye aralıklarla çalıştırmalı
8. THE API Monitor SHALL health check sonuçlarını log'a yazmalı

---

### Gereksinim 5: User Analytics & Behavior Tracking

**Kullanıcı Hikayesi**: Bir ürün yöneticisi olarak, kullanıcıların sistemi nasıl kullandığını ve hangi özellikleri tercih ettiğini anlamak istiyorum, böylece ürünü daha iyi geliştirebilirim.

#### Kabul Kriterleri

1. WHEN bir kullanıcı sisteme giriş yaptığında, THE Analytics Tracker SHALL login event'ini kaydetmeli
2. WHEN bir kullanıcı bir sohbet başlattığında, THE Analytics Tracker SHALL chat_start event'ini kaydetmeli
3. WHEN bir kullanıcı bir mesaj gönderdiğinde, THE Analytics Tracker SHALL message_sent event'ini kaydetmeli
4. WHEN bir kullanıcı bir resim oluşturduğunda, THE Analytics Tracker SHALL image_generated event'ini kaydetmeli
5. THE Analytics Tracker SHALL event'leri user_id, timestamp ve event_type ile birlikte kaydetmeli
6. THE Analytics Tracker SHALL event'leri merkezi bir veritabanına göndermeli
7. THE Analytics Tracker SHALL event'leri batch halinde toplayıp göndermeli (en az 100 event veya 5 dakika)
8. THE Analytics Tracker SHALL kullanıcı privacy'sini korumak için PII (Personally Identifiable Information) verilerini anonymize etmeli

---

### Gereksinim 6: Centralized Log Storage & Retrieval

**Kullanıcı Hikayesi**: Bir sistem yöneticisi olarak, tüm logları merkezi bir yerde saklamak ve gerektiğinde sorgulamak istiyorum, böylece sorunları hızlı bir şekilde debug edebilirim.

#### Kabul Kriterleri

1. THE Log Storage SHALL tüm backend loglarını merkezi bir yerde saklamalı
2. THE Log Storage SHALL tüm frontend error loglarını merkezi bir yerde saklamalı
3. THE Log Storage SHALL logları en az 90 gün saklamalı
4. THE Log Storage SHALL logları timestamp, log level ve module'e göre filtreleyebilmeli
5. THE Log Storage SHALL logları full-text search ile arayabilmeli
6. THE Log Storage SHALL logları JSON formatında saklamalı
7. THE Log Storage SHALL logları gzip ile sıkıştırmalı (disk alanı tasarrufu için)
8. THE Log Storage SHALL logları backup'lamalı ve disaster recovery için hazır olmalı

---

### Gereksinim 7: Alerting & Notifications

**Kullanıcı Hikayesi**: Bir sistem yöneticisi olarak, kritik hataları veya performans sorunlarını hemen bildirilmek istiyorum, böylece sorunlara hızlı bir şekilde müdahale edebilirim.

#### Kabul Kriterleri

1. WHEN error rate'i %5'i aşarsa, THE Alert System SHALL admin'e email göndermeli
2. WHEN response time'ı 5 saniyeyi aşarsa, THE Alert System SHALL admin'e email göndermeli
3. WHEN disk alanı %80'i aşarsa, THE Alert System SHALL admin'e email göndermeli
4. WHEN memory kullanımı %90'ı aşarsa, THE Alert System SHALL admin'e email göndermeli
5. WHEN bir API endpoint'i 5 dakika boyunca down olursa, THE Alert System SHALL admin'e email göndermeli
6. THE Alert System SHALL alert'leri Slack veya benzer bir platform'a göndermeli
7. THE Alert System SHALL alert'leri escalate edebilmeli (eğer ilk alert'e cevap yoksa)
8. THE Alert System SHALL alert'lerin history'sini tutmalı

---

### Gereksinim 8: Dashboard & Visualization

**Kullanıcı Hikayesi**: Bir sistem yöneticisi olarak, sistem performansını ve sağlığını görsel olarak görmek istiyorum, böylece sorunları hızlı bir şekilde tespit edebilirim.

#### Kabul Kriterleri

1. THE Dashboard SHALL real-time API response time'ını göstermeli
2. THE Dashboard SHALL real-time error rate'ini göstermeli
3. THE Dashboard SHALL real-time request count'unu göstermeli
4. THE Dashboard SHALL CPU, memory ve disk kullanımını göstermeli
5. THE Dashboard SHALL database query time'ını göstermeli
6. THE Dashboard SHALL top error'ları göstermeli
7. THE Dashboard SHALL time-series grafikleri göstermeli (son 24 saat, 7 gün, 30 gün)
8. THE Dashboard SHALL custom alert'ler oluşturabilmeli

---

### Gereksinim 9: Log Retention & Cleanup

**Kullanıcı Hikayesi**: Bir sistem yöneticisi olarak, eski logları otomatik olarak silmek istiyorum, böylece disk alanını tasarruf edebilirim.

#### Kabul Kriterleri

1. THE Log Cleanup SHALL 90 günden eski logları silmeli
2. THE Log Cleanup SHALL silme işlemini günde bir kere çalıştırmalı (gece saatlerinde)
3. THE Log Cleanup SHALL silme işleminden önce backup'lamalı
4. THE Log Cleanup SHALL silme işlemini log'a yazmalı
5. THE Log Cleanup SHALL silme işlemini admin'e email ile bildirimli yapmalı
6. THE Log Cleanup SHALL silme işlemini dry-run modunda test edebilmeli
7. THE Log Cleanup SHALL silme işlemini scheduled olarak yapılandırabilmeli
8. THE Log Cleanup SHALL silme işlemini başarısız olursa retry etmeli

---

### Gereksinim 10: Integration with Existing Systems

**Kullanıcı Hikayesi**: Bir backend geliştirici olarak, logging & monitoring sistemi mevcut kodla sorunsuz bir şekilde entegre olmalı, böylece kod değişiklikleri minimal olmalıdır.

#### Kabul Kriterleri

1. THE Logging System SHALL mevcut `app.core.logger` modülü ile uyumlu olmalı
2. THE Logging System SHALL mevcut `app.main` middleware'i ile uyumlu olmalı
3. THE Logging System SHALL mevcut error handling mekanizması ile uyumlu olmalı
4. THE Logging System SHALL mevcut API route'ları ile uyumlu olmalı
5. THE Logging System SHALL mevcut frontend error handling ile uyumlu olmalı
6. THE Logging System SHALL backward compatibility sağlamalı
7. THE Logging System SHALL gradual migration desteklemeli (eski ve yeni sistem aynı anda çalışabilmeli)
8. THE Logging System SHALL configuration ile enable/disable edilebilmeli

---

## Özet

Bu gereksinimler, Mami AI'ın production ortamında sorunları hızlı bir şekilde debug edebilmek, performans darboğazlarını tespit edebilmek ve sistem sağlığını izleyebilmek için gerekli olan kapsamlı bir logging ve monitoring sistemi tanımlar. Sistem, backend ve frontend'den gelen logları merkezi bir yerde toplar, hataları otomatik olarak takip eder ve performans metriklerini ölçer.
