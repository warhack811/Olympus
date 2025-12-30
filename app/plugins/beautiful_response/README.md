# Beautiful Response Plugin

Bu plugin, Mami AI'nin ürettiği metin tabanlı cevapları zengin, yapılandırılmış bloklara (structured blocks) dönüştürür.

## Amaç
Standart markdown çıktısını alıp, frontend'in daha akıllıca render edebileceği bileşenlere ayırmak.

## Özellikler (Planlanan)
- **Akıllı Blok Ayrıştırma:** Metinleri, kodları ve alıntıları otomatik olarak ayırır.
- **Dinamik Bileşenler:** Tablolar, grafikler (Mermaid/Chart.js), Kanban tahtaları gibi yapıları tanır.
- **JSON Çıktısı:** İstenirse cevabı raw text yerine structured JSON olarak dönebilir.

## Kurulum
1. `app/plugins/__init__.py` dosyasına kaydedilir (Otomatik).
2. `data/feature_flags.json` üzerinden aktif edilir.

## Konfigürasyon
`beautiful_response_enabled`: `true` / `false`
