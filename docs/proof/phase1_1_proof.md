# Phase 1.1 Proof Package (RAW)
- generated_at: `2025-12-27T13:33:26.245797Z`
- repo_root: `D:/ai/mami_ai_v4`
- scope_files: `app/chat/smart_router.py, tests/test_smart_router_orchestrator.py`

## Repo Snapshot (RAW)

### COMMAND
`git rev-parse --abbrev-ref HEAD`

**exit_code:** `0`

**stdout:**
```text
main
```

**stderr:**
```text
<empty>
```

### COMMAND
`git log -3 --oneline`

**exit_code:** `0`

**stdout:**
```text
d1f72c3 refactor: gereksiz Ã¶lÃ¼ kod fonksiyonlarÄ± temizlendi
2c4dab4 backup: Ã¶lÃ¼ kod temizliÄŸi Ã¶ncesi yedek
84454e8 YapÄ±lan guncelleme ile ilgili kisa aciklama
```

**stderr:**
```text
<empty>
```

### COMMAND
`git status --porcelain`

**exit_code:** `0`

**stdout:**
```text
 M alembic/script.py.mako
 M app/ai/groq/__init__.py
 M app/ai/ollama/gemma_handler.py
 M app/ai/prompts/compiler.py
 M app/ai/prompts/identity.py
 M app/ai/prompts/image_guard.py
 M app/api/routes/__init__.py
 D app/api/user_routes.py
 M app/auth/dependencies.py
 M app/auth/invite_manager.py
 M app/auth/remember.py
 M app/auth/session.py
 M app/auth/user_manager.py
 M app/chat/__init__.py
 M app/chat/answerer.py
 M app/chat/decider.py
 D app/chat/orchestrator/__init__.py
 D app/chat/orchestrator/bridge.py
 D app/chat/orchestrator/composer.py
 M app/chat/search.py
 M app/chat/smart_router.py
 M app/core/__init__.py
 M app/core/config_models.py
 M app/core/config_seed.py
 M app/core/database.py
 M app/core/dynamic_config.py
 M app/core/exceptions.py
 M app/core/feature_flags.py
 M app/core/logger.py
 M app/core/usage_limiter.py
 M app/image/flux_stub.py
 M app/image/image_manager.py
 M app/image/job_queue.py
 M app/main.py
 M app/memory/__init__.py
 M app/memory/conversation.py
 M app/memory/rag.py
 M app/memory/store.py
 M app/plugins/__init__.py
 M app/plugins/async_image/tasks.py
 D app/plugins/response_enhancement/__init__.py
 D app/plugins/response_enhancement/config.py
 D app/plugins/response_enhancement/orchestrator.py
 D app/plugins/response_enhancement/plugin.py
 D app/plugins/response_enhancement/prompt_enhancer.py
 D app/plugins/response_enhancement/smart_shaper.py
 D app/plugins/response_enhancement/visual_beautifier.py
 M app/services/query_enhancer.py
 M app/services/response_processor.py
 M app/services/user_context.py
 D app/websocket_sender.py
 D dead_code_analysis_report.md
 D debug_image_flow.py
 M docs/ARCHITECTURE.md
 D docs/BACKEND_ANALYSIS_REPORT.md
 D docs/DETAYLI_HATA_ANALIZI_VE_COZUMLER.md
 D docs/DETAYLI_HATA_ANALIZI_VE_COZUMLER_DEVAM.md
 D docs/FRONTEND_ANALYSIS_REPORT.md
 M docs/IMAGE_QUEUE_SYSTEM.md
 D docs/IMPROVEMENTS_FOR_10_10.md
 M docs/QUALITY_MASTER_PLAN.md
 M docs/README.md
 M docs/ROADMAP.md
 D docs/UYGULAMA_RAPORU_FINAL.md
 D docs/auto/_db_generator.py
 D docs/auto/_generator.py
 D docs/auto/_routes_generator.py
 M docs/auto/api_routes.md
 M docs/auto/architecture_overview.md
 M docs/auto/critical_files.md
 M docs/auto/db_schema.md
 M docs/auto/repo_inventory.json
 M docs/auto/repo_tree.txt
 D plans/theme_compatibility_report.md
 D plans/ui_migration_analysis.md
 D requirements_upgrade.txt
 M scripts/__init__.py
 D scripts/cleanup_memories.py
 D scripts/deploy_critical_fixes.py
 D scripts/deploy_critical_fixes.sh
 D scripts/mobile_server.bat
 D scripts/redis.bat
 D scripts/setup_alembic_migration.py
 D test_persona.py
 M tests/conftest.py
 M tests/test_image_router.py
 D tests/test_orchestrator_composer.py
 D tests/test_orchestrator_processor_bridge.py
A  tests/test_smart_router_orchestrator.py
 M ui-new/index.html
 M ui-new/package-lock.json
 M ui-new/package.json
 M ui-new/public/manifest.json
 M ui-new/public/sw.js
 M ui-new/src/App.tsx
 M ui-new/src/api/client.ts
 M ui-new/src/components/chat/ChatArea.tsx
 M ui-new/src/components/chat/ChatInput.tsx
 M ui-new/src/components/chat/ImageProgressCard.tsx
 M ui-new/src/components/chat/MessageBubble.tsx
 M ui-new/src/components/chat/MessageList.tsx
 M ui-new/src/components/chat/MessageReactions.tsx
 M ui-new/src/components/chat/QuickSettings.tsx
 M ui-new/src/components/chat/WelcomeScreen.tsx
 M ui-new/src/components/common/ImageGallery.tsx
 M ui-new/src/components/common/SettingsSheet.tsx
 M ui-new/src/components/layout/ChatLayout.tsx
 M ui-new/src/components/layout/Header.tsx
 M ui-new/src/components/layout/Sidebar.tsx
 M ui-new/src/components/ui/index.ts
 M ui-new/src/hooks/index.ts
 M ui-new/src/index.css
 M ui-new/src/lib/markdownRenderer.ts
 M ui-new/src/main.tsx
 M ui-new/src/stores/settingsStore.ts
 M ui-new/src/styles/code.css
 M ui-new/src/styles/globals.css
 M ui-new/src/types/index.ts
 M ui-new/vite.config.ts
 D ui/admin.html
 D ui/chat.html
 D ui/css/base.css
 D ui/css/code-blocks.css
 D ui/css/header.css
 D ui/css/layout.css
 D ui/css/main.css
 D ui/css/messages.css
 D ui/css/modals.css
 D ui/css/modern.css
 D ui/css/sidebar.css
 D ui/css/themes.css
 D ui/css/utilities.css
 D ui/css/variables.css
 D ui/js/chat-core.js
 D ui/js/images.js
 D ui/js/main.js
 D ui/js/markdown.js
 D ui/js/memory.js
 D ui/js/persona.js
 D ui/js/ui.js
 D ui/js/utils.js
 D ui/login.html
 D ui/manifest.json
 D ui/register.html
 D ui/sw.js
 D unused_functions_analysis.md
 D vulture_report_high.txt
 D walkthrough.md
?? .agent/
?? app/api/admin_api_keys.py
?? app/api/routes/chat.py
?? app/api/routes/documents.py
?? app/api/routes/images.py
?? app/api/routes/memories.py
?? app/api/routes/preferences.py
?? app/chat/services/
?? app/chat/stream_manager.py
?? app/core/env_manager.py
?? app/core/websockets.py
?? app/memory/_deprecated/
?? app/memory/query_expander.py
?? app/memory/rag_service.py
?? app/memory/rag_v2.py
?? app/memory/rag_v2_conversation.py
?? app/memory/rag_v2_docs.py
?? app/memory/rag_v2_lexical.py
?? app/memory/rag_v2_telemetry.py
?? app/plugins/beautiful_response/
?? app/plugins/rag_v2/
?? app/services/api_monitor.py
?? docs/1upgrade_plan.md
?? docs/PROJECT_IMPROVEMENTS_AND_ISSUES.md
?? docs/benchmark_results.md
?? docs/benchmark_results_hakem_codex.md
?? docs/benchmark_results_new.md
?? docs/groq_models_analysis.md
?? docs/model_scorecard.md
?? docs/multi_model_strategy.md
?? docs/orchestrator_router_blueprint.md
?? docs/project_roadmap.md
?? docs/proof/
?? docs/turkish_benchmark_final_40_results.md
?? docs/turkish_benchmark_grand_final.md
?? docs/turkish_benchmark_short_30.md
?? docs/turkish_benchmark_short_30_results.md
?? docs/turkish_benchmark_v2_questions.md
?? docs/turkish_benchmark_v2_results.md
?? docs/turkish_model_implementation_strategy.md
?? docs/turkish_model_scorecard_final_40.md
?? docs/turkish_model_scorecard_short_30.md
?? docs/turkish_model_scorecard_v2.md
?? docs/upgrade_plan.md
?? scripts/groq_models.json
?? scripts/mobile_test.bat
?? scripts/proof_phase1_1.py
?? scripts/start_backend_only.bat
?? tests/eval_harness/cases.json
?? tests/eval_harness/run_eval.py
?? tests/manual_verification_phase_7_4.py
?? tests/rag_v2/
?? tests/test_eval_harness_smoke.py
?? tests/test_persona_duzeltilmis.py
?? tests/test_rag_v2_continue.py
?? tests/test_rag_v2_conversation_pinning.py
?? tests/test_rag_v2_doc_selection.py
?? tests/test_rag_v2_faithfulness.py
?? tests/test_rag_v2_ingestion.py
?? tests/test_rag_v2_phase_7_4.py
?? tests/test_rag_v2_plugin.py
?? tests/test_rag_v2_plugin_retrieval.py
?? tests/test_rag_v2_summary.py
?? tests/verify_updates.py
?? ui-new/src/components/admin/
?? ui-new/src/components/chat/ImageLightbox.tsx
?? ui-new/src/components/chat/MermaidViewer.tsx
?? ui-new/src/components/chat/ModernChatInput.tsx
?? ui-new/src/components/chat/UniversalMediaViewer.tsx
?? ui-new/src/components/common/DocumentsTab.tsx
?? ui-new/src/components/common/ImageLightbox.tsx
?? ui-new/src/components/layout/RootLayout.tsx
?? ui-new/src/components/layout/UserProfile.tsx
?? ui-new/src/components/ui/Badge.tsx
?? ui-new/src/components/ui/Card.tsx
?? ui-new/src/components/ui/Dialog.tsx
?? ui-new/src/components/ui/Progress.tsx
?? ui-new/src/components/ui/Sheet.tsx
?? ui-new/src/components/ui/Switch.tsx
?? ui-new/src/components/ui/Table.tsx
?? ui-new/src/hooks/use-toast.ts
?? ui-new/src/hooks/useMermaidDiagrams.ts
?? ui-new/src/lib/svgToPng.ts
?? ui-new/src/pages/
```

