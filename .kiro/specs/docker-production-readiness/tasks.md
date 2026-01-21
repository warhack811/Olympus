# Docker Production Readiness - Uygulama Görevleri

## Genel Bilgi

Bu dosya, Mami AI projesini Docker'a geçmek için gerekli tüm görevleri tanımlar. Görevler sırasıyla uygulanmalıdır.

**Toplam Görev Sayısı:** 21
**Tahmini Süre:** 4-6 saat
**Zorluk Seviyesi:** Orta

---

## Faz 1: Proje Temizliği (Yüksek Öncelik)

### 1.1 Kök Dizin Çöp Dosyalarını Sil

- [ ] 1.1 Kök dizin eski dokümantasyon dosyalarını sil (20 dosya)

**Detaylar:**
- Silinecek dosyalar: CHAT_SYSTEM_FIXES_VERIFICATION.md, DOCKER_*.md, FAZE_*.md, FINAL_VERIFICATION.md, IMAGE_GENERATION_ANALYSIS.md, IMPLEMENTATION_*.md, PHASE_*.md, QUEUE_POSITION_FIX_*.md, TEST_PLAN.md
- Komut: `rm -f CHAT_SYSTEM_FIXES_VERIFICATION.md DOCKER_*.md FAZE_*.md ...`
- Doğrulama: `ls -la | grep -E "(FAZE|DOCKER|FINAL|IMPLEMENTATION|PHASE|QUEUE|TEST_PLAN)"`

### 1.2 Test Sonuç Dosyalarını Sil

- [ ] 1.2 Test sonuç dosyalarını sil (5 dosya)

**Detaylar:**
- Silinecek dosyalar: gemini_test_results*.txt
- Komut: `rm -f gemini_test_results*.txt`
- Doğrulama: `ls -la gemini_test_results*.txt 2>&1 | grep "No such file"`

### 1.3 Standalone Test Dosyalarını Sil

- [ ] 1.3 Standalone test dosyalarını sil (3 dosya)

**Detaylar:**
- Silinecek dosyalar: hello_world.py, test_gemini.py, worker_local.py
- Komut: `rm -f hello_world.py test_gemini.py worker_local.py`
- Doğrulama: `ls -la hello_world.py test_gemini.py worker_local.py 2>&1 | grep "No such file"`

---

## Faz 2: Yedek Klasörleri Temizliği

### 2.1 Backups Klasörünü Sil

- [ ] 2.1 backups/ klasörünü sil (~50 MB)

**Detaylar:**
- Silinecek klasör: backups/ (graveyard, ranking_v4.5_pre, standalone_router)
- Komut: `rm -rf backups/`
- Doğrulama: `ls -la backups 2>&1 | grep "No such file"`
- Tasarruf: ~50 MB

### 2.2 UI Backup Klasörünü Sil

- [ ] 2.2 _ui_backup/ klasörünü sil (~5 MB)

**Detaylar:**
- Silinecek klasör: _ui_backup/ (eski UI implementasyonu)
- Komut: `rm -rf _ui_backup/`
- Doğrulama: `ls -la _ui_backup 2>&1 | grep "No such file"`
- Tasarruf: ~5 MB

---

## Faz 3: Test Debug Dosyaları Temizliği

### 3.1 Test Debug Dosyalarını Sil

- [ ] 3.1 tests/ klasöründeki debug dosyalarını sil (18 dosya)

**Detaylar:**
- Silinecek dosyalar: check_*.py, cleanup_*.py, debug_*.py, detailed_*.py, dry_run_*.py, inject_*.py, live_*.py, manual_*.py, persona_*.py, rag_live_*.py, reproduce_*.py, verify_*.py, test_ui_queue_position_updates.tsx, auto_integration_test.py
- Komut: `rm -f tests/check_*.py tests/cleanup_*.py tests/debug_*.py tests/detailed_*.py tests/dry_run_*.py tests/inject_*.py tests/live_*.py tests/manual_*.py tests/persona_*.py tests/rag_live_*.py tests/reproduce_*.py tests/verify_*.py tests/test_ui_queue_position_updates.tsx tests/auto_integration_test.py`
- Doğrulama: `ls -la tests/ | grep -E "(check_|cleanup_|debug_|detailed_|dry_run_|inject_|live_|manual_|persona_|rag_live_|reproduce_|verify_|test_ui_queue_position_updates|auto_integration_test)" | wc -l` (0 olmalı)

---

## Faz 4: Scripts Temizliği

### 4.1 Windows Batch Dosyalarını Sil

- [ ] 4.1 scripts/ klasöründeki Windows batch dosyalarını sil (4 dosya)

