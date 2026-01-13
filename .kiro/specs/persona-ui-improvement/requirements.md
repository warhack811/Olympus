# Requirements Document

## Introduction

Atlas projesinin mevcut persona seçimi UI'ı footer alanında çok fazla yer kaplamakta ve kullanıcı deneyimini olumsuz etkilemektedir. Bu özellik, persona seçimini daha kompakt, erişilebilir ve kullanışlı hale getirmeyi amaçlamaktadır.

## Glossary

- **Persona**: Kullanıcının AI asistanının davranış tarzını belirleyen karakter profili
- **UI_Component**: Kullanıcı arayüzündeki etkileşimli element
- **Footer_Area**: Sayfanın alt kısmındaki input ve kontrol alanı
- **Dropdown_Menu**: Açılır menü komponenti
- **Active_Persona**: Şu anda seçili olan persona
- **Atlas_Interface**: Ana chat arayüzü

## Requirements

### Requirement 1: Kompakt Persona Seçimi

**User Story:** Kullanıcı olarak, persona seçiminin daha az yer kaplamasını istiyorum, böylece chat alanım daha geniş olsun.

#### Acceptance Criteria

1. WHEN kullanıcı ana sayfayı açtığında, THE Atlas_Interface SHALL persona seçimini kompakt bir formatta göstermeli
2. THE UI_Component SHALL mevcut footer alanının %30'undan fazlasını kaplamamalı
3. WHEN persona seçimi yapıldığında, THE Atlas_Interface SHALL seçimi görsel olarak belirtmeli
4. THE Active_Persona SHALL her zaman kullanıcıya görünür olmalı

### Requirement 2: Gelişmiş Erişilebilirlik

**User Story:** Kullanıcı olarak, persona seçimini hızlı ve kolay yapmak istiyorum, böylece iş akışım kesintiye uğramasın.

#### Acceptance Criteria

1. WHEN kullanıcı persona değiştirmek istediğinde, THE UI_Component SHALL maksimum 2 tıklama ile erişilebilir olmalı
2. THE UI_Component SHALL keyboard navigasyonunu desteklemeli
3. WHEN kullanıcı persona üzerine hover yaptığında, THE Atlas_Interface SHALL persona açıklamasını göstermeli
4. THE UI_Component SHALL mobile cihazlarda da kullanılabilir olmalı

### Requirement 3: Görsel Tutarlılık

**User Story:** Tasarımcı olarak, persona seçiminin Atlas'ın genel tasarım diline uygun olmasını istiyorum, böylece tutarlı bir deneyim sunsun.

#### Acceptance Criteria

1. THE UI_Component SHALL mevcut Atlas tema renklerini kullanmalı
2. THE UI_Component SHALL glass-morphism tasarım stilini korumalı
3. WHEN persona değiştirildiğinde, THE Atlas_Interface SHALL smooth animasyon göstermeli
4. THE UI_Component SHALL mevcut typography sistemini kullanmalı

### Requirement 4: Persona Yönetimi

**User Story:** Kullanıcı olarak, tüm persona seçeneklerine erişebilmek istiyorum, böylece ihtiyacıma göre en uygun olanı seçebilim.

#### Acceptance Criteria

1. THE UI_Component SHALL tüm mevcut personaları (9 adet) gösterebilmeli
2. WHEN yeni persona eklenmesi gerektiğinde, THE UI_Component SHALL kolayca genişletilebilir olmalı
3. THE UI_Component SHALL persona iconlarını ve isimlerini göstermeli
4. WHEN persona seçildiğinde, THE Atlas_Interface SHALL seçimi backend'e iletmeli

### Requirement 5: Performans ve Uyumluluk

**User Story:** Geliştirici olarak, yeni UI'ın mevcut kod yapısını bozmadan çalışmasını istiyorum, böylece sistem kararlılığı korunsun.

#### Acceptance Criteria

1. THE UI_Component SHALL mevcut JavaScript fonksiyonlarıyla uyumlu olmalı
2. THE UI_Component SHALL sayfa yükleme süresini %5'ten fazla artırmamalı
3. WHEN persona değiştirildiğinde, THE Atlas_Interface SHALL mevcut chat geçmişini korumalı
4. THE UI_Component SHALL tüm modern tarayıcılarda çalışmalı