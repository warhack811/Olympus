# Orchestrator Router v4.2 — Handoff & Operasyon Dokümanı

> **Tarih**: 29 Aralık 2025  
> **Sürüm**: v4.2  
> **Durum**: Feature Complete / Rollout Ready  

Bu belge, **Orchestrator Router v4.2** sisteminin operasyonel devri, güvenli dağıtımı (rollout) ve acil durum yönetimi için tek doğruluk kaynağıdır.

---

## 0. Kapsam ve Prensipler

Orchestrator v4.2, eski "Smart Router" yapısının yerine geçen, ancak **%100 geriye uyumlu** çalışan hibrit bir yönlendirme katmanıdır.

*   **Temel Prensip**: `ORCH_ENABLED=False` (Varsayılan) olduğu sürece sistem **Tamamen Legacy** modda çalışır. Müşteri trafiğini etkilemez.
*   **Fail-Safe**: Orchestrator içindeki herhangi bir hata (Timeout, Exception, Validation Failure) otomatik olarak **Legacy Fallback** tetikler. Sistem asla 500 hatası üretmez; eski cevabı döner.
*   **Deterministik**: Prompt inşası, araç seçimi ve doğrulama adımları rastgelelikten arındırılmıştır (Deterministic Verify).

### Ana Şalterler ve Hook Mekanizması
Sistem iki kademeli bir kontrol mekanizmasına sahiptir:
1.  **`ORCH_ENABLED`** (`app/api/routes/chat.py`): Legacy kod içinde Orchestrator v4.2'nin **kod seviyesinde** çağrılıp çağrılmayacağını belirler. `False` ise Orchestrator v4.2 koduna hiç girilmez.
2.  **`ORCH_PRODUCTION_ENABLED`** (`app/orchestrator_v42/feature_flags.py`): Orchestrator v4.2 katmanına girildikten sonraki ana şalterdir. `True` ise rollout/allowlist kuralları uygulanır.

---

## 1. Hızlı Başlangıç (Quick Start)

### 1.1 Sağlık Kontrolü (Smoke Test)
Sistemin dağıtıma hazır olup olmadığını tek komutla test edin:
```bash
python verify_smoke_suite_14_8.py
```
*   **Beklenen Çıktı**: `ALL CRITICAL TESTS PASSED`

---

## 2. Feature Flags Referansı

Tüm konfigürasyon `app/orchestrator_v42/feature_flags.py` dosyasında `OrchestratorFeatureFlags` sınıfı ile yönetilir.

### Kritik Bayraklar

| Env Değişkeni | Varsayılan | Açıklama | Risk |
| :--- | :--- | :--- | :--- |
| `ORCH_PRODUCTION_ENABLED` | `False` | **Orchestrator Ana Şalter**. Rollout kurallarını aktif eder. | YÜKSEK |
| `ORCH_ROLLOUT_PERCENT` | `0` | Trafik yüzdesi (0-100). Deterministik bucket hesaplar. | ORTA |
| `ORCH_LLM_DRY_RUN` | `True` | True ise LLM çağrısı yapılmaz. Router bu flag True ise trafiği Legacy'ye atar. | DÜŞÜK |
| `ORCH_RAG_DRY_RUN` | `True` | RAG araması yapar ancak sonucu prompt'a eklemez. | DÜŞÜK |

---

## 3. Rollout Runbook (Operasyonel Geçiş)

Dosya: `app/orchestrator_v42/rollout.py`

### 3.1 Kademeli Açılış Planı
1.  **Aşama 0 (Internal Test)**: `ORCH_PRODUCTION_ENABLED=True`, `ORCH_LLM_DRY_RUN=False`, `ORCH_ROLLOUT_PERCENT=0`, `ORCH_ROLLOUT_ALLOWLIST=dev_user_1`
2.  **Aşama 1 (Canary - 1%)**: `ORCH_ROLLOUT_PERCENT=1`
3.  **Aşama 2 (Beta - 20%)**: `ORCH_ROLLOUT_PERCENT=20`
4.  **Aşama 3 (GA - 100%)**: `ORCH_ROLLOUT_PERCENT=100`

---

## 4. Bütçe ve Timeout Politikası

