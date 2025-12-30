# Critical Files Inventory

Güncel projedeki kritik dosya ve dizinler.

## Entrypoint & Konfig
- `app/main.py`: FastAPI uygulaması, router montajı, middleware.
- `app/config.py`: Pydantic settings, ortam değişkenleri.
- `app/core/feature_flags.py`, `data/feature_flags.json`: Özellik bayrakları.
- `app/websocket_sender.py`: WebSocket yardımcıları.

## Çekirdek & DB
- `app/core/database.py`: DB bağlantısı.
- `app/core/models.py`: SQLModel tabloları (User, Conversation, Message, Session, Invite, Feedback, AIIdentityConfig, ConversationSummarySettings vb.).
- `alembic/env.py`, `alembic/versions/`: Migration ayarları ve script’ler.
- `app/core/logger.py`, `app/core/usage_limiter.py`: Loglama ve oran/kota yönetimi.

## Kimlik & Yetki
- `app/auth/user_manager.py`: Varsayılan admin, kullanıcı yönetimi.
- `app/auth/permissions.py`: internet/local/image izin kontrolleri.
- `app/auth/session.py`, `app/auth/dependencies.py`: Oturum ve auth dependency’leri.
- `app/auth/invite_manager.py`: Davet kodu üretimi/validasyonu.

## Sohbet & AI
- `app/chat/processor.py`: Ana sohbet akışı, routing, image/internet/local kararları.
- `app/chat/smart_router.py`: IMAGE/INTERNET/LOCAL/GROQ intent tespiti.
- `app/chat/answerer.py`, `app/services/response_processor.py`: Yanıt üretimi ve post-process.
- `app/ai/prompts/*`: System prompt derleyici, image prompt guard/çeviri.
- `app/ai/groq/*`, `app/ai/ollama/gemma_handler.py`: Harici ve yerel model entegrasyonları.

## Pluginler
- `app/plugins/__init__.py`: Plugin yükleyici/registry.
- `app/plugins/beautiful_response/*`: Structured blocks parser/enhancer.
- `app/plugins/rag_v2/*`: RAG v2 geliştirmeleri.
- `app/plugins/async_image/*`: Asenkron görsel üretim görevi (celery yoksa fall-back).

## API Router’ları
- `app/api/user_routes.py`: Chat, dosya yükleme, hafıza, personas, görüntü işleri.
- `app/api/admin_routes.py`: Kullanıcı/özet/log/feedback/AI kimliği yönetimi.
- `app/api/public_routes.py`: Ping, login/logout, invite ile kayıt.
- `app/api/system_routes.py`: Feature toggle, health, overview.
- `app/api/auth_routes.py`: Mevcut kullanıcı bilgisi.

## Görsel Üretim
- `app/image/routing.py`, `app/image/image_manager.py`: Model seçimi, job başlatma.
- `app/image/job_queue.py`: Kuyruk ve worker mantığı.
- `app/image/flux_stub.py`: Yedek görsel üretim stub’ı.

## Hafıza & RAG
- `app/memory/conversation.py`, `app/memory/store.py`, `app/memory/rag.py`: Konuşma, vektör arama, RAG entegrasyonu.
- `app/services/semantic_classifier.py`, `app/services/query_enhancer.py`: Semantik analiz ve arama sorgusu iyileştirme.

## Frontend
- `ui-new/src/App.tsx` ve `ui-new/src/components/*`: Yeni React/Vite UI.
- `ui-new/src/stores/*`: Zustand store’lar.
- Legacy dosyalar `ui/` altında, ancak birincil arayüz `ui-new`.
