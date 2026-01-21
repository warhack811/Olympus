# Docker Production Readiness - Proje Temizlik Analizi

## Özet

Mami AI projesinde Docker'a geçmeden önce temizlenmesi gereken **çöp dosyalar**, **eski konfigürasyonlar**, **test dosyaları** ve **yedek klasörler** tespit edilmiştir. Bu analiz, projeyi temiz ve production-ready hale getirmek için yapılmıştır.

---

## 1. Kök Dizinindeki Çöp Dosyalar

### 1.1 Eski Dokümantasyon Dosyaları (Silinecek)

Bu dosyalar, geçmiş faz tamamlama raporlarıdır ve artık geçerli değildir:

| Dosya | Neden Silinmeli | Boyut | Öncelik |
|-------|-----------------|-------|---------|
| `CHAT_SYSTEM_FIXES_VERIFICATION.md` | Eski faz raporu | ~5KB | YÜKSEK |
| `DOCKER_CHANGES_SUMMARY.md` | Eski Docker notları | ~3KB | YÜKSEK |
| `DOCKER_HAZIR.md` | Türkçe eski not | ~2KB | YÜKSEK |
| `DOCKER_KURULUM.md` | Türkçe eski not | ~2KB | YÜKSEK |
| `DOCKER_READY.md` | Eski Docker not | ~2KB | YÜKSEK |
| `DOCKER_SETUP.md` | Eski Docker not | ~2KB | YÜKSEK |
| `FAZE_2_COMPLETION_SUMMARY.md` | Eski faz raporu | ~8KB | YÜKSEK |
| `FAZE_2_DELIVERABLES.md` | Eski faz raporu | ~5KB | YÜKSEK |
| `FAZE_2_EXECUTIVE_SUMMARY.md` | Eski faz raporu | ~4KB | YÜKSEK |
| `FAZE_2_FINAL_VERIFICATION.md` | Eski faz raporu | ~6KB | YÜKSEK |
| `FAZE_3_COMPLETION.md` | Eski faz raporu | ~4KB | YÜKSEK |
| `FAZE_4_COMPLETION.md` | Eski faz raporu | ~3KB | YÜKSEK |
| `FINAL_VERIFICATION.md` | Eski faz raporu | ~5KB | YÜKSEK |
| `IMAGE_GENERATION_ANALYSIS.md` | Eski analiz | ~8KB | ORTA |
| `IMPLEMENTATION_STATUS.md` | Eski durum raporu | ~6KB | ORTA |
| `IMPLEMENTATION_SUMMARY.md` | Eski özet | ~5KB | ORTA |
| `PHASE_1_TEST_RESULTS.md` | Eski test sonuçları | ~4KB | ORTA |
| `PHASE_2_SPECIFICATION_SUMMARY.md` | Eski spec özeti | ~6KB | ORTA |
| `QUEUE_POSITION_FIX_FINAL.md` | Eski fix raporu | ~4KB | ORTA |
| `QUEUE_POSITION_FIX_SUMMARY.md` | Eski fix raporu | ~3KB | ORTA |
| `TEST_PLAN.md` | Eski test planı | ~4KB | ORTA |

**Toplam Boyut:** ~110 KB

**Aksiyon:** Tüm bu dosyaları silin. Gerekli bilgiler `.kiro/specs/` ve `docs/` klasörlerinde saklanmalıdır.

---

### 1.2 Test Sonuç Dosyaları (Silinecek)

Bu dosyalar, geçmiş test çalıştırmalarının sonuçlarıdır:

| Dosya | Neden Silinmeli | Boyut | Öncelik |
|-------|-----------------|-------|---------|
| `gemini_test_results.txt` | Eski test sonucu | ~2KB | YÜKSEK |
| `gemini_test_results_v2.txt` | Eski test sonucu | ~2KB | YÜKSEK |
| `gemini_test_results_v3.txt` | Eski test sonucu | ~2KB | YÜKSEK |
| `gemini_test_results_v4.txt` | Eski test sonucu | ~2KB | YÜKSEK |
| `gemini_test_results_v5.txt` | Eski test sonucu | ~2KB | YÜKSEK |

**Toplam Boyut:** ~10 KB

**Aksiyon:** Tüm bu dosyaları silin. Test sonuçları CI/CD pipeline'ında otomatik olarak oluşturulmalıdır.

---

### 1.3 Standalone Test Dosyaları (Silinecek)

Bu dosyalar, kök dizinde bulunan ve proje yapısına uygun olmayan test dosyalarıdır:

| Dosya | Neden Silinmeli | Boyut | Öncelik |
|-------|-----------------|-------|---------|
| `hello_world.py` | Örnek/test dosyası | ~1KB | YÜKSEK |
| `test_gemini.py` | Standalone test | ~2KB | YÜKSEK |
| `worker_local.py` | Eski worker dosyası | ~3KB | YÜKSEK |

**Toplam Boyut:** ~6 KB

**Aksiyon:** Tüm bu dosyaları silin. Eğer gerekli ise `tests/` klasörüne taşıyın.

---

### 1.4 Konfigürasyon Dosyaları (Gözden Geçirilecek)

| Dosya | Durum | Aksiyon |
|-------|-------|--------|
| `.roomodes` | Bilinmeyen amaç | Kontrol et, gerekli değilse sil |
| `.pre-commit-config.yaml` | Pre-commit hooks | Kontrol et, Docker'da gerekli mi? |
| `Makefile` | Build otomasyonu | Kontrol et, Docker Compose ile değiştirilmeli mi? |

---

## 2. Yedek ve Arşiv Klasörleri

### 2.1 `backups/` Klasörü (Silinecek)

```
backups/
├── graveyard/              # Eski kod parçaları
│   ├── __pycache__/
│   ├── orchestrator_v42/
│   ├── plugins/
│   └── tools/
├── ranking_v4.5_pre/       # Eski ranking versiyonu
│   ├── backend/
│   └── frontend/
└── standalone_router/      # Eski router implementasyonu
```

**Neden Silinmeli:**
- Eski versiyonların yedekleri
- Git history'de zaten saklanmış
- Proje boyutunu gereksiz yere artırıyor
- Docker imajında yer kaybı

**Aksiyon:** Tüm `backups/` klasörünü silin.

---

### 2.2 `_ui_backup/` Klasörü (Silinecek)

```
_ui_backup/
└── ui/
    ├── app.js
    ├── arena.html
    ├── arena.js
    ├── index.html
    └── styles.css
```

**Neden Silinmeli:**
- Eski UI implementasyonu
- `ui-new/` yeni React uygulaması ile değiştirilmiş
- Git history'de saklanmış
- Docker imajında yer kaybı

**Aksiyon:** Tüm `_ui_backup/` klasörünü silin.

---

## 3. Veri Klasörleri (Dikkatli Temizlik)

### 3.1 `data/` Klasörü (Seçici Temizlik)

```
data/
├── api_daily_usage.json      # Eski API istatistikleri
├── api_stats.json            # Eski API istatistikleri
├── app.db                    # SQLite veritabanı (SAKLA)
├── app.db-shm                # SQLite WAL dosyası (SAKLA)
├── app.db-wal                # SQLite WAL dosyası (SAKLA)
├── chroma_db/                # ChromaDB vektör depolama (SAKLA)
├── eval_results.json         # Eski eval sonuçları
├── feature_flags.json        # Feature flags (SAKLA)
├── images/                   # Kullanıcı yüklenen görseller (SAKLA)
├── rag_v2_fts.db            # RAG FTS veritabanı (SAKLA)
├── rag_v2_telemetry.jsonl   # RAG telemetri (SAKLA)
└── uploads/                  # Kullanıcı yüklemeleri (SAKLA)
```

**Temizlenecek Dosyalar:**
- `api_daily_usage.json` - Eski istatistikler
- `api_stats.json` - Eski istatistikler
- `eval_results.json` - Eski eval sonuçları

**Saklanacak Dosyalar:**
- `app.db*` - Veritabanı
- `chroma_db/` - Vektör depolama
- `feature_flags.json` - Aktif konfigürasyon
- `images/` - Kullanıcı veri
- `rag_v2_*` - RAG sistemi veri
- `uploads/` - Kullanıcı veri

**Aksiyon:** Eski istatistik dosyalarını silin, veri dosyalarını sakla.

---

### 3.2 `logs/` Klasörü (Seçici Temizlik)

```
logs/
├── deletion_audit.jsonl      # Audit log (SAKLA)
├── mami.log                  # Aktif log (SAKLA)
└── mami.log.3                # Eski log (SİL)
```

**Temizlenecek Dosyalar:**
- `mami.log.3` - Eski rotated log

**Saklanacak Dosyalar:**
- `deletion_audit.jsonl` - Audit trail
- `mami.log` - Aktif log

**Aksiyon:** Eski log dosyalarını silin, aktif logları sakla.

---

## 4. Test Dosyaları (Gözden Geçirilecek)

### 4.1 `tests/` Klasörü Analizi

**Sorunlu Test Dosyaları:**

| Dosya | Neden Sorunlu | Aksiyon |
|-------|---------------|--------|
| `auto_integration_test.py` | Eski integration test | Kontrol et, gerekli değilse sil |
| `check_ids.py` | Debug script | Sil |
| `check_search_config.py` | Debug script | Sil |
| `cleanup_test_rag.py` | Debug script | Sil |
| `debug_search.py` | Debug script | Sil |
| `detailed_search_diag.py` | Debug script | Sil |
| `dry_run_stream.py` | Debug script | Sil |
| `inject_test_rag.py` | Debug script | Sil |
| `live_api_test.py` | Manual test | Sil veya `manual_tests/` taşı |
| `manual_image_trigger.py` | Manual test | Sil veya `manual_tests/` taşı |
| `persona_test.py` | Manual test | Sil veya `manual_tests/` taşı |
| `rag_live_test.py` | Manual test | Sil veya `manual_tests/` taşı |
| `reproduce_issues.py` | Debug script | Sil |
| `reproduce_search.py` | Debug script | Sil |
| `test_ui_queue_position_updates.tsx` | TypeScript test (Python klasöründe) | Taşı veya sil |
| `verify_intent.py` | Debug script | Sil |
| `verify_secret.py` | Debug script | Sil |
| `verify_tck.py` | Debug script | Sil |

**Toplam Silinecek:** ~18 dosya

**Aksiyon:** Debug ve manual test dosyalarını silin. Resmi test dosyaları (`test_*.py` pattern'ı ile başlayanlar) saklanmalıdır.

---

## 5. Konfigürasyon Dosyaları (Gözden Geçirilecek)

### 5.1 `.vscode/` Klasörü

```
.vscode/
└── settings.json
```

**Durum:** Geliştirici konfigürasyonu, `.gitignore`'a eklenmelidir.

**Aksiyon:** `.gitignore`'a ekle, repo'dan kaldır.

---

### 5.2 `.clinerules/` Klasörü

```
.clinerules/
└── mami-ai.md
```

**Durum:** Kiro IDE kuralları, saklanabilir.

**Aksiyon:** Sakla (gerekli değilse silebilir).

---

## 6. Node.js Bağımlılıkları (Dikkatli Temizlik)

### 6.1 `node_modules/` Klasörü (Silinecek)

**Neden Silinmeli:**
- Docker'da `npm install` ile yeniden oluşturulacak
- Boyutu çok büyük (~500MB+)
- Git'te saklanmamalı (`.gitignore`'da olmalı)
- Platform-specific binary'ler içerebilir

**Aksiyon:** Tüm `node_modules/` klasörünü silin.

---

### 6.2 `package-lock.json` (Kök Dizin)

**Durum:** Kök dizinde `package.json` yoksa bu dosya gereksizdir.

**Aksiyon:** Kontrol et, gerekli değilse sil.

---

## 7. Python Bağımlılıkları (Dikkatli Temizlik)

### 7.1 `.venv/` Klasörü (Silinecek)

**Neden Silinmeli:**
- Docker'da yeniden oluşturulacak
- Boyutu çok büyük (~500MB+)
- Platform-specific binary'ler içerir
- `.gitignore`'da olmalı

**Aksiyon:** Tüm `.venv/` klasörünü silin.

---

### 7.2 `__pycache__/` Klasörleri (Silinecek)

**Nerede Bulunur:**
- `app/__pycache__/`
- `alembic/__pycache__/`
- `tests/__pycache__/`
- Tüm alt klasörlerde

**Neden Silinmeli:**
- Python bytecode cache
- Platform-specific
- `.gitignore`'da olmalı
- Docker'da yeniden oluşturulacak

**Aksiyon:** Tüm `__pycache__/` klasörlerini silin.

---

## 8. Docs Klasörü (Gözden Geçirilecek)

### 8.1 `docs/` Klasörü Analizi

```
docs/
├── FAZ1_COMPLETION_REPORT.md          # Eski faz raporu
├── FAZ1_IMPLEMENTATION_PLAN.md        # Eski plan
├── FAZ2_IMPLEMENTATION_PLAN.md        # Eski plan
├── FAZ2_RECOMMENDATIONS.md            # Eski öneriler
├── FAZ2A_COMPLETION_REPORT.md         # Eski faz raporu
├── IMAGE_PIPELINE_ANALYSIS.md         # Analiz (SAKLA)
├── KNOWN_ISSUES.md                    # Bilinen sorunlar (SAKLA)
├── MEMORY_DEBUG_ANALYSIS.md           # Debug analizi (SAKLA)
├── router_analysis.md                 # Router analizi (SAKLA)
├── ROUTER_LAYERS_ANALYSIS.md          # Router analizi (SAKLA)
└── ROUTER_TOOL_COMPARISON.md          # Router karşılaştırması (SAKLA)
```