*   **Memory Writeback**: `memory_write_timeout_s` (Default **0.25s**). Ana akışı bozmamak için fire-and-forget kısıtı vardır.
*   **Retry Yok**: Gateway seviyesinde failover mevcuttur, ancak alt bileşenlerde retry uygulanmaz.

---

## 5. Evidence-Aware Akış (Kanıt Sistemi)

*   **Hafıza**: En son 5 madde (max 240 char).
*   **Araçlar**: Max 2 araç çağrısı (MVP Sert Limit).
*   **RAG**: Max 3 doküman (max 300 char).

---

## 6. Kalite Kontrol (Quality Control)

Dosya: `app/orchestrator_v42/quality_control.py`

*   **Verify/Jury**: Risk >= Medium ise tetiklenir.
*   **Streaming**: Yayındayken Jury zorla kapatılır (`jury_forced_off_by_streaming`).

---

## 7. Telemetri ve İzleme

Dosya: `app/orchestrator_v42/telemetry.py`

### Whitelist (İzinli Label Anahtarları)
Düşük kardinaliteyi korumak için sadece aşağıdaki anahtarlar kabul edilir:
*   `reason` (Hata veya fallback nedeni)
*   `type` (İşlem tipi)
*   `risk` (Güvenlik risk seviyesi)
*   `verify` (Doğrulama durumu)
*   `jury` (Jüri sonucu)

---

## 8. Testler ve Smoke Suite Kılavuzu

Sistemin stabilitesi `verify_smoke_suite_14_8.py` üzerinden doğrulanır.

### Bölümler ve Davranış
*   **PHASE 1 (CRITICAL TESTS)**: Sistemin ana motorunun (Gateway, Evidence, Memory) çalışmasını test eder. Herhangi biri başarısız olursa suite **Exit Code 1** ile anında durur.
    *   `verify_gateway_evidence_e2e_14_7.py`: En kritik uçtan uca kanıt akışı testi.
    *   `verify_hygiene_14_8.py`: Kod içi yasaklı kelime ve güvenlik taraması.
*   **PHASE 2 (LEGACY TESTS)**: Opsiyonel veya eski özellikleri test eder. Fail durumunda raporlanır ancak pipeline'ı kırmaz (Exit Code 0).

### Yeni Test Ekleme Kuralları
1.  **CRITICAL**: Sadece deterministik, mocklanmış ve her ortamda tutarlı çalışan testler bu gruba eklenmelidir.
2.  **LEGACY**: Ortam değişkenlerine, gerçek internete veya rastgele LLM çıktılarına bağımlı testler bu grupta kalmalıdır.

---

## 9. Arıza Senaryoları (Troubleshooting)

| Belirti | Olası Neden | Çözüm |
| :--- | :--- | :--- |
| **Hep Legacy Dönüyor** | `ORCH_ENABLED=False` veya `ORCH_PRODUCTION_ENABLED=False` | Ayarları kontrol et. |
| **Hafıza Yazmıyor** | Timeout yetersiz (0.25s) | `ORCH_MEMORY_WRITE_TIMEOUT_S` artır. |
| **Streaming & Jury Çakışması** | Streaming açıksa Jury çalışmaz | Tasarım gereği (Quality Control). |

---

## 10. Release Checklist (Go/No-Go)

### 10.1 Preflight (Deploy Öncesi)
- [ ] **Bayrak Kontrolü**: `ORCH_ENABLED=True` ve `ORCH_PRODUCTION_ENABLED=True` ayarlanmış olmalı.
- [ ] **Güvenli Başlangıç**: İlk aşamada `ORCH_LLM_DRY_RUN=False`, ancak `ORCH_ROLLOUT_PERCENT=0` ile sadece allowlist üzerinden test yapılmalı.
- [ ] **Bağımlılıklar**: RAG ve Araç (Web Search) servislerinin ayakta olduğu (Dry-run kapalıysa) doğrulanmalı.
- [ ] **Kritik Kanıt**: `python verify_smoke_suite_14_8.py` çalıştırılmalı ve `ALL CRITICAL TESTS PASSED` sonucu alınmalı.

### 10.2 Canary İzleme (1%–5%)
- [ ] **Telemetri**: `orch_fallback` sayaçları izlenmeli.
  *   *Alarm Eşiği*: Toplam isteklerin %2'sinden fazlası `reason=error` ile fallback'e düşüyorsa durdur.
  *   *Latency*: Gateway yanıt süresi ortalamada 3s üzerine çıkıyorsa izleme paneli / metrik paneli üzerinden incele.
