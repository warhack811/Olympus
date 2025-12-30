# Database Schema (SQLModel)

Aşağıdaki tablolar `app/core/models.py` içinde tanımlı; Alembic migration’ları `alembic/versions/` altında.

## Kullanıcı & Kimlik
- **users**: `id`, `username`, `password_hash`, `role`, `is_banned`, `selected_model`, `bela_unlocked`, `active_persona`, `limits` (JSON), `permissions` (JSON), `created_at`.
- **user_preferences**: `id`, `user_id`, `key`, `value` (Text), `category`, `source`, `is_active`, `updated_at`.
- **model_presets**: `id`, `name`, `description`, `system_prompt_template` (Text), `temperature`, `max_tokens`, `model_name`, `is_global`, `owner_id`.
- **sessions**: `id` (token), `user_id`, `type` (active_session/remember_token), `expires_at`, `user_agent`, `created_at`.
- **invites**: `code`, `created_by`, `is_used`, `used_by`, `used_at`, `created_at`.

## Sohbet & Hafıza
- **conversations**: `id` (uuid), `user_id`, `title`, `preset_id`, `created_at`, `updated_at`.
- **messages**: `id`, `conversation_id`, `role` (user/bot/system), `content` (Text), `extra_metadata` (JSON), `created_at`.
- **conversation_summaries**: `conversation_id`, `summary` (Text), `updated_at`, `message_count_at_update`, `last_message_id`.
- **conversation_summary_settings**: singleton `id=1`, `summary_enabled`, `summary_first_threshold`, `summary_update_step`, `summary_max_messages`, `updated_at`.
- **answer_cache**: `id`, `user_id`, `cache_key`, `question` (Text), `answer` (Text), `engine`, `created_at`, `expires_at`.
- **usage_counters**: `id`, `user_id`, `usage_date`, `groq_count`, `local_count`, `total_chat_count`.
- **feedback**: `id`, `user_id`, `conversation_id`, `message_content` (Text), `feedback_type` (like/dislike), `created_at`.

## Sistem Kimliği
- **ai_identity_config**: singleton `id=1`, `display_name`, `developer_name`, `product_family`, `short_intro` (Text), `forbid_provider_mention`, `updated_at`.

## Notlar
- Tüm modeller SQLModel ile tanımlı; JSON alanlar Postgres/SQLite JSON sütunları olarak tutuluyor.
- Migration’lar Alembic ile yönetiliyor; mevcut versiyon dosyaları `alembic/versions/` altında.