**Detaylar:**
- Silinecek dosyalar: launcher.pyw, mobile_test.bat, start_backend_only.bat, start.bat
- Komut: `rm -f scripts/launcher.pyw scripts/mobile_test.bat scripts/start_backend_only.bat scripts/start.bat`
- Doğrulama: `ls -la scripts/*.bat scripts/*.pyw 2>&1 | grep "No such file"`

### 4.2 Eski Verify Scriptlerini Sil

- [ ] 4.2 scripts/ klasöründeki eski verify scriptlerini sil (4 dosya)

**Detaylar:**
- Silinecek dosyalar: verify_phase2.py, verify_phase3.py, verify_phase4.py, verify_refactor_phase1.py
- Komut: `rm -f scripts/verify_phase*.py scripts/verify_refactor_*.py`
- Doğrulama: `ls -la scripts/verify_*.py 2>&1 | grep "No such file"`

---

## Faz 5: Dokümantasyon Temizliği

### 5.1 Eski Faz Raporlarını Sil

- [ ] 5.1 docs/ klasöründeki eski faz raporlarını sil (5 dosya)

**Detaylar:**
- Silinecek dosyalar: FAZ1_COMPLETION_REPORT.md, FAZ1_IMPLEMENTATION_PLAN.md, FAZ2_IMPLEMENTATION_PLAN.md, FAZ2_RECOMMENDATIONS.md, FAZ2A_COMPLETION_REPORT.md
- Komut: `rm -f docs/FAZ*.md`
- Doğrulama: `ls -la docs/FAZ*.md 2>&1 | grep "No such file"`
- Not: Teknik analizler (IMAGE_PIPELINE_ANALYSIS.md, KNOWN_ISSUES.md, MEMORY_DEBUG_ANALYSIS.md, router_analysis.md, ROUTER_LAYERS_ANALYSIS.md, ROUTER_TOOL_COMPARISON.md) saklanmalıdır

---

## Faz 6: Veri Temizliği

### 6.1 Eski İstatistik Dosyalarını Sil

- [ ] 6.1 data/ klasöründeki eski istatistik dosyalarını sil (3 dosya)

**Detaylar:**
- Silinecek dosyalar: api_daily_usage.json, api_stats.json, eval_results.json
- Komut: `rm -f data/api_daily_usage.json data/api_stats.json data/eval_results.json`
- Doğrulama: `ls -la data/api_*.json data/eval_results.json 2>&1 | grep "No such file"`
- Not: data/app.db, data/chroma_db/, data/feature_flags.json, data/images/, data/rag_v2_*, data/uploads/ saklanmalıdır

### 6.2 Eski Log Dosyalarını Sil

- [ ] 6.2 logs/ klasöründeki eski log dosyalarını sil (1 dosya)

**Detaylar:**
- Silinecek dosyalar: mami.log.3 (ve diğer rotated logs)
- Komut: `rm -f logs/mami.log.*`
- Doğrulama: `ls -la logs/mami.log.* 2>&1 | grep "No such file"`
- Not: logs/mami.log ve logs/deletion_audit.jsonl saklanmalıdır

---

## Faz 7: Bağımlılık Klasörleri Temizliği

### 7.1 Node.js Bağımlılıklarını Sil

- [ ] 7.1 node_modules/ klasörünü sil (~500 MB)

**Detaylar:**
- Silinecek klasör: node_modules/ (kök ve ui-new/)
- Komut: `rm -rf node_modules/ ui-new/node_modules/`
- Doğrulama: `ls -la node_modules 2>&1 | grep "No such file"` ve `ls -la ui-new/node_modules 2>&1 | grep "No such file"`
- Tasarruf: ~500 MB
- Not: Docker'da `npm install` ile yeniden oluşturulacak

### 7.2 Python Virtual Environment'ı Sil

- [ ] 7.2 .venv/ klasörünü sil (~500 MB)

**Detaylar:**
- Silinecek klasör: .venv/
- Komut: `rm -rf .venv/`
- Doğrulama: `ls -la .venv 2>&1 | grep "No such file"`
- Tasarruf: ~500 MB
- Not: Docker'da `pip install` ile yeniden oluşturulacak

### 7.3 Python Cache Dosyalarını Sil

- [ ] 7.3 __pycache__/ klasörlerini sil (~50 MB)

**Detaylar:**
- Silinecek klasörler: Tüm __pycache__/ klasörleri
- Komut: `find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true`
- Doğrulama: `find . -type d -name __pycache__ | wc -l` (0 olmalı)
- Tasarruf: ~50 MB

---

## Faz 8: Konfigürasyon Güncellemeleri

### 8.1 .gitignore Dosyasını Güncelle

- [ ] 8.1 .gitignore dosyasını güncelle