- [ ] **Debug Snapshot**: `/api/v1/admin/orch/snapshot` endpoint'i üzerinden (verbose=true ile) logic'in doğru bucket'lara düştüğü teyit edilmeli.
   *   *Not*: Chat UI'da URL sonuna `?orch_debug=1` ekleyerek sağ üstte açılan panelden anlık izleme yapılabilir (Dev/Test amaçlı).

### 10.3 Rollback Prosedürü (1 Dakikada Kapatma)
- [ ] **Hızlı Kesici**: Herhangi bir anomali durumunda **`ORCH_ENABLED=False`** yapın. Bu, `chat.py` seviyesinde Orchestrator akışını anında ve tamamen devre dışı bırakır.
- [ ] **Alternatif**: `ORCH_ROLLOUT_PERCENT=0` yapılarak trafik kademeli (ancak hızlı) bir şekilde Legacy'ye çekilebilir.
- [ ] **Recovary**: Auto-circuit tetiklendiyse, hata kaynağı çözüldükten sonra servis yeniden başlatılarak veya TTL süresi beklenerek toparlanma sağlanır.

### 10.4 Yayın Sonrası (24 Saat)
- [ ] **Legacy Takip**: `PHASE 2 (LEGACY TESTS)` düzenli olarak (örn. saatte bir) pipeline kırmadan koşulmalı ve regresyon takibi yapılmalı.
- [ ] **Stabilite**: Flaky (istikrarsız) olduğu tespit edilen hiçbir test **CRITICAL** grubuna alınmamalı, LEGACY grubunda iyileştirmesi beklenmelidir.

---

## 11. Geliştirici İzleme (Observability)

Geliştirme ve test süreçlerinde Orchestrator'ın anlık durumunu izlemek için admin-only bir endpoint mevcuttur.

*   **Endpoint**: `/api/v1/admin/orch/snapshot`
*   **Yetki**: Admin Session gereklidir.
*   **Parametreler**:
    *   `verbose=true`: Eğer sistem `DEBUG=True` (Geliştirme modu) modundaysa, tüm karar zincirini ve kanıt detaylarını (trace) döner.
    *   `verbose=false`: Sadece telemetri sayaçlarını ve temel sistem sağlık özetini döner.

Bu endpoint, prod ortamında `DEBUG=False` iken detaylı veri sızıntısını önlemek için otomatik olarak `verbose` verisini kısıtlar.

---

## 12. Gelecek Yol Haritası (FAZ 17)

**Ocak 2026** için planlanan "FAZ 17: Proaktif Kişisel Veri ve Çoklu İstemci" geliştirmeleri aşağıdadır.

### 12.1 Hedef: Çoklu İstemci (Multi-Client)
*   **Android & Masaüstü**: Orchestrator API artık mobil ve masaüstü native istemciler için optimize edilecek.
*   **Offline First**: İstemci tarafında cache ve senkronizasyon yetenekleri artırılacak.

### 12.2 Personal Data Vault (Kişisel Veri Kasası)
*   Kullanıcıya ait hassas veriler (API keyler, şifreler) **maskelenmiş token** olarak saklanacak.
*   Orchestrator, bu verilere erişirken sadece referans kullanacak; plaintext veri veritabanında tutulmayacak.

### 12.3 Connector Ekosistemi
*   **Tool-Host Bağlayıcıları**: WhatsApp, E-posta ve Dosya Sistemi erişimi için "Connector" mimarisi kurulacak.
*   **Consent & Audit**: Her bir veri erişimi (örn. "Son 3 mailimi oku") kullanıcı onayına ve denetim loguna (audit trail) tabi olacak.

### 12.4 Proaktif Plans & Routines
*   **Proaktif Motor**: Kullanıcının rutinlerini (örn. "Her sabah 09:00'da borsa özeti") takip eden ve tetikleyen modül.
*   **Hybrid Input**: Hem sohbet içinden ("Her akşam bana hatırlat") hem de UI üzerinden yapılandırılmış veri girişi.

> **Güvenlik Notu (Dev/MVP)**: Geliştirme aşamasında Connector izinleri gevşek olabilir, ancak Production ortamında OAuth2 ve sıkı scope denetimi zorunludur.