**stderr:**
```text
<empty>
```

### COMMAND
`git diff --name-only`

**exit_code:** `0`

**stdout:**
```text
alembic/script.py.mako
app/ai/groq/__init__.py
app/ai/ollama/gemma_handler.py
app/ai/prompts/compiler.py
app/ai/prompts/identity.py
app/ai/prompts/image_guard.py
app/api/routes/__init__.py
app/api/user_routes.py
app/auth/dependencies.py
app/auth/invite_manager.py
app/auth/remember.py
app/auth/session.py
app/auth/user_manager.py
app/chat/__init__.py
app/chat/answerer.py
app/chat/decider.py
app/chat/orchestrator/__init__.py
app/chat/orchestrator/bridge.py
app/chat/orchestrator/composer.py
app/chat/search.py
app/chat/smart_router.py
app/core/__init__.py
app/core/config_models.py
app/core/config_seed.py
app/core/database.py
app/core/dynamic_config.py
app/core/exceptions.py
app/core/feature_flags.py
app/core/logger.py
app/core/usage_limiter.py
app/image/flux_stub.py
app/image/image_manager.py
app/image/job_queue.py
app/main.py
app/memory/__init__.py
app/memory/conversation.py
app/memory/rag.py
app/memory/store.py
app/plugins/__init__.py
app/plugins/async_image/tasks.py
app/plugins/response_enhancement/__init__.py
app/plugins/response_enhancement/config.py
app/plugins/response_enhancement/orchestrator.py
app/plugins/response_enhancement/plugin.py
app/plugins/response_enhancement/prompt_enhancer.py
app/plugins/response_enhancement/smart_shaper.py
app/plugins/response_enhancement/visual_beautifier.py
app/services/query_enhancer.py
app/services/response_processor.py
app/services/user_context.py
app/websocket_sender.py
dead_code_analysis_report.md
debug_image_flow.py
docs/ARCHITECTURE.md
docs/BACKEND_ANALYSIS_REPORT.md
docs/DETAYLI_HATA_ANALIZI_VE_COZUMLER.md
docs/DETAYLI_HATA_ANALIZI_VE_COZUMLER_DEVAM.md
docs/FRONTEND_ANALYSIS_REPORT.md
docs/IMAGE_QUEUE_SYSTEM.md
docs/IMPROVEMENTS_FOR_10_10.md
docs/QUALITY_MASTER_PLAN.md
docs/README.md
docs/ROADMAP.md
docs/UYGULAMA_RAPORU_FINAL.md
docs/auto/_db_generator.py
docs/auto/_generator.py
docs/auto/_routes_generator.py
docs/auto/api_routes.md
docs/auto/architecture_overview.md
docs/auto/critical_files.md
docs/auto/db_schema.md
docs/auto/repo_inventory.json
docs/auto/repo_tree.txt
plans/theme_compatibility_report.md
plans/ui_migration_analysis.md
requirements_upgrade.txt
scripts/__init__.py
scripts/cleanup_memories.py
scripts/deploy_critical_fixes.py
scripts/deploy_critical_fixes.sh
scripts/mobile_server.bat
scripts/redis.bat
scripts/setup_alembic_migration.py
test_persona.py
tests/conftest.py
tests/test_image_router.py
tests/test_orchestrator_composer.py
tests/test_orchestrator_processor_bridge.py
ui-new/index.html
ui-new/package-lock.json
ui-new/package.json
ui-new/public/manifest.json
ui-new/public/sw.js
ui-new/src/App.tsx
ui-new/src/api/client.ts
ui-new/src/components/chat/ChatArea.tsx
ui-new/src/components/chat/ChatInput.tsx
ui-new/src/components/chat/ImageProgressCard.tsx
ui-new/src/components/chat/MessageBubble.tsx
ui-new/src/components/chat/MessageList.tsx
ui-new/src/components/chat/MessageReactions.tsx
ui-new/src/components/chat/QuickSettings.tsx
ui-new/src/components/chat/WelcomeScreen.tsx
ui-new/src/components/common/ImageGallery.tsx
ui-new/src/components/common/SettingsSheet.tsx
ui-new/src/components/layout/ChatLayout.tsx
ui-new/src/components/layout/Header.tsx
ui-new/src/components/layout/Sidebar.tsx
ui-new/src/components/ui/index.ts
ui-new/src/hooks/index.ts
ui-new/src/index.css
ui-new/src/lib/markdownRenderer.ts
ui-new/src/main.tsx
ui-new/src/stores/settingsStore.ts
ui-new/src/styles/code.css
ui-new/src/styles/globals.css
ui-new/src/types/index.ts
ui-new/vite.config.ts
ui/admin.html
ui/chat.html
ui/css/base.css
ui/css/code-blocks.css
ui/css/header.css
ui/css/layout.css
ui/css/main.css
ui/css/messages.css
ui/css/modals.css
ui/css/modern.css
ui/css/sidebar.css
ui/css/themes.css
ui/css/utilities.css
ui/css/variables.css
ui/js/chat-core.js
ui/js/images.js
ui/js/main.js
ui/js/markdown.js
ui/js/memory.js
ui/js/persona.js
ui/js/ui.js
ui/js/utils.js
ui/login.html
ui/manifest.json
ui/register.html
ui/sw.js
unused_functions_analysis.md
vulture_report_high.txt
walkthrough.md
```