**Detaylar:**
- Eklenecek satırlar:
  ```
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
- Doğrulama: `grep -E "(node_modules|\.venv|__pycache__|\.vscode)" .gitignore`

### 8.2 .dockerignore Dosyasını Oluştur

- [ ] 8.2 .dockerignore dosyasını oluştur

**Detaylar:**
- Oluşturulacak dosya: .dockerignore
- İçerik:
  ```
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
- Doğrulama: `cat .dockerignore | head -5`

---

## Faz 9: Git Operasyonları

### 9.1 Git Status Kontrol Et

- [ ] 9.1 Git status kontrol et

**Detaylar:**
- Komut: `git status`
- Doğrulama: Tüm silinmiş dosyalar "deleted" olarak gösterilmeli
- Not: Hiçbir dosya staged olmamalı

### 9.2 Tüm Değişiklikleri Stage Et

- [ ] 9.2 Tüm değişiklikleri stage et

**Detaylar:**
- Komut: `git add -A`
- Doğrulama: `git status` (tüm dosyalar staged olmalı)

### 9.3 Git Commit Yap

- [ ] 9.3 Git commit yap

**Detaylar:**
- Komut: `git commit -m "chore: cleanup project for Docker production readiness"`
- Doğrulama: `git log --oneline | head -1`

### 9.4 Git Push Yap

- [ ] 9.4 Git push yap

**Detaylar:**
- Komut: `git push origin main` (veya current branch)
- Doğrulama: GitHub'da commit görüntülenmeli

---

## Faz 10: Docker Build ve Test

### 10.1 Docker İmajını Build Et

- [ ] 10.1 Docker imajını build et

**Detaylar:**
- Komut: `docker build -t mami-ai:latest .`
- Doğrulama: `docker images | grep mami-ai`
- Beklenen: Build başarılı, imaj boyutu ~450 MB

### 10.2 Docker İmaj Boyutunu Kontrol Et

- [ ] 10.2 Docker imaj boyutunu kontrol et

**Detaylar:**
- Komut: `docker images mami-ai:latest --format "{{.Size}}"`
- Doğrulama: Boyut ~450 MB olmalı (temizlik öncesi ~1.55 GB)
- Tasarruf: %71 azalma

### 10.3 Docker Konteynerini Test Et

- [ ] 10.3 Docker konteynerini test et

**Detaylar:**
- Komut: `docker run --rm mami-ai:latest python -c "import app; print('OK')"`
- Doğrulama: "OK" çıktısı görülmeli

### 10.4 Docker Compose Test Et

- [ ] 10.4 Docker Compose test et

**Detaylar:**
- Komut: `docker-compose up -d`
- Doğrulama: `docker-compose ps` (tüm servisler "Up" olmalı)
- Health check: `docker-compose ps | grep healthy`

### 10.5 Health Check Kontrol Et

- [ ] 10.5 Health check kontrol et

**Detaylar:**
- Komut: `curl http://localhost:8000/health`
- Doğrulama: `{"status": "ok", "app": "Mami AI"}` döndürülmeli
- Timeout: 30 saniye

### 10.6 Docker Compose Kapat

- [ ] 10.6 Docker Compose kapat

**Detaylar:**
- Komut: `docker-compose down`
- Doğrulama: `docker-compose ps` (boş olmalı)

---

## Faz 11: Doğrulama ve Raporlama

### 11.1 Temizlik Kontrol Listesini Tamamla

- [ ] 11.1 Temizlik kontrol listesini tamamla

**Detaylar:**
- Kontrol edilecek:
  - [ ] Kök dizin çöp dosyaları silindi
  - [ ] Yedek klasörleri silindi
  - [ ] Test debug dosyaları silindi
  - [ ] Scripts temizliği yapıldı
  - [ ] Docs temizliği yapıldı
  - [ ] Veri temizliği yapıldı
  - [ ] Bağımlılık klasörleri silindi
  - [ ] .gitignore güncellendi
  - [ ] .dockerignore oluşturuldu
  - [ ] Git commit yapıldı
  - [ ] Git push yapıldı
  - [ ] Docker build başarılı
  - [ ] Docker imaj boyutu azaldı
  - [ ] Docker Compose test başarılı
  - [ ] Health check geçti

### 11.2 Temizlik Raporu Oluştur

- [ ] 11.2 Temizlik raporu oluştur

**Detaylar:**
- Rapor içeriği:
  - Temizlik öncesi boyut: ~1.55 GB
  - Temizlik sonrası boyut: ~450 MB
  - Tasarruf: ~1.1 GB (%71 azalma)
  - Silinmiş dosya sayısı: ~60
  - Silinmiş klasör sayısı: ~5
  - Tamamlanma tarihi: [tarih]
  - Durum: ✅ Başarılı

### 11.3 Sonuç Belgesi Oluştur

- [ ] 11.3 Sonuç belgesi oluştur

