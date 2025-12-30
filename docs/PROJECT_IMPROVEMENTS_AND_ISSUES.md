# Proje İyileştirmeleri ve Bekleyen Görevler

Bu belge, eski analiz raporlarından derlenmiş ve **19 Aralık 2025** tarihinde kod tabanı kontrol edilerek güncellenmiştir.

---

## 🔴 Kritik Eksikler (Frontend Analizinden)

| Özellik | Durum | Notlar |
|---------|-------|--------|
| **Mesaj Yeniden Oluştur (Regenerate)** | ❌ Eksik | Backend'de endpoint yok, Frontend'de buton işlevsiz. |
| **Sohbet İçe Aktar (Import)** | ❌ Eksik | `/conversations/import` endpoint'i yok. Frontend arayüzü hazır. |
| **Görsel Galerisi API Formatı** | ⚠️ Uyumsuz | Backend `List[UserImageOut]` dönüyor, Frontend string listesi bekliyor. |
| **Komut Paleti Aksiyonları** | ⚠️ Boş | Komutlar (`/mod` vb.) frontend tarafında bağlanmadı. |
| **Tüm Sohbetleri Sil** | ❌ Eksik | API bulunamadı. |

---

## 🟡 Hata Durumları (Kod Kontrol Sonrası)

### ✅ ÇÖZÜLENLER

#### Hata #4: Memory Duplicate Detection
- **Durum:** ✅ **Çözüldü**
- **Tespit:** `app/services/memory_service.py` içinde "Hybrid Duplicate Detection" (Semantic + Entity Check) mekanizması uygulanmış durumda.

#### Hata #8: Image Callback Exception Handling
- **Durum:** ✅ **Çözüldü**
- **Tespit:** `app/image/safe_callback.py` modülü mevcut ve kullanılıyor. Hatalar güvenli şekilde yakalanıyor.

#### Hata #5: Streaming Memory Duplicate Risk
- **Durum:** ✅ **Çözüldü / Güvenli**
- **Tespit:** `user_routes.py` streaming yapısındaki `stream_and_save` fonksiyonu, mesajı veritabanına stream bittikten sonra tek seferde kaydediyor. Race condition riski minimize edilmiş.

---

### ❌ HALA BEKLEYENLER

#### Hata #6: Context Truncation (Basit Silme)
- **Durum:** ❌ **Devam Ediyor**
- **Tespit:** `app/memory/conversation.py` içindeki `get_recent_context` fonksiyonu basitçe son N mesajı alıyor (`[-max_messages:]`). Akıllı silme veya önem puanlaması yok.
- **Öneri:** Mesaj önem puanına göre silme (Semantik Context Window) eklenmeli.

#### Hata #7: WebSocket Authentication
- **Durum:** ⚠️ **İncelenmeli**
- **Tespit:** WebSocket endpointleri `user_routes.py` içinde görünmüyor. Eğer kullanılıyorsa (main.py veya başka yerde) authentication mekanizması kontrol edilmeli.

---

## 🟢 Önerilen Sistem İyileştirmeleri (Future Roadmap)

Aşağıdaki özellikler "10/10 Kalite" için önerilmiştir ancak henüz uygulanmamıştır:

1.  **Prompt Versioning & Analytics:** Prompt değişiklik takibi ve A/B testi.
2.  **Memory Decay:** Eski anıların önem puanının zamanla düşmesi.
3.  **RAG Chunking (Smart):** Cümle bölmeden chunking yapılması.
4.  **Batch Image Generation:** Tek seferde 4 varyasyon üretme.
5.  **Custom Personas:** Kullanıcı tarafında yeni persona yaratma UI/API.
6.  **Admin Audit Logging:** Sansürlenen veya engellenen isteklerin loglanması.

---

## 🛠️ Kod Temizliği Önerileri

Aşağıdaki kullanılmayan kodlar **silinebilir**:

- `app/core/logger.py` -> `get_debug_logger()` (Gereksiz wrapper)
- `app/services/user_preferences.py` -> `set_bulk_formatting_preferences()` (Güvensiz)
- `app/ai/prompts/identity.py` -> `engine_key` (Unused variable)
- `app/auth/session.py` -> `ip_address`, `max_age_minutes` (Unused)

*(Bu belge `docs/` klasöründeki eski raporların özetidir ve günceldir.)*