**stderr:**
```text
warning: in the working copy of 'app/ai/ollama/gemma_handler.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/ai/prompts/compiler.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/chat/answerer.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/chat/decider.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/chat/smart_router.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/core/config_seed.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/core/database.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/image/flux_stub.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/image/image_manager.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/image/job_queue.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/main.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/memory/conversation.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/plugins/__init__.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/plugins/async_image/tasks.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/services/query_enhancer.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/services/response_processor.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/services/user_context.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/ARCHITECTURE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/IMAGE_QUEUE_SYSTEM.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/QUALITY_MASTER_PLAN.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/README.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/ROADMAP.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/auto/api_routes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/auto/architecture_overview.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/auto/critical_files.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/auto/db_schema.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/index.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/package-lock.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/package.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/public/manifest.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/public/sw.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/App.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/api/client.ts', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/chat/ChatArea.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/chat/ImageProgressCard.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/chat/MessageList.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/chat/MessageReactions.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/chat/QuickSettings.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/common/ImageGallery.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/common/SettingsSheet.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/layout/ChatLayout.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/layout/Header.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/components/ui/index.ts', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/hooks/index.ts', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/index.css', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/lib/markdownRenderer.ts', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/main.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/stores/settingsStore.ts', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/styles/code.css', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/styles/globals.css', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/src/types/index.ts', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'ui-new/vite.config.ts', LF will be replaced by CRLF the next time Git touches it
```

## Scope Files (Existence & Tracking)

### FILE
`app/chat/smart_router.py`
- exists: `True`
- size_bytes: `35047`

### FILE
`tests/test_smart_router_orchestrator.py`
- exists: `True`
- size_bytes: `6810`

### COMMAND
`git ls-files app/chat/smart_router.py tests/test_smart_router_orchestrator.py`

**exit_code:** `0`

**stdout:**
```text
app/chat/smart_router.py
tests/test_smart_router_orchestrator.py
```

**stderr:**
```text
<empty>
```

## Diffs (Scope Files)

### COMMAND
`git diff -- app/chat/smart_router.py`

**exit_code:** `0`