**Detaylar:**
- Belge adı: CLEANUP_COMPLETION_REPORT.md
- İçerik:
  - Temizlik özeti
  - Yapılan işlemler
  - Tasarruf istatistikleri
  - Doğrulama sonuçları
  - Sonraki adımlar

---

## Ek Görevler (Opsiyonel)

### A.1 GitHub Actions Workflow Oluştur

- [ ]* A.1 GitHub Actions workflow oluştur

**Detaylar:**
- Dosya: .github/workflows/docker-build.yml
- İçerik: Docker build, test ve push
- Trigger: Push to main/develop

### A.2 Production Docker Compose Oluştur

- [ ]* A.2 Production Docker Compose oluştur

**Detaylar:**
- Dosya: docker-compose.prod.yml
- İçerik: Production-specific konfigürasyon
- Ayarlar: DEBUG=False, restart policies, resource limits

### A.3 Monitoring Dashboard Konfigüre Et

- [ ]* A.3 Monitoring dashboard konfigüre et

**Detaylar:**
- Grafana dashboard oluştur
- Prometheus alerting rules konfigüre et
- Elasticsearch logging konfigüre et

---

## Görev Tamamlama Kontrol Listesi

### Faz 1: Proje Temizliği
- [ ] 1.1 Kök dizin çöp dosyaları silindi
- [ ] 1.2 Test sonuç dosyaları silindi
- [ ] 1.3 Standalone test dosyaları silindi

### Faz 2: Yedek Klasörleri
- [ ] 2.1 backups/ silindi
- [ ] 2.2 _ui_backup/ silindi

### Faz 3: Test Debug Dosyaları
- [ ] 3.1 Test debug dosyaları silindi

### Faz 4: Scripts Temizliği
- [ ] 4.1 Windows batch dosyaları silindi
- [ ] 4.2 Eski verify scriptleri silindi

### Faz 5: Dokümantasyon Temizliği
- [ ] 5.1 Eski faz raporları silindi

### Faz 6: Veri Temizliği
- [ ] 6.1 Eski istatistik dosyaları silindi
- [ ] 6.2 Eski log dosyaları silindi

### Faz 7: Bağımlılık Klasörleri
- [ ] 7.1 node_modules/ silindi
- [ ] 7.2 .venv/ silindi
- [ ] 7.3 __pycache__/ silindi

### Faz 8: Konfigürasyon Güncellemeleri
- [ ] 8.1 .gitignore güncellendi
- [ ] 8.2 .dockerignore oluşturuldu

### Faz 9: Git Operasyonları
- [ ] 9.1 Git status kontrol edildi
- [ ] 9.2 Değişiklikler staged edildi
- [ ] 9.3 Git commit yapıldı
- [ ] 9.4 Git push yapıldı

### Faz 10: Docker Build ve Test
- [ ] 10.1 Docker imajı build edildi
- [ ] 10.2 Docker imaj boyutu kontrol edildi
- [ ] 10.3 Docker konteyner test edildi
- [ ] 10.4 Docker Compose test edildi
- [ ] 10.5 Health check kontrol edildi
- [ ] 10.6 Docker Compose kapatıldı

### Faz 11: Doğrulama ve Raporlama
- [ ] 11.1 Temizlik kontrol listesi tamamlandı
- [ ] 11.2 Temizlik raporu oluşturuldu
- [ ] 11.3 Sonuç belgesi oluşturuldu

---

## Tahmini Zaman Çizelgesi

| Faz | Görev | Tahmini Süre |
|-----|-------|-------------|
| 1 | Proje Temizliği | 5 dakika |
| 2 | Yedek Klasörleri | 10 dakika |
| 3 | Test Debug Dosyaları | 5 dakika |
| 4 | Scripts Temizliği | 5 dakika |
| 5 | Dokümantasyon Temizliği | 5 dakika |
| 6 | Veri Temizliği | 5 dakika |
| 7 | Bağımlılık Klasörleri | 30 dakika |
| 8 | Konfigürasyon Güncellemeleri | 10 dakika |
| 9 | Git Operasyonları | 5 dakika |
| 10 | Docker Build ve Test | 60 dakika |
| 11 | Doğrulama ve Raporlama | 10 dakika |
| **TOPLAM** | | **150 dakika (2.5 saat)** |

---

## Notlar

- Tüm görevler sırasıyla uygulanmalıdır
- Her görev tamamlandıktan sonra doğrulama yapılmalıdır
- Hata durumunda önceki adıma geri dönülmelidir
- Git commit'ler atomik olmalıdır (her faz için bir commit)
- Docker build süresi makinenin performansına bağlıdır

---

**Hazırlanma Tarihi:** 2026-01-21
**Durum:** Hazır Uygulanmaya
**Zorluk Seviyesi:** Orta
**Tahmini Süre:** 2.5-4 saat
