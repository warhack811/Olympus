# Architecture Overview

## Stack & Bileşenler
- **API Sunucusu (FastAPI)**: `app/main.py` giriş; router’lar `app/api/*.py`. Hem `/api/v1/*` hem de backward-compatible `/api/*` prefix’leri aktif.
- **Eklenti Katmanı**: `app/plugins/__init__.py` ile otomatik yükleme; Beautiful Response (cevap formatlama), RAG v2, Async Image gibi plugin’ler.
- **Sohbet Motoru**: `app/chat/processor.py` akışı; `smart_router` ile intent tespiti (IMAGE/INTERNET/LOCAL/GROQ), `response_processor` ile post-process. Prompts `app/ai/prompts/*`.
- **Görsel Üretim**: `app/chat/build_image_prompt` + `app/image/*` (routing, queue, manager, flux_stub). Markers: `[IMAGE_PENDING]`, `[IMAGE_QUEUED:job_id:message_id]`, `IMAGE_PATH:`.
- **Veritabanı**: SQLModel tabanlı modeller `app/core/models.py`; migration Alembic (`alembic/versions`). Dinamik ayarlar/kimlik: `AIIdentityConfig`, `ConversationSummarySettings`.
- **Ön Uç**: Yeni React/Vite arayüzü `ui-new/` (komponentler, stores). Legacy HTML/JS hâlâ mevcut fakat birincil arayüz `ui-new`.
- **Özellik bayrakları ve yapılandırma**: `app/core/feature_flags.py`, `.env`, `data/feature_flags.json`.

## Akışlar
- **Sohbet**: İstek `/api[/v1]/user/chat` → auth (session/invite) → `smart_router` (IMAGE/INTERNET/LOCAL/GROQ) → ilgili eylem (görsel kuyruğu, web araması, Groq/Local LLM) → streaming yanıt; post-process `app/services/response_processor.py` + Beautiful Response plugin.
- **Görsel üretim**: IMAGE intent → `build_image_prompt` (tek `!` ile ham prompt, guard kapalı; normalde çeviri+guard) → `request_image_generation` → iş kuyruğu `app/image/job_queue.py` → sonuç `IMAGE_PATH:` ile döner, statik servis `/images`.
- **Özetleme/Hafıza**: Context derleme `build_enhanced_context`; özetler `ConversationSummary`/`ConversationSummarySettings`; hafıza/RAG `app/memory/*`, RAG v2 plugin ile genişletilebilir.
- **Feature flag & persona**: `data/feature_flags.json`, `app/core/feature_flags.py`; personas/presets API’leri `app/api/user_routes.py`.

## Konfigürasyon & Gözlemlenebilirlik
- Konfig: `.env` + `app/config.py` (pydantic-settings). Dinamik ayarlar admin API üzerinden güncellenebilir.
- Loglama: `app/core/logger.py`; önemli akışlar (chat, image queue, plugins) log’lanıyor.
- Kullanım/güvenlik: `app/core/usage_limiter.py`, izin kontrolleri `app/auth/permissions.py`.
