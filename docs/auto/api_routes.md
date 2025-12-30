# API Routes (güncel)

Tüm router’lar hem `/api/v1/*` hem de backward-compatible `/api/*` prefix’leriyle mount edilmiş. Aşağıdaki tablo v1 yollarını listeler.

| Method | Path | Handler | Auth |
|---|---|---|---|
| GET | /api/v1/public/ping | `public_routes:ping` | Public |
| POST | /api/v1/public/register_with_invite | `public_routes:register_with_invite` | Public |
| POST | /api/v1/public/login | `public_routes:login` | Public |
| POST | /api/v1/public/logout | `public_routes:logout` | Public |
| GET | /api/v1/auth/me | `auth_routes:get_current_user_info` | User |
| POST | /api/v1/user/chat | `user_routes:chat` | User |
| GET | /api/v1/user/conversations | `user_routes:get_conversations` | User |
| GET | /api/v1/user/conversations/{conversation_id} | `user_routes:get_conversation_messages` | User |
| DELETE | /api/v1/user/conversations/{conversation_id} | `user_routes:delete_conversation_endpoint` | User |
| POST | /api/v1/user/upload | `user_routes:upload_document` | User |
| GET | /api/v1/user/documents | `user_routes:list_user_documents` | User |
| DELETE | /api/v1/user/documents/{filename} | `user_routes:delete_user_document` | User |
| GET | /api/v1/user/image/status | `user_routes:check_image_status` | User |
| GET | /api/v1/user/image/job/{job_id}/status | `user_routes:get_job_status_endpoint` | User |
| POST | /api/v1/user/image/job/{job_id}/cancel | `user_routes:cancel_job_endpoint` | User |
| GET | /api/v1/user/images | `user_routes:list_user_images` | User |
| GET | /api/v1/user/memories | `user_routes:list_user_memories` | User |
| POST | /api/v1/user/memories | `user_routes:create_user_memory` | User |
| DELETE | /api/v1/user/memories/all-delete | `user_routes:delete_all_user_memories` | User |
| PUT | /api/v1/user/memories/{memory_id} | `user_routes:update_user_memory` | User |
| DELETE | /api/v1/user/memories/{memory_id} | `user_routes:delete_user_memory_endpoint` | User |
| POST | /api/v1/user/feedback | `user_routes:submit_feedback` | User |
| GET | /api/v1/user/preferences | `user_routes:get_my_preferences` | User |
| POST | /api/v1/user/preferences | `user_routes:set_my_preference` | User |
| GET | /api/v1/user/personas | `user_routes:list_personas` | User |
| GET | /api/v1/user/personas/active | `user_routes:get_active_persona` | User |
| POST | /api/v1/user/personas/select | `user_routes:select_persona` | User |
| GET | /api/v1/admin/me | `admin_routes:admin_me` | Admin |
| GET | /api/v1/admin/users | `admin_routes:admin_list_users` | Admin |
| PUT | /api/v1/admin/users/{username} | `admin_routes:admin_update_user` | Admin |
| GET | /api/v1/admin/invites | `admin_routes:admin_list_invites` | Admin |
| POST | /api/v1/admin/invites | `admin_routes:admin_create_invite` | Admin |
| DELETE | /api/v1/admin/invites/{code} | `admin_routes:admin_delete_invite` | Admin |
| GET | /api/v1/admin/summary | `admin_routes:admin_summary` | Admin |
| GET | /api/v1/admin/summary-settings | `admin_routes:admin_get_summary_settings` | Admin |
| PUT | /api/v1/admin/summary-settings | `admin_routes:admin_update_summary_settings` | Admin |
| GET | /api/v1/admin/logs/tail | `admin_routes:admin_logs_tail` | Admin |
| GET | /api/v1/admin/feedback | `admin_routes:admin_list_feedback` | Admin |
| GET | /api/v1/admin/usage/messages | `admin_routes:admin_list_messages` | Admin |
| GET | /api/v1/admin/ai-identity | `admin_routes:admin_get_ai_identity` | Admin |
| PUT | /api/v1/admin/ai-identity | `admin_routes:admin_update_ai_identity` | Admin |
| GET | /api/v1/system/health | `health_router:health` | Public |
| GET | /api/v1/system/features | `system_routes:list_features` | Public (flag okunur) |
| POST | /api/v1/system/features/toggle | `system_routes:toggle_feature` | Public (koruma yok; admin’e kilitlemek önerilir) |
| GET | /api/v1/system/overview | `system_routes:system_overview` | Public (koruma yok) |
| WEBSOCKET | /ws | `main:websocket_endpoint` | Public (session cookie ile çalışır) |

Not: `/api/*` prefix’i altında aynı yolların korumasız/kopya versiyonları da mount edilmiş; istemciler için v1 path’lerini kullanmak tercih edilir.