**stdout:**
```text
diff --git a/app/chat/smart_router.py b/app/chat/smart_router.py
index 6457615..7868cac 100644
--- a/app/chat/smart_router.py
+++ b/app/chat/smart_router.py
@@ -147,6 +147,87 @@ NSFW_IMAGE_PATTERNS = [
 ]
 
 
+# =============================================================================
+# ORCHESTRATOR v5.8 - MODEL CATALOG & INTENT PATTERNS
+# =============================================================================
+
+# Model Catalog (Consensus v5.2 - Blueprint compliant)
+# strengths: 0-3 score, quality/latency/cost: literal tier
+MODEL_CATALOG: Dict[str, Dict[str, Any]] = {
+    "llama-3.1-8b-instant": {
+        "strengths": {"coding": 1, "analysis": 1, "creative": 2, "social_chat": 1, "tool_planning": 1, "tr_natural": 2},
+        "quality_tier": "med",
+        "latency_tier": "fast",
+        "cost_tier": "low",
+        "can_judge": False,
+        "can_rewrite": False,
+    },
+    "qwen3-32b": {
+        "strengths": {"coding": 2, "analysis": 3, "creative": 2, "social_chat": 2, "tool_planning": 3, "tr_natural": 3},
+        "quality_tier": "high",
+        "latency_tier": "med",
+        "cost_tier": "med",
+        "can_judge": True,
+        "can_rewrite": True,
+    },
+    "kimi-k2": {
+        # social_chat = TR slang / sokak aÄŸzÄ± / doÄŸal samimiyet (VIP Param)
+        "strengths": {"coding": 2, "analysis": 2, "creative": 3, "social_chat": 3, "tool_planning": 2, "tr_natural": 3},
+        "quality_tier": "high",
+        "latency_tier": "med",
+        "cost_tier": "med",
+        "can_judge": False,
+        "can_rewrite": True,
+    },
+    "gpt-oss-120b": {
+        "strengths": {"coding": 3, "analysis": 3, "creative": 2, "social_chat": 1, "tool_planning": 3, "tr_natural": 2},
+        "quality_tier": "high",
+        "latency_tier": "slow",
+        "cost_tier": "high",
+        "can_judge": True,
+        "can_rewrite": False,
+    },
+    "llama-70b": {
+        "strengths": {"coding": 2, "analysis": 3, "creative": 2, "social_chat": 2, "tool_planning": 2, "tr_natural": 2},
+        "quality_tier": "high",
+        "latency_tier": "slow",
+        "cost_tier": "high",
+        "can_judge": True,
+        "can_rewrite": False,
+    },
+}
+
+# Intent types for orchestrator v5.8
+INTENT_TYPES = ["code", "analysis", "creative", "social_chat", "research", "tool_use", "rag_query", "general"]
+
+# Domain/intent regex patterns for fallback classification
+INTENT_PATTERNS: Dict[str, re.Pattern] = {
+    "code": re.compile(r"(?i)\b(kod|code|python|javascript|script|fonksiyon|function|debug|hata|error|program|algoritma|yaz|yazdir|dÃ¶ngÃ¼|dongu|class|sinif|sÄ±nÄ±f)\b"),
+    "social_chat": re.compile(r"(?i)^(merhaba|selam|naber|nasilsin|nasÄ±lsÄ±n|hey|gunaydin|gÃ¼naydÄ±n|iyi\s*geceler|iyi\s*aksamlar|iyi\s*akshamlar|hos\s*geldin|hoÅŸ\s*geldin)\b"),
+    "research": re.compile(r"(?i)\b(arastir|araÅŸtÄ±r|incele|analiz\s*et|karsilastir|karÅŸÄ±laÅŸtÄ±r|ne\s*fark|arasindaki|arasÄ±ndaki|ozet|Ã¶zet)\b"),
+    "rag_query": re.compile(r"(?i)\b(TCK|madde|kanun|yonetmelik|yÃ¶netmelik|belge|dosya|pdf|document|mevzuat|hukuk)\b"),
+    "creative": re.compile(r"(?i)\b(hikaye|siir|ÅŸiir|roman|senaryo|yaratici|yaratÄ±cÄ±|hayal|fantezi)\b"),
+}
+
+# Intent â†’ Primary model mapping (capability-based selection)
+INTENT_TO_MODEL: Dict[str, str] = {
+    "code": "gpt-oss-120b",
+    "analysis": "qwen3-32b",
+    "creative": "kimi-k2",
+    "social_chat": "kimi-k2",
+    "research": "qwen3-32b",
+    "tool_use": "qwen3-32b",
+    "rag_query": "qwen3-32b",
+    "general": "qwen3-32b",
+}
+
+# Complexity detection patterns
+COMPLEXITY_PATTERNS = {
+    "high": re.compile(r"(?i)\b(karmasik|karmaÅŸÄ±k|complex|detayli|detaylÄ±|kapsamli|kapsamlÄ±|optimizasyon|refactor|mimari|architecture)\b"),
+    "simple": re.compile(r"(?i)^(evet|hayir|hayÄ±r|tamam|ok|tesekkur|teÅŸekkÃ¼r|peki|anladim|anladÄ±m)$"),
+}
+
+
 # =============================================================================
 # SMART ROUTER
 # =============================================================================
@@ -221,7 +302,35 @@ class SmartRouter:
         Returns:
             ToolIntent: AlgÄ±lanan intent
         """
+        # 1. Image Intent Check
         if self._matches_any(message, self._image_patterns):
+            # EXCEPTION: Technical Diagrams/Charts should NOT go to Image Generator
+            # unless explicitly asking for "resim" (picture) specifically?
+            
+            # Diagram keywords (suffix friendly for Turkish)
+            diagram_keywords = [
+                r"\b(diyagram|ÅŸema|sema|tablo|grafik|chart|diagram|flowchart|algoritma|mermaid)\w*",
+                r"\b(akÄ±ÅŸ)\s*(ÅŸema|sema)\w*",
+                r"\b(kavram)\s*(harita)\w*"
+            ]
+            
+            # Check for diagram intent
+            is_technical_diagram = False
+            for p in diagram_keywords:
+                if re.search(p, message, re.IGNORECASE):
+                    is_technical_diagram = True
+                    break
+            
+            # BUT: If user explicitly asks for "photorealistic", "gerÃ§ekÃ§i", "fotoÄŸraf", "resim" 
+            # AND "diagram", maybe they want a picture OF a diagram? 
+            # Generally, if "mermaid" or "akÄ±ÅŸ ÅŸemasÄ±" is present, we prefer Text.
+            
+            if is_technical_diagram:
+                # One last check: Does user emphasize IMAGE generation heavily?
+                # e.g. "bana akÄ±ÅŸ ÅŸemasÄ±nÄ±n fotoÄŸrafÄ±nÄ± oluÅŸtur" -> Image?
+                # For now, safe bet is: mixed intent -> Text (because LLM can explain it can't gen header image)
+                return ToolIntent.NONE
+                
             return ToolIntent.IMAGE
         
         if self._matches_any(message, self._internet_patterns):
@@ -271,6 +380,197 @@ class SmartRouter:
         
         return False
     
+    # -------------------------------------------------------------------------
+    # ORCHESTRATOR v5.8 - INTENT DETECTION & METADATA
+    # -------------------------------------------------------------------------
+    
+    def _detect_intent_regex(self, message: str) -> Dict[str, Any]:
+        """
+        Regex-based intent classification (Phase 1 fallback).
+        
+        Args:
+            message: KullanÄ±cÄ± mesajÄ±
+        
+        Returns:
+            Dict with intent, confidence, and signals
+        """
+        detected_intent = "general"
+        confidence = 0.3  # Default low confidence for general
+        signals: Dict[str, bool] = {
+            "rag_needed": False,
+            "tool_needed": False,
+            "tr_slang_hint": False,
+            "exact_match_hint": False,
+        }
+        
+        # Check patterns in priority order
+        for intent_type, pattern in INTENT_PATTERNS.items():
+            if pattern.search(message):
+                detected_intent = intent_type
+                confidence = 0.6  # Regex match = medium confidence
+                break
+        
+        # RAG signals
+        if detected_intent == "rag_query":
+            signals["rag_needed"] = True
+            signals["exact_match_hint"] = True  # TCK, madde etc. need exact match
+        
+        # Tool signals (internet search)
+        if self._matches_any(message, self._internet_patterns):
+            signals["tool_needed"] = True
+        
+        # TR slang hint for social chat
+        if detected_intent == "social_chat":
+            signals["tr_slang_hint"] = True
+        
+        return {
+            "intent": detected_intent,
+            "confidence": confidence,
+            "signals": signals,
+        }
+    
+    def _detect_complexity(self, message: str) -> str:
+        """
+        Detect message complexity level.
+        
+        Returns:
+            "simple", "medium", or "high"
+        """
+        if COMPLEXITY_PATTERNS["simple"].match(message):
+            return "simple"
+        if COMPLEXITY_PATTERNS["high"].search(message):
+            return "high"
+        
+        # Length-based heuristic
+        word_count = len(message.split())
+        if word_count > 50:
+            return "high"
+        elif word_count < 10:
+            return "simple"
+        
+        return "medium"
+    
+    def _select_model_for_intent(self, intent: str) -> str:
+        """
+        Select best model for given intent using MODEL_CATALOG.
+        
+        Args:
+            intent: Detected intent type
+        
+        Returns:
+            Model name from catalog
+        """
+        return INTENT_TO_MODEL.get(intent, "qwen3-32b")
+    
+    def _build_orchestrator_metadata(
+        self,
+        message: str,
+        intent_result: Dict[str, Any],
+    ) -> Dict[str, Any]:
+        """
+        Build orchestrator v5.8 metadata structure.
+        
+        Args:
+            message: Original user message
+            intent_result: Result from _detect_intent_regex
+        
+        Returns:
+            Orchestrator metadata dict for RoutingDecision.metadata
+        """
+        intent = intent_result["intent"]
+        confidence = intent_result["confidence"]
+        signals = intent_result["signals"]
+        
+        selected_model = self._select_model_for_intent(intent)
+        complexity = self._detect_complexity(message)
+        
+        # Determine required tools
+        requires_tools: List[str] = []
+        if signals.get("tool_needed"):
+            requires_tools.append("web_search")
+        if signals.get("rag_needed"):
+            requires_tools.append("rag_search")
+        
+        # Required capabilities based on intent
+        capability_map = {
+            "code": ["coding", "high_precision"],
+            "analysis": ["analysis", "reasoning"],
+            "creative": ["creative", "tr_natural"],
+            "social_chat": ["social_chat", "tr_natural"],
+            "research": ["analysis", "tool_planning"],
+            "rag_query": ["analysis", "tool_planning"],
+            "general": ["analysis"],
+        }
+        required_capabilities = capability_map.get(intent, ["analysis"])
+        
+        # Build tasks array (single task for Phase 1)
+        tasks = [{
+            "id": "t1",
+            "type": intent,
+            "depends_on": [],
+            "required_capabilities": required_capabilities,
+            "requires_tools": requires_tools,  # List[str] per user patch
+            "priority": 1,
+        }]
+        
+        return {
+            "version": "v5.8",
+            "tasks": tasks,
+            "selected_model": selected_model,
+            "complexity": complexity,
+            "domain": intent,
+            "confidence": confidence,
+            "signals": signals,
+        }
+    
+    async def _detect_intent_llm(
+        self,
+        message: str,
+        user_ctx: Optional[Dict[str, Any]] = None,
+    ) -> tuple:
+        """
+        LLM-based intent classification (Phase 2 - not called from route()).
+        
+        Args:
+            message: User message
+            user_ctx: Optional user context
+        
+        Returns:
+            Tuple of (intent_result, error_code)
+            - On success: (intent_dict, None)
+            - On timeout: (None, "INTENT_LLM_TIMEOUT")
+            - On error: (None, "INTENT_LLM_ERROR")
+        
+        Note:
+            This method is async and will be integrated in Phase 2
+            when the async pipeline is implemented. For Phase 1,
+            route() uses _detect_intent_regex() only.
+        """
+        import asyncio
+        
+        # Get timeout from config (default 800ms)
+        config_service = self._get_config_service()
+        timeout_ms = 800
+        if config_service:
+            timeout_ms = config_service.get("orchestrator.intent.timeout_ms", 800)
+        
+        timeout_sec = timeout_ms / 1000.0
+        
+        try:
+            # TODO Phase 2: Implement actual LLM call with Scout model
+            # For now, this is a stub that simulates the interface
+            await asyncio.sleep(0.01)  # Simulate minimal async work
+            
+            # Stub: Fall back to regex for now
+            intent_result = self._detect_intent_regex(message)
+            return (intent_result, None)
+            
+        except asyncio.TimeoutError:
+            return (None, "INTENT_LLM_TIMEOUT")
+        except Exception as e:
+            logger.warning(f"[ROUTER] Intent LLM error: {e}")
+            return (None, "INTENT_LLM_ERROR")
+    
     # -------------------------------------------------------------------------
     # ANA ROUTING LOGIC
     # -------------------------------------------------------------------------
@@ -340,6 +640,12 @@ class SmartRouter:
             tool_intent = ToolIntent.NONE
             reason_codes.append("web_search_disabled_by_user_pref")
         
+        # =====================================================================
+        # ORCHESTRATOR v5.8: Intent Detection & Metadata (Phase 1 - regex only)
+        # =====================================================================
+        intent_result = self._detect_intent_regex(message)
+        orchestrator_metadata = self._build_orchestrator_metadata(message, intent_result)
+        
         # =====================================================================
         # PRIORITY 1: TOOL INTENT (IMAGE / INTERNET)
         # =====================================================================
@@ -357,6 +663,7 @@ class SmartRouter:
                     persona_name=active_persona,
                     persona_requires_uncensored=persona_uncensored,
                     final_model=final_model,
+                    metadata={"orchestrator": orchestrator_metadata},
                 )
             
             # NSFW kontrolÃ¼
@@ -372,6 +679,7 @@ class SmartRouter:
                     persona_name=active_persona,
                     persona_requires_uncensored=persona_uncensored,
                     final_model=final_model,
+                    metadata={"orchestrator": orchestrator_metadata},
                 )
             
             reason_codes.append("tool_intent_image")
@@ -383,7 +691,7 @@ class SmartRouter:
                 persona_name=active_persona,
                 persona_requires_uncensored=persona_uncensored,
                 final_model=final_model,
-                metadata={"is_nsfw": is_nsfw},
+                metadata={"is_nsfw": is_nsfw, "orchestrator": orchestrator_metadata},
             )
         
         if tool_intent == ToolIntent.INTERNET:
@@ -398,6 +706,7 @@ class SmartRouter:
                     persona_name=active_persona,
                     persona_requires_uncensored=persona_uncensored,
                     final_model=final_model,
+                    metadata={"orchestrator": orchestrator_metadata},
                 )
             
             reason_codes.append("tool_intent_internet")
@@ -409,6 +718,7 @@ class SmartRouter:
                 persona_name=active_persona,
                 persona_requires_uncensored=persona_uncensored,
                 final_model=final_model,
+                metadata={"orchestrator": orchestrator_metadata},
             )
         
         # =====================================================================
@@ -446,6 +756,7 @@ class SmartRouter:
                     persona_name=active_persona,
                     persona_requires_uncensored=bool(persona_requires),
                     final_model="local",  # Explicit local seÃ§ildi
+                    metadata={"orchestrator": orchestrator_metadata},
                 )
             else:
                 # Ä°zin yok, Groq'a yÃ¶nlendir
@@ -459,6 +770,7 @@ class SmartRouter:
                     persona_name=active_persona,
                     persona_requires_uncensored=bool(persona_requires),
                     final_model="groq",
+                    metadata={"orchestrator": orchestrator_metadata},
                 )
         
         # =====================================================================
@@ -475,6 +787,7 @@ class SmartRouter:
                 persona_name=active_persona,
                 persona_requires_uncensored=persona_uncensored,
                 final_model="local",
+                metadata={"orchestrator": orchestrator_metadata},
             )
         
         # Semantic analiz bazlÄ± routing (opsiyonel, yavaÅŸ olabilir)
@@ -494,6 +807,7 @@ class SmartRouter:
                     persona_name=active_persona,
                     persona_requires_uncensored=persona_uncensored,
                     final_model="local",
+                    metadata={"orchestrator": orchestrator_metadata},
                 )
         
         # =====================================================================
@@ -509,6 +823,7 @@ class SmartRouter:
             persona_name=active_persona,
             persona_requires_uncensored=persona_uncensored,
             final_model=final_model,
+            metadata={"orchestrator": orchestrator_metadata},
         )
     
     # -------------------------------------------------------------------------
```

