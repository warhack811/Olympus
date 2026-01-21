# Image Generation System - Production Ready Fix

## Introduction

Resim üretim sistemi temel işlevselliği sağlıyor ancak production'a hazır değil. Bu spec, 9 kritik sorun ve uyarıyı çözmek için kapsamlı bir çözüm sunuyor.

## Glossary

- **Queue Position**: Kuyrukta bir job'un sırası (1, 2, 3, ...)
- **Message Persistence**: Mesaj verilerinin database'de kalıcı olarak saklanması
- **Race Condition**: Concurrent işlemlerde veri kaybı riski
- **Stuck Job**: 5 dakika inaktif kalan job
- **Terminal State**: Complete veya error durumu (geri dönüş yok)
- **Deep Merge**: Nested object'leri birleştirme
- **Atomic Counter**: Thread-safe counter (Redis INCR)
- **Circuit Breaker**: Hata durumunda request'leri durdurma mekanizması

## Requirements

### Requirement 1: Queue Position Dinamik Güncelleme

**User Story**: Kullanıcı olarak, kuyrukta beklediğim resim isteğinin sırasının gerçek zamanda güncellendiğini görmek istiyorum, böylece ne kadar bekleyeceğimi bilebilirim.

#### Acceptance Criteria

1. WHEN bir job processing'e geçtiğinde, THEN kalan queued job'ların queue_position'ı frontend'de otomatik olarak güncellenir
2. WHEN sayfa yenilendikçinde, THEN queue position'lar doğru şekilde hesaplanır
3. WHEN job complete olduğunda, THEN queue position'lar yeniden hesaplanır
4. WHEN multiple job'lar aynı anda queue'da olduğunda, THEN her job'un unique position'ı vardır

---

### Requirement 2: Message Persistence - Tüm Alanlar

**User Story**: Kullanıcı olarak, sayfa yenilemesinden sonra resim üretim durumunu görmek istiyorum, böylece ilerlemeyi takip edebilirim.

#### Acceptance Criteria

1. WHEN job queued durumuna geçtiğinde, THEN status, progress, queue_position database'de kaydedilir
2. WHEN job processing durumuna geçtiğinde, THEN status, progress, queue_position database'de güncellenir
3. WHEN sayfa yenilendikçinde, THEN tüm job bilgileri database'den yüklenir
4. WHEN job complete/error olduğunda, THEN image_url veya error message database'de kaydedilir
5. WHEN concurrent update'ler olduğunda, THEN veri kaybı olmaz (deep merge)

---

### Requirement 3: Race Condition Protection

**User Story**: Sistem olarak, concurrent update'lerde veri kaybı olmadan güvenli bir şekilde çalışmak istiyorum.

#### Acceptance Criteria

1. WHEN WebSocket ve backend aynı anda update_message() çağırdığında, THEN deep merge ile tüm alanlar korunur
2. WHEN multiple field'lar update edildiğinde, THEN hiçbir field kaybolmaz
3. WHEN database transaction başarısız olduğunda, THEN rollback yapılır ve veri tutarlı kalır

---

### Requirement 4: Stuck Job Detection

**User Story**: Sistem olarak, 5 dakika inaktif kalan job'ları otomatik olarak error olarak işaretlemek istiyorum, böylece kullanıcı sonsuz bekleme durumundan kurtulur.

#### Acceptance Criteria

1. WHEN job 5 dakika inaktif kalırsa, THEN backend tarafından error olarak işaretlenir
2. WHEN stuck job error olarak işaretlenirse, THEN user'a bildirim gönderilir
3. WHEN maintenance task çalışırsa, THEN tüm stuck job'lar kontrol edilir
4. WHEN stuck job'lar işaretlenirse, THEN database'de updated_at timestamp'ı güncellenir

---

### Requirement 5: Timeout Handling - User Friendly

**User Story**: Kullanıcı olarak, Forge API timeout olduğunda açık bir hata mesajı görmek istiyorum.

#### Acceptance Criteria

1. WHEN Forge API timeout olursa, THEN user'a "Forge API zaman aşımına uğradı (180s). Lütfen tekrar deneyin." mesajı gönderilir
2. WHEN timeout olursa, THEN job error durumuna geçer
3. WHEN timeout olursa, THEN placeholder image döndürülmez (error döndürülür)
4. WHEN user tekrar denerse, THEN yeni bir job oluşturulur

---

### Requirement 6: Concurrent Submission - Atomic Counter

**User Story**: Sistem olarak, hızlı arka arkaya gelen job'ların doğru queue position'ları almasını sağlamak istiyorum.

#### Acceptance Criteria

1. WHEN 3 job hızlı arka arkaya gönderilirse, THEN her job unique position alır (1, 2, 3)
2. WHEN Redis'ten multiple job pop edilirse, THEN queue position'lar doğru hesaplanır
3. WHEN atomic counter kullanılırsa, THEN race condition olmaz

---

### Requirement 7: WebSocket Delivery Guarantee

**User Story**: Kullanıcı olarak, offline olduğumda bile resim üretim durumunu görmek istiyorum.

#### Acceptance Criteria

1. WHEN user offline ise, THEN sayfa yüklendiğinde database'den durum yüklenir
2. WHEN WebSocket mesajı gönderilmezse, THEN database persistence ile veri kurtarılır
3. WHEN sayfa yenilendikçinde, THEN tüm pending job'lar gösterilir

---

### Requirement 8: Circuit Breaker Configuration

**User Story**: Sistem olarak, Forge API down olduğunda graceful degradation sağlamak istiyorum.

#### Acceptance Criteria

1. WHEN 5 hata arka arkaya olursa, THEN circuit breaker açılır
2. WHEN circuit breaker açılırsa, THEN placeholder image döndürülür
3. WHEN 60 saniye geçerse, THEN circuit breaker reset'e hazır hale gelir
4. WHEN circuit breaker reset olursa, THEN yeni request'ler denenir

---

### Requirement 9: Comprehensive Error Messages

**User Story**: Kullanıcı olarak, hata olduğunda ne yapacağımı bilen açık bir mesaj görmek istiyorum.

#### Acceptance Criteria

1. WHEN Forge API bağlantı hatası olursa, THEN "Forge API bağlantı hatası. Lütfen sistem yöneticisine bildirin." mesajı gösterilir
2. WHEN timeout olursa, THEN "İşlem zaman aşımına uğradı. Lütfen tekrar deneyin." mesajı gösterilir
3. WHEN stuck job olursa, THEN "İşlem zaman aşımına uğradı (Stuck Job Guard). Lütfen tekrar deneyin." mesajı gösterilir
4. WHEN unknown error olursa, THEN "Bilinmeyen bir hata oluştu. Lütfen tekrar deneyin." mesajı gösterilir

---

### Requirement 10: Integration Testing

**User Story**: Sistem olarak, tüm bileşenlerin birlikte doğru çalıştığını doğrulamak istiyorum.

#### Acceptance Criteria

1. WHEN 3 job hızlı arka arkaya gönderilirse, THEN tüm job'lar doğru şekilde işlenir
2. WHEN sayfa yenilendikçinde, THEN tüm job'lar doğru durumda yüklenir
3. WHEN concurrent update'ler olduğunda, THEN veri kaybı olmaz
4. WHEN Forge API timeout olursa, THEN user'a doğru mesaj gönderilir
5. WHEN stuck job olursa, THEN backend tarafından error olarak işaretlenir