**Temizlenecek Dosyalar:**
- `FAZ1_COMPLETION_REPORT.md`
- `FAZ1_IMPLEMENTATION_PLAN.md`
- `FAZ2_IMPLEMENTATION_PLAN.md`
- `FAZ2_RECOMMENDATIONS.md`
- `FAZ2A_COMPLETION_REPORT.md`

**Saklanacak Dosyalar:**
- `IMAGE_PIPELINE_ANALYSIS.md`
- `KNOWN_ISSUES.md`
- `MEMORY_DEBUG_ANALYSIS.md`
- `router_analysis.md`
- `ROUTER_LAYERS_ANALYSIS.md`
- `ROUTER_TOOL_COMPARISON.md`

**Aksiyon:** Eski faz raporlarını silin, teknik analizleri sakla.

---

## 9. Scripts Klasörü (Gözden Geçirilecek)

### 9.1 `scripts/` Klasörü Analizi

```
scripts/
├── __init__.py                        # SAKLA
├── create_placeholder_images.py       # Utility (SAKLA)
├── generate_word_report.py            # Utility (SAKLA)
├── groq_models.json                   # Konfigürasyon (SAKLA)
├── launcher.pyw                       # Windows launcher (SİL)
├── mobile_test.bat                    # Windows batch (SİL)
├── request_context_smoke.py           # Test script (SAKLA)
├── start_backend_only.bat             # Windows batch (SİL)
├── start.bat                          # Windows batch (SİL)
├── verify_phase2.py                   # Eski verify script (SİL)
├── verify_phase3.py                   # Eski verify script (SİL)
├── verify_phase4.py                   # Eski verify script (SİL)
└── verify_refactor_phase1.py          # Eski verify script (SİL)
```

**Temizlenecek Dosyalar:**
- `launcher.pyw` - Windows GUI launcher
- `mobile_test.bat` - Windows batch
- `start_backend_only.bat` - Windows batch
- `start.bat` - Windows batch
- `verify_phase2.py` - Eski verify
- `verify_phase3.py` - Eski verify
- `verify_phase4.py` - Eski verify
- `verify_refactor_phase1.py` - Eski verify

**Saklanacak Dosyalar:**
- `__init__.py`
- `create_placeholder_images.py`
- `generate_word_report.py`
- `groq_models.json`
- `request_context_smoke.py`

**Aksiyon:** Windows batch dosyalarını ve eski verify scriptlerini silin.

---

## 10. .gitignore Güncellemesi

Aşağıdaki dosyalar `.gitignore`'a eklenmelidir:

```gitignore
# Bağımlılıklar
node_modules/
.venv/
venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Ortam
.env
.env.local
.env.*.local

# Veri (geliştirme)
data/api_*.json
data/eval_results.json
logs/*.log.*

# OS
.DS_Store
Thumbs.db

# Test
.pytest_cache/
.coverage
htmlcov/

# Build
ui-new/dist/
```

---

## 11. Temizlik Aksiyon Planı

### Faz 1: Yüksek Öncelik (Hemen Silinecek)

```bash
# Kök dizin çöp dosyaları
rm -f CHAT_SYSTEM_FIXES_VERIFICATION.md
rm -f DOCKER_CHANGES_SUMMARY.md
rm -f DOCKER_HAZIR.md
rm -f DOCKER_KURULUM.md
rm -f DOCKER_READY.md
rm -f DOCKER_SETUP.md
rm -f FAZE_*.md
rm -f FINAL_VERIFICATION.md
rm -f gemini_test_results*.txt
rm -f hello_world.py
rm -f test_gemini.py
rm -f worker_local.py

# Yedek klasörleri
rm -rf backups/
rm -rf _ui_backup/

# Veri temizliği
rm -f data/api_*.json
rm -f data/eval_results.json
rm -f logs/mami.log.*

# Test debug dosyaları
rm -f tests/check_*.py
rm -f tests/cleanup_*.py
rm -f tests/debug_*.py
rm -f tests/detailed_*.py
rm -f tests/dry_run_*.py
rm -f tests/inject_*.py
rm -f tests/live_*.py
rm -f tests/manual_*.py
rm -f tests/persona_*.py
rm -f tests/rag_live_*.py
rm -f tests/reproduce_*.py
rm -f tests/verify_*.py
rm -f tests/test_ui_queue_position_updates.tsx

# Scripts temizliği
rm -f scripts/launcher.pyw
rm -f scripts/mobile_test.bat
rm -f scripts/start_backend_only.bat
rm -f scripts/start.bat
rm -f scripts/verify_*.py

# Docs temizliği
rm -f docs/FAZ*.md
```