**stderr:**
```text
warning: in the working copy of 'app/chat/smart_router.py', LF will be replaced by CRLF the next time Git touches it
```

### COMMAND
`git diff -- tests/test_smart_router_orchestrator.py`

**exit_code:** `0`

**stdout:**
```text
<empty>
```

**stderr:**
```text
<empty>
```

## Git History (Scope Files)

### COMMAND
`git log -n 10 --oneline -- app/chat/smart_router.py`

**exit_code:** `0`

**stdout:**
```text
555f6b7 chore: format
0e67c7a chore: initial commit
```

**stderr:**
```text
<empty>
```

### COMMAND
`git log -n 10 --oneline -- tests/test_smart_router_orchestrator.py`

**exit_code:** `0`

**stdout:**
```text
<empty>
```

**stderr:**
```text
<empty>
```

## Pytest Evidence (RAW)

### COMMAND
`C:\Users\admin\AppData\Local\Programs\Python\Python310\python.exe -m pytest -q --collect-only tests/test_smart_router_orchestrator.py`

**exit_code:** `0`

**stdout:**
```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.0.1, pluggy-1.6.0
rootdir: D:\ai\mami_ai_v4
configfile: pyproject.toml
plugins: anyio-3.7.1, hydra-core-1.3.2, asyncio-1.3.0
asyncio: mode=auto, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 10 items

<Dir mami_ai_v4>
  <Package tests>
    <Module test_smart_router_orchestrator.py>
      <Class TestModelCatalog>
        <Function test_catalog_has_required_models>
        <Function test_catalog_schema_compliance>
      <Class TestIntentDetectionRegex>
        <Function test_social_chat_intent>
        <Function test_code_intent>
        <Function test_rag_query_signals>
        <Function test_internet_tool_consistency>
        <Function test_metadata_structure>
      <Class TestIntentLLMExtension>
        <Coroutine test_llm_intent_timeout>
        <Coroutine test_llm_intent_error>
        <Coroutine test_llm_intent_success_stub>

========================= 10 tests collected in 0.02s =========================
```

