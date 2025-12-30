# app/orchestrator_v42/plugins/llm_client_adapter.py
from __future__ import annotations

import asyncio
import importlib
import inspect
from typing import Dict, Any, Optional, TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags

class LlmClientAdapter:
    """
    LLM İstemci Uyarlayıcısı (LLM Client Adapter).
    
    Orchestrator ile dış LLM sağlayıcısı arasında köprü görevi görür.
    Varsayılan olarak 'DRY RUN' (Kuru Çalıştırma) modundadır.
    """
    
    def __init__(self):
        pass
        
    def _map_model_id(self, model_hint: str) -> str:
        """
        Model Seçici'den gelen soyut ID'yi (hint) gerçek LLM model ID'sine çevirir.
        3. Model Mapping (Soyut ID -> Gerçek ID / Settings)
        """
        from app.config import get_settings
        settings = get_settings()
        
        # [FAZ 16.7] Blueprint Mapping
        # Environment Variable Önceliği
        mapping = {
            # Core Roles
            "fast": settings.ORCH_MODEL_FAST or "llama-3.1-8b-instant",
            "general": settings.ORCH_MODEL_GENERAL or "llama-3.3-70b-versatile",
            "heavy": settings.ORCH_MODEL_HEAVY or "qwen-2.5-32b-instruct",
            "stylist": settings.ORCH_MODEL_STYLIST or "llama-3.1-8b-instant",
            "judge": settings.ORCH_MODEL_JUDGE or "llama-3.3-70b-versatile",
            
            # Legacy Aliases (Backward Compatibility)
            "genel_hizli_v1": settings.ORCH_MODEL_FAST or "llama-3.1-8b-instant",
            "genel_dengeli_v1": settings.ORCH_MODEL_GENERAL or "llama-3.3-70b-versatile",
            "kod_uzman_v1": settings.ORCH_MODEL_HEAVY or "qwen-2.5-32b-instruct",
            "derin_akil_v1": settings.ORCH_MODEL_HEAVY or "qwen-2.5-32b-instruct",
            "sosyal_uzman_v1": settings.ORCH_MODEL_HEAVY or "qwen-2.5-32b-instruct",
        }
        
        # Normalize
        model_hint = str(model_hint).strip().lower()
        
        # Eğer varsa tabloyu kullan, yoksa passthrough
        return mapping.get(model_hint, mapping.get("general")) # Fallback to general
        
    async def generate(
        self, 
        *, 
        message: str, 
        model_hint: str, 
        runtime: Dict[str, Any], 
        context: Dict[str, Any],
        flags: Optional[OrchestratorFeatureFlags] = None,
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        LLM çağrısını gerçekleştirir. 'messages' verilirse onu kullanır, yoksa 'message' tekil prompt olur.
        [FAZ 16.7] Cascade/Fallback logic implemented inside.
        """
        
        # 1. Flags Yükleme
        from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
        if flags is None:
            flags = OrchestratorFeatureFlags.load_from_env()
            
        # 2. Model Mapping ve Cascade Zinciri Belirleme
        # Chain Logic: Fast -> General -> Heavy
        actual_model_id = self._map_model_id(model_hint)
        cascade_chain = []
        
        if model_hint == "fast":
            cascade_chain = ["general", "heavy"]
        elif model_hint == "general":
            cascade_chain = ["heavy"]
        # heavy has no fallback
            
        # --- LIVE TRACE ---
        from app.core.live_tracer import LiveTracer
        LiveTracer.model_select(actual_model_id, "external", model_hint)
        # ------------------
        
        # 3. DRY RUN
        if flags.llm_dry_run:
             return {
                "text": f"[DRY_RUN] Yanıt ({actual_model_id}): {message[:20]}...",
                "raw": {"dry_run": True, "mapped_to": actual_model_id},
                "used_model_hint": model_hint
            }
            
        # 4. GERÇEK ÇAĞRI (WITH CASCADE)
        last_error = None
        
        # Primary Attempt
        try:
            return await self._execute_call(actual_model_id, message, messages, runtime)
        except Exception as e:
            last_error = e
            # Log primary failure (Print avoid log spam)
            print(f"WARN: Primary model {model_hint} ({actual_model_id}) failed: {e}")
            
            # Cascade Loop
            for fallback_hint in cascade_chain:
                try:
                    fallback_id = self._map_model_id(fallback_hint)
                    print(f"INFO: Cascade falling back to {fallback_hint} ({fallback_id})")
                    
                    res = await self._execute_call(fallback_id, message, messages, runtime)
                    
                    # Mark as fallback in metadata
                    if "raw" not in res: res["raw"] = {}
                    res["raw"]["cascade_used"] = True
                    res["raw"]["original_hint"] = model_hint
                    res["used_model_hint"] = fallback_hint
                    
                    return res
                except Exception as ce:
                    last_error = ce
                    print(f"WARN: Cascade {fallback_hint} failed: {ce}")
                    continue
        
        # All failed
        return {
            "text": "",
            "raw": {"error": f"All models failed. Last error: {str(last_error)}"},
            "used_model_hint": model_hint
        }

    async def _execute_call(self, model_id, message, messages, runtime):
        """Helper to execute single call via provider."""
        import importlib
        import inspect
        decider_module = importlib.import_module("app.chat.decider")
        
        candidates = [
            name for name in dir(decider_module) 
            if name.startswith("call_") 
            and name.endswith("_api_safe_async")
            and inspect.iscoroutinefunction(getattr(decider_module, name))
        ]
        
        if not candidates:
             raise ValueError("Provider function not found")
        
        # Simple Selection
        provider_func_name = sorted(candidates)[0]
        call_provider_func = getattr(decider_module, provider_func_name)
        
        # Arguments
        final_messages = messages if messages else [{"role": "user", "content": message}]
        call_kwargs = {"messages": final_messages}
        
        sig = inspect.signature(call_provider_func)
        if "model" in sig.parameters:
            call_kwargs["model"] = model_id
            
        if "timeout" in sig.parameters:
            call_kwargs["timeout"] = float(runtime.get("timeout_seconds", 30.0))
        
        # Key Injection logic...
        selected_key = runtime.get("selected_key_id")
        if selected_key and selected_key != "yok":
            for param_name in ["api_key", "key", "token"]:
                if param_name in sig.parameters:
                    call_kwargs[param_name] = selected_key
                    break
        
        # Execute
        result = await call_provider_func(**call_kwargs)
        
        # Handle dict or tuple return
        content = ""
        error = None
        
        if isinstance(result, tuple):
            content, error = result
        elif isinstance(result, dict):
             content = result.get("content")
             error = result.get("error")
        else:
             content = str(result)

        if error:
            raise RuntimeError(f"Provider Error: {error}")
            
        return {
            "text": content or "",
            "raw": {"provider": "external"},
            "used_model_hint": model_id 
        }

# =============================================================================
# STANDALONE HELPER FUNCTIONS (Blueprint v4.2 Adapter Pattern)
# =============================================================================

async def call_llm_safe(
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 1500
) -> str | None:
    """
    Basitleştirilmiş LLM Çağrısı (Adapter Pattern).
    Decider modülündeki karmaşık API çağrısını sarmalar.
    """
    try:
        from app.chat.decider import call_groq_api_safe_async
        
        content, error = await call_groq_api_safe_async(
            messages=messages,
            model=model,
            temperature=temperature,
            timeout=45.0 # Specialist için biraz daha uzun süre
        )
        
        if error:
            return None
            
        return content
        
    except Exception:
        return None