### Faz 2: Orta Öncelik (Gözden Geçirildikten Sonra)

```bash
# Eski dokümantasyon
rm -f IMAGE_GENERATION_ANALYSIS.md
rm -f IMPLEMENTATION_STATUS.md
rm -f IMPLEMENTATION_SUMMARY.md
rm -f PHASE_*.md
rm -f QUEUE_POSITION_FIX_*.md
rm -f TEST_PLAN.md

# Bağımlılık klasörleri
rm -rf node_modules/
rm -rf .venv/
find . -type d -name __pycache__ -exec rm -rf {} +
```

### Faz 3: Konfigürasyon Güncellemeleri

```bash
# .gitignore güncelle
# .vscode/ ekle
# node_modules/ ekle
# .venv/ ekle
# __pycache__/ ekle
```

---

## 12. Temizlik Sonrası Boyut Tahmini

| Kategori | Silinecek Boyut | Tasarruf |
|----------|-----------------|---------|
| Kök dokümantasyon | ~150 KB | ✓ |
| Test sonuçları | ~10 KB | ✓ |
| Yedek klasörleri | ~50 MB | ✓✓✓ |
| node_modules | ~500 MB | ✓✓✓ |
| .venv | ~500 MB | ✓✓✓ |
| __pycache__ | ~50 MB | ✓✓ |
| Eski docs | ~30 KB | ✓ |
| **TOPLAM** | **~1.1 GB** | **✓✓✓** |

---

## 13. Docker İmaj Boyutu Etkisi

**Temizlik Öncesi Tahmini:**
- Base Python 3.11 slim: ~150 MB
- Python bağımlılıkları: ~200 MB
- Proje kodu: ~100 MB
- Çöp dosyalar: ~1.1 GB
- **TOPLAM:** ~1.55 GB

**Temizlik Sonrası Tahmini:**
- Base Python 3.11 slim: ~150 MB
- Python bağımlılıkları: ~200 MB
- Proje kodu: ~100 MB
- **TOPLAM:** ~450 MB

**Tasarruf:** ~1.1 GB (%71 azalma)

---

## 14. Temizlik Kontrol Listesi

- [ ] Kök dizin çöp dosyaları silindi
- [ ] Yedek klasörleri silindi
- [ ] Test debug dosyaları silindi
- [ ] Eski dokümantasyon silindi
- [ ] Veri klasörü temizlendi (seçici)
- [ ] Logs klasörü temizlendi (seçici)
- [ ] Scripts klasörü temizlendi
- [ ] Docs klasörü temizlendi
- [ ] .gitignore güncellendi
- [ ] node_modules silindi
- [ ] .venv silindi
- [ ] __pycache__ silindi
- [ ] Git commit yapıldı: "chore: cleanup project for Docker production readiness"

---

## 15. Ek Öneriler

### 15.1 `.dockerignore` Dosyası

Docker build sırasında gereksiz dosyaları hariç tutmak için:

```dockerfile
# .dockerignore
.git
.github
.venv
node_modules
__pycache__
*.pyc
.pytest_cache
.coverage
htmlcov
.vscode
.idea
*.log
data/api_*.json
data/eval_results.json
backups/
_ui_backup/
docs/
tests/
scripts/
.env
.env.local
```

### 15.2 `.gitignore` Güncellemesi

Zaten `.gitignore`'da olması gereken dosyalar:

```gitignore
# Bağımlılıklar
node_modules/
.venv/
venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/

# IDE
.vscode/
.idea/

# Ortam
.env
.env.local

# Veri
data/api_*.json
data/eval_results.json
logs/*.log.*
```

### 15.3 GitHub Actions Workflow

Temizlik sonrası, GitHub Actions workflow'u şu şekilde olmalıdır:

```yaml
name: Docker Build & Push

on:
  push:
    branches: [main, develop]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t mami-ai:latest .
      
      - name: Test Docker image
        run: docker run --rm mami-ai:latest python -c "import app; print('OK')"
      
      - name: Push to registry
        run: docker push mami-ai:latest
```

---

## Sonuç

Proje temizliği yapıldıktan sonra:

1. **Docker imajı boyutu %71 azalacak** (~1.55 GB → ~450 MB)
2. **Proje yapısı daha temiz ve anlaşılır olacak**
3. **Git repository daha hafif olacak**
4. **CI/CD pipeline daha hızlı çalışacak**
5. **Production deployment daha güvenilir olacak**

Temizlik, Docker production readiness'ın ilk adımıdır.