**stderr:**
```text
<empty>
```

### COMMAND
`C:\Users\admin\AppData\Local\Programs\Python\Python310\python.exe -m pytest -q tests/test_smart_router_orchestrator.py -vv --tb=long`

**exit_code:** `0`

**stdout:**
```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.0.1, pluggy-1.6.0 -- C:\Users\admin\AppData\Local\Programs\Python\Python310\python.exe
cachedir: .pytest_cache
rootdir: D:\ai\mami_ai_v4
configfile: pyproject.toml
plugins: anyio-3.7.1, hydra-core-1.3.2, asyncio-1.3.0
asyncio: mode=auto, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 10 items

tests/test_smart_router_orchestrator.py::TestModelCatalog::test_catalog_has_required_models PASSED [ 10%]
tests/test_smart_router_orchestrator.py::TestModelCatalog::test_catalog_schema_compliance PASSED [ 20%]
tests/test_smart_router_orchestrator.py::TestIntentDetectionRegex::test_social_chat_intent PASSED [ 30%]
tests/test_smart_router_orchestrator.py::TestIntentDetectionRegex::test_code_intent PASSED [ 40%]
tests/test_smart_router_orchestrator.py::TestIntentDetectionRegex::test_rag_query_signals PASSED [ 50%]
tests/test_smart_router_orchestrator.py::TestIntentDetectionRegex::test_internet_tool_consistency PASSED [ 60%]
tests/test_smart_router_orchestrator.py::TestIntentDetectionRegex::test_metadata_structure PASSED [ 70%]
tests/test_smart_router_orchestrator.py::TestIntentLLMExtension::test_llm_intent_timeout PASSED [ 80%]
tests/test_smart_router_orchestrator.py::TestIntentLLMExtension::test_llm_intent_error PASSED [ 90%]
tests/test_smart_router_orchestrator.py::TestIntentLLMExtension::test_llm_intent_success_stub PASSED [100%]

============================= 10 passed in 0.93s ==============================
```

**stderr:**
```text
<empty>
```

### COMMAND
`C:\Users\admin\AppData\Local\Programs\Python\Python310\python.exe -m pytest -q --collect-only`

**exit_code:** `2`

**stdout:**
```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.0.1, pluggy-1.6.0
rootdir: D:\ai\mami_ai_v4
configfile: pyproject.toml
testpaths: tests
plugins: anyio-3.7.1, hydra-core-1.3.2, asyncio-1.3.0
asyncio: mode=auto, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 171 items / 1 error

<Dir mami_ai_v4>
  <Package tests>
    <Dir rag_v2>
      <Module test_phase_7_4.py>
        <Function test_bypass_python_question>
        <Function test_non_bypass_but_sanity_fails>
        <Function test_rag_pass>
        <Function test_telemetry_single_write>
    <Module test_critical_fixes.py>
      <Class TestChromaDBWhereFilter>
        <Coroutine test_rag_search_uses_where_filter>
        <Coroutine test_memory_service_uses_where_filter>
      <Class TestForgeCircuitBreaker>
        <Function test_circuit_starts_closed>
        <Function test_circuit_opens_after_threshold>
        <Function test_circuit_half_open_after_timeout>
        <Function test_circuit_closes_after_success_in_half_open>
        <Coroutine test_flux_stub_uses_circuit_breaker>
      <Class TestAlembicMigration>
        <Function test_alembic_config_exists>
        <Function test_alembic_versions_directory_exists>
        <Function test_database_init_tries_alembic_first>
        <Function test_create_db_has_deprecation_warning>
      <Class TestCriticalFixesIntegration>
        <Coroutine test_all_fixes_work_together>
    <Module test_eval_harness_smoke.py>
      <Function test_evaluate_case_smoke>
    <Module test_fixes_8_9.py>
      <Class TestSafeCallbackExecutor>
        <Coroutine test_successful_callback>
        <Coroutine test_callback_retry_on_failure>
        <Coroutine test_callback_all_retries_fail>
        <Coroutine test_async_callback_support>
        <Coroutine test_context_tracking>
        <Function test_clear_failed_history>
      <Class TestDatabaseConnectionPool>
        <Function test_engine_initialization>
        <Function test_get_session_context_manager>
        <Function test_concurrent_sessions>
        <Function test_session_rollback_on_error>
        <Function test_busy_timeout_configured>
      <Class TestIntegration>
        <Coroutine test_callback_with_db_operation>
        <Coroutine test_multiple_callbacks_concurrent>
    <Module test_image_router.py>
      <Class TestCheckpointSelection>
        <Function test_safe_content_uses_standard_checkpoint>
        <Function test_nsfw_content_with_permission_uses_uncensored>
        <Function test_nsfw_content_without_permission_blocked>
        <Function test_admin_can_generate_nsfw>
      <Class TestNSFWDetection>
        <Function test_nsfw_keywords_detected>
        <Function test_safe_keywords_not_detected>
      <Class TestPermissionEnforcement>
        <Function test_no_image_permission_blocked>
        <Function test_banned_user_blocked>
      <Class TestParameters>
        <Function test_default_parameters>
        <Function test_custom_parameters>
        <Function test_negative_prompt>
      <Class TestSpecToDict>
        <Function test_to_dict_conversion>
    <Module test_next_three_fixes.py>
      <Class TestMemoryDuplicateDetection>
        <Function test_text_similarity_exact_match>
        <Function test_text_similarity_different>
        <Function test_normalization>
        <Function test_entity_extraction>
        <Function test_duplicate_false_positive_prevention>
        <Function test_duplicate_true_positive>
        <Function test_importance_based_thresholds>
      <Class TestStreamingMemoryManager>
        <Coroutine test_can_process_memory_first_time>
        <Coroutine test_duplicate_prevention>
        <Coroutine test_mark_completed>
        <Coroutine test_concurrent_lock>
      <Class TestContextTruncationManager>
        <Function test_token_estimation>
        <Function test_message_importance_position>
        <Function test_message_importance_role>
        <Function test_message_importance_content_type>
        <Function test_truncate_messages_by_importance>
        <Function test_truncate_text_smart_paragraph_boundary>
        <Function test_truncate_text_smart_sentence_completion>
      <Class TestIntegration>
        <Coroutine test_memory_service_with_hybrid_detection>
        <Function test_processor_context_truncation>
    <Module test_persona_system.py>
      <Class TestImageGuard>
        <Function test_forbidden_tokens_removed>
        <Function test_user_requested_tokens_kept>
        <Function test_validate_prompt_minimal>
        <Function test_get_forbidden_tokens_in_prompt>
        <Function test_empty_prompt>
        <Function test_multiple_forbidden_tokens>
      <Class TestSmartRouterPersona>
        <Function test_romantic_persona_with_image_request>
        <Function test_romantic_persona_with_web_request>
        <Function test_romantic_persona_with_chat>
        <Function test_tool_priority_over_persona>
        <Function test_admin_always_has_access>
      <Class TestPersonaSelection>
        <Function test_requires_uncensored_with_local_permission>
        <Function test_requires_uncensored_without_local_permission>
      <Class TestPromptCompiler>
        <Function test_build_system_prompt_basic>
        <Function test_build_system_prompt_with_toggles>
      <Class TestPermissionHelpers>
        <Function test_admin_bypasses_all_restrictions>
        <Function test_regular_user_respects_permissions>
      <Class TestImagePromptPrefix>
        <Coroutine test_single_bang_raw_prompt>
        <Function test_single_bang_with_forbidden_token>
        <Function test_double_bang_bypasses_guard>
        <Function test_double_bang_preserves_all_tokens>
        <Function test_prefix_extraction>
        <Function test_empty_after_prefix>
    <Module test_professional_output.py>
      <Class TestStepByStep>
        <Function test_technical_steps_are_numbered>
        <Function test_short_answer_not_forced_to_list>
      <Class TestComparison>
        <Function test_pros_cons_structure>
      <Class TestCodeExample>
        <Function test_code_block_preserved>
        <Function test_incomplete_code_block_closed>
      <Class TestTableJson>
        <Function test_table_preserved>
        <Function test_json_in_code_block>
      <Class TestCasualChat>
        <Function test_casual_response_not_over_formatted>
      <Class TestWebToolOutput>
        <Function test_sources_section_added>
        <Function test_no_sources_no_section>
      <Class TestPersonaTone>
        <Function test_friendly_tone_preserved>
      <Class TestStrictCensorship>
        <Function test_format_not_broken_by_censorship>
      <Class TestPresets>
        <Function test_professional_preset_exists>
        <Function test_professional_is_default>
        <Function test_professional_no_emoji>
    <Module test_rag_v2_continue.py>
      <UnitTestCase TestRagV2Continue>
        <TestCaseFunction test_compiler_continue_contract>
        <TestCaseFunction test_compiler_priority>
        <TestCaseFunction test_processor_triggers_clean>
        <TestCaseFunction test_search_continue_logic>
    <Module test_rag_v2_conversation_pinning.py>
      <Function test_conversation_pinning_flow>
      <Function test_conversation_pinning_search_integration>
    <Module test_rag_v2_doc_selection.py>
      <Function test_doc_selection_from_seeds_logic>
      <Function test_search_documents_v2_uses_two_stage_query>
      <Function test_auto_pinning_margin_logic>
      <Function test_auto_pinning_success>
    <Module test_rag_v2_faithfulness.py>
      <Function test_rag_v2_inactive_no_strict_rules>
      <Function test_rag_v2_active_strict_rules_present>
      <Function test_rag_v2_strict_rules_override_content>
    <Module test_rag_v2_ingestion.py>
      <Function test_add_txt_document_v2>
      <Function test_sanitize_filename>
      <Function test_add_pdf_document_v2_mock>
    <Module test_rag_v2_phase_7_4.py>
      <Function test_bypass_keywords>
      <Function test_gating_fail_no_evidence>
      <Function test_gating_pass_with_evidence>
      <Function test_lexical_sanity_check>
    <Module test_rag_v2_plugin.py>
      <Function test_plugin_registration>
      <Function test_plugin_default_disabled>
      <Function test_plugin_enabled_by_flag>
      <Function test_process_response_noop>
      <Coroutine test_processor_hook_integration>
    <Module test_rag_v2_plugin_retrieval.py>
      <Function test_process_response_with_candidates>
      <Function test_process_response_no_context_query>
      <Function test_process_response_empty_results>
      <Function test_process_response_error_handling>
      <Function test_hybrid_search_sorting_integration>
      <Function test_lexical_search_fail_open_integration>
      <Function test_process_response_no_evidence_due_to_threshold>
      <Function test_process_response_no_evidence_due_to_margin>
      <Function test_process_response_with_valid_evidence>
      <Function test_hybrid_merge_key_uses_page_number>
      <Function test_gating_uses_hybrid_score_for_hybrid_candidates>
      <Function test_gating_fails_hybrid_threshold>
      <Function test_telemetry_logging_integration>
    <Module test_response_enhancement.py>
      <Function test_basic_markdown>
      <Function test_code_enhancement>
      <Function test_emoji_callouts>
      <Function test_list_formatting>
      <Function test_turkish_rules>
      <Function test_format_levels>
      <Function test_comprehensive>
    <Module test_smart_router_orchestrator.py>
      <Class TestModelCatalog>
        <Function test_catalog_has_required_models>
        <Function test_catalog_schema_compliance>
      <Class TestIntentDetectionRegex>
        <Function test_social_chat_intent>
        <Function test_code_intent>
        <Function test_rag_query_signals>
        <Function test_internet_tool_consistency>
        <Function test_metadata_structure>
      <Class TestIntentLLMExtension>
        <Coroutine test_llm_intent_timeout>
        <Coroutine test_llm_intent_error>
        <Coroutine test_llm_intent_success_stub>
    <Module test_streaming_buffer.py>
      <Class TestStreamingBuffer>
        <Function test_buffer_initialization>
        <Function test_append_chunks>
        <Function test_circular_buffer_overflow>
        <Function test_finalize>
        <Function test_finalize_multiple_calls>
        <Function test_clear>
        <Function test_empty_chunks_ignored>
        <Function test_stats>
      <Class TestStreamingBufferMemoryManagement>
        <Function test_memory_usage_stays_bounded>
        <Function test_large_chunks_handled>
      <Class TestStreamingBufferAsyncUsage>
        <Coroutine test_async_streaming_simulation>
        <Coroutine test_concurrent_buffers>
      <Class TestStreamingBufferEdgeCases>
        <Function test_max_chunks_zero>
        <Function test_max_chunks_one>
        <Function test_unicode_chunks>
        <Function test_very_long_single_chunk>

=================================== ERRORS ====================================
_____________ ERROR collecting tests/test_persona_duzeltilmis.py ______________
ImportError while importing test module 'D:\ai\mami_ai_v4\tests\test_persona_duzeltilmis.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Users\admin\AppData\Local\Programs\Python\Python310\lib\importlib\__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests\test_persona_duzeltilmis.py:22: in <module>
    from app.core.database import engine, get_session as app_get_session
E   ImportError: cannot import name 'engine' from 'app.core.database' (D:\ai\mami_ai_v4\app\core\database.py)
------------------------------- Captured stderr -------------------------------
2025-12-27 16:33:30 - app.main - INFO - API route'ları yüklendi (v1 + backward compat)
=========================== short test summary info ===========================
ERROR tests/test_persona_duzeltilmis.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
==================== 171 tests collected, 1 error in 1.32s ====================
```

**stderr:**
```text
<empty>
```

## Line-Context Proof: metadata["orchestrator"] injection

```text
[hit 1] line 465
   0461:             Model name from catalog
   0462:         """
   0463:         return INTENT_TO_MODEL.get(intent, "qwen3-32b")
   0464:     
>> 0465:     def _build_orchestrator_metadata(
   0466:         self,
   0467:         message: str,
   0468:         intent_result: Dict[str, Any],
   0469:     ) -> Dict[str, Any]:

[hit 2] line 647
   0643:         # =====================================================================
   0644:         # ORCHESTRATOR v5.8: Intent Detection & Metadata (Phase 1 - regex only)
   0645:         # =====================================================================
   0646:         intent_result = self._detect_intent_regex(message)
>> 0647:         orchestrator_metadata = self._build_orchestrator_metadata(message, intent_result)
   0648:         
   0649:         # =====================================================================
   0650:         # PRIORITY 1: TOOL INTENT (IMAGE / INTERNET)
   0651:         # =====================================================================

[hit 3] line 666
   0662:                     block_reason="Görsel üretim izniniz bulunmuyor.",
   0663:                     persona_name=active_persona,
   0664:                     persona_requires_uncensored=persona_uncensored,
   0665:                     final_model=final_model,
>> 0666:                     metadata={"orchestrator": orchestrator_metadata},
   0667:                 )
   0668:             
   0669:             # NSFW kontrolü
   0670:             is_nsfw = self._detect_nsfw_image(message)

[hit 4] line 682
   0678:                     block_reason="Bu tür görsel içerik üretim izniniz bulunmuyor.",
   0679:                     persona_name=active_persona,
   0680:                     persona_requires_uncensored=persona_uncensored,
   0681:                     final_model=final_model,
>> 0682:                     metadata={"orchestrator": orchestrator_metadata},
   0683:                 )
   0684:             
   0685:             reason_codes.append("tool_intent_image")
   0686:             return RoutingDecision(

[hit 5] line 694
   0690:                 censorship_level=censorship_level,
   0691:                 persona_name=active_persona,
   0692:                 persona_requires_uncensored=persona_uncensored,
   0693:                 final_model=final_model,
>> 0694:                 metadata={"is_nsfw": is_nsfw, "orchestrator": orchestrator_metadata},
   0695:             )
   0696:         
   0697:         if tool_intent == ToolIntent.INTERNET:
   0698:             if not can_use_internet:

[hit 6] line 709
   0705:                     block_reason="İnternet araması izniniz bulunmuyor.",
   0706:                     persona_name=active_persona,
   0707:                     persona_requires_uncensored=persona_uncensored,
   0708:                     final_model=final_model,
>> 0709:                     metadata={"orchestrator": orchestrator_metadata},
   0710:                 )
   0711:             
   0712:             reason_codes.append("tool_intent_internet")
   0713:             return RoutingDecision(

[hit 7] line 721
   0717:                 censorship_level=censorship_level,
   0718:                 persona_name=active_persona,
   0719:                 persona_requires_uncensored=persona_uncensored,
   0720:                 final_model=final_model,
>> 0721:                 metadata={"orchestrator": orchestrator_metadata},
   0722:             )
   0723:         
   0724:         # =====================================================================
   0725:         # PRIORITY 2: EXPLICIT LOCAL

[hit 8] line 759
   0755:                     censorship_level=censorship_level,
   0756:                     persona_name=active_persona,
   0757:                     persona_requires_uncensored=bool(persona_requires),
   0758:                     final_model="local",  # Explicit local seçildi
>> 0759:                     metadata={"orchestrator": orchestrator_metadata},
   0760:                 )
   0761:             else:
   0762:                 # İzin yok, Groq'a yönlendir
   0763:                 reason_codes.append("local_permission_denied")

[hit 9] line 773
   0769:                     censorship_level=censorship_level,
   0770:                     persona_name=active_persona,
   0771:                     persona_requires_uncensored=bool(persona_requires),
   0772:                     final_model="groq",
>> 0773:                     metadata={"orchestrator": orchestrator_metadata},
   0774:                 )
   0775:         
   0776:         # =====================================================================
   0777:         # PRIORITY 3: CONTENT HEURISTIC (sadece net sinyallerde - AUTO routing)

[hit 10] line 790
   0786:                 censorship_level=censorship_level,
   0787:                 persona_name=active_persona,
   0788:                 persona_requires_uncensored=persona_uncensored,
   0789:                 final_model="local",
>> 0790:                 metadata={"orchestrator": orchestrator_metadata},
   0791:             )
   0792:         
   0793:         # Semantic analiz bazlı routing (opsiyonel, yavaş olabilir)
   0794:         if semantic and can_auto_local:

[hit 11] line 810
   0806:                     censorship_level=censorship_level,
   0807:                     persona_name=active_persona,
   0808:                     persona_requires_uncensored=persona_uncensored,
   0809:                     final_model="local",
>> 0810:                     metadata={"orchestrator": orchestrator_metadata},
   0811:                 )
   0812:         
   0813:         # =====================================================================
   0814:         # PRIORITY 4: DEFAULT → GROQ

[hit 12] line 826
   0822:             censorship_level=censorship_level,
   0823:             persona_name=active_persona,
   0824:             persona_requires_uncensored=persona_uncensored,
   0825:             final_model=final_model,
>> 0826:             metadata={"orchestrator": orchestrator_metadata},
   0827:         )
   0828:     
   0829:     # -------------------------------------------------------------------------
   0830:     # LOGGING
```

## Return-path Signals (Best-effort scan)

- return RoutingDecision occurrences: `10`

- metadata orchestrator injection occurrences: `9`

**return lines:**
```text
656
672
686
699
713
751
765
782
802
818
```

**orchestrator metadata lines:**
```text
666
682
709
721
759
773
790
810
826
```
