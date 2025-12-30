import json
import asyncio
import logging
from pydantic import BaseModel, Field, ValidationError
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags

# Logger
logger = logging.getLogger("orchestrator.memory.writeback")


# [FAZ 16.4] LLM Fact Extractor Modelleri
class FactItem(BaseModel):
    key: str = Field(..., description="Fact anahtarı (örn: name_preference, job, hobby)")
    value: str = Field(..., min_length=2, max_length=40, description="Fact değeri")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(default="")

    def clean_value(self):
        """Basit temizlik: tırnaklar, boşluklar ve yaygın kuyruk kelimeler (Zincirleme)."""
        v = self.value.strip()
        # Temizlenecek karakterler
        for ch in ["'", '"', ".", "!", ","]:
            v = v.replace(ch, "")
        
        # Kuyruk temizliği (Suffix removal - Chained)
        suffixes = ["olsun", "lütfen", "bunu", "şunu", "yap", "et"]
        words = v.split()
        
        while words and words[-1].lower() in suffixes:
            words.pop()
            
        v = " ".join(words).strip()
        self.value = v[:40] # Hard clamp 40 chars

class FactExtractionResult(BaseModel):
    should_promote: bool
    facts_to_add: list[FactItem] = Field(default_factory=list)
    facts_to_remove: list[str] = Field(default_factory=list)

# [FAZ 16.4] Dar Tetikleyiciler (Trigger Words)
# Minimum set: "kod adım", "diye çağır", "hatırla"
TRIGGER_KEYWORDS = ["kod adım", "diye çağır", "hatırla"]

async def write_memory_turn(
    user_id: str | None,
    user_message: str,
    assistant_message: str,
    flags: OrchestratorFeatureFlags,
    trace_id: str,
    conversation_id: str | None = None
) -> dict:
    """
    Kullanıcı ve asistan mesajlarını eski hafıza sistemine yazar (Chat History).
    [FAZ 16.4.2] Fact Extraction arka planda (fire-and-forget) çalışır.
    """
    # 1. Ön Kontroller
    if not user_id:
        return {"ran": False, "dry_run": False, "ok": False, "notes": "Kullanıcı kimliği yok, yazma atlandı."}
        
    if not flags.memory_write_enabled:
        return {"ran": False, "dry_run": False, "ok": False, "notes": "Hafıza yazma kapalı."}

    # Kullanılacak conversation ID
    if not conversation_id:
         return {"ran": False, "dry_run": False, "ok": False, "notes": "Conversation ID yok, yazma atlandı."}

    # 2. Dry-Run Kontrolü
    if flags.memory_write_dry_run:
        logger.info(f"[{trace_id}] Hafıza Yazma (Kuru Çalıştırma): kullanıcı={len(user_message)} kü, asistan={len(assistant_message)} kü")
        return {"ran": True, "dry_run": True, "ok": True, "notes": "Dry-run: yazma simüle edildi."}

    # 3. Gerçek Yazma İşlemi (Async Wrapper)
    try:
        from app.memory.conversation import append_message
        
        def _sync_write_task():
            append_message(username=user_id, conv_id=conversation_id, role="user", text=user_message)
            append_message(username=user_id, conv_id=conversation_id, role="bot", text=assistant_message)
            return True

        timeout_val = max(0.05, flags.memory_write_timeout_s) 
        
        await asyncio.wait_for(
            asyncio.to_thread(_sync_write_task),
            timeout=timeout_val
        )
        
        # [FAZ 16.4.2] Kalıcı Hafıza Promote (Fire-and-Forget)
        # Ana akışı bloklamamak için create_task ile arka plana atıyoruz.
        # Wrapper içinde timeout (0.4s) yönetiliyor.
        async def _promote_safe_wrapper():
            try:
                await asyncio.wait_for(
                    _promote_critical_info(user_id, user_message, conversation_id, trace_id),
                    timeout=0.4
                )
            except asyncio.TimeoutError:
                logger.warning(f"[{trace_id}] Memory Promote Timeout (0.4s)")
            except Exception as e:
                logger.error(f"[{trace_id}] Memory Promote Error: {e}")

        asyncio.create_task(_promote_safe_wrapper())
        
        return {"ran": True, "dry_run": False, "ok": True, "notes": "Başarıyla yazıldı, promote arka planda tetiklendi."}
        
    except asyncio.TimeoutError:
        logger.warning(f"[{trace_id}] Hafıza Yazma Zaman Aşımı ({timeout_val}s)")
        return {"ran": True, "dry_run": False, "ok": False, "notes": "Hafıza yazma zaman aşımı."}
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{trace_id}] Hafıza Yazma Hatası: {error_msg}")
        return {"ran": True, "dry_run": False, "ok": False, "notes": f"Hafıza yazma hatası: {error_msg}"}


async def _promote_critical_info(username: str, message: str, conversation_id: str, trace_id: str) -> None:
    """
    [FAZ 16.4] Kritik bilgileri LLM ile analiz edip profile yazar.
    """
    from app.memory.conversation_archive import ConversationArchive
    from app.services.user_profile_service import UserProfileService
    from app.core.database import get_session
    from app.core.models import User
    from sqlmodel import select
    
    # 1. Archive Trigger (Layer 4)
    if ConversationArchive.has_critical_info(message):
        await ConversationArchive.trigger_immediate_summary(
            conversation_id, 
            reason="critical_info_detected"
        )
        logger.info(f"[{trace_id}] Archive Immediate Summary Triggered")

    # 2. Trigger Check
    msg_lower = message.lower()
    if not any(kw in msg_lower for kw in TRIGGER_KEYWORDS):
        return

    # 3. LLM Fact Extraction
    facts = await _extract_facts_via_llm(message)
    if not facts or not facts.should_promote:
        return

    # 4. User Resolution & Write
    user_db_id = None
    try:
        with get_session() as session:
            user = session.exec(select(User).where(User.username == username)).first()
            if user:
                user_db_id = user.id
    except Exception as e:
        logger.warning(f"[{trace_id}] User Resolution Failed: {e}")
        return

    if user_db_id:
        for item in facts.facts_to_add:
            item.clean_value()
            if len(item.value) < 2:
                continue

            await UserProfileService.add_fact(
                user_id=user_db_id,
                category="personal",
                key=item.key,
                value=item.value,
                source="extractor_llm", 
                confidence=item.confidence,
                metadata={"reason": item.reason, "promoted_by": "fact_extractor_v1"},
                auto_resolve_conflict=True
            )
            # Generic Log
            logger.info(f"[{trace_id}] Profile Fact Promoted: {item.key}={item.value}")


async def _extract_facts_via_llm(message: str) -> FactExtractionResult | None:
    """
    Mesajdan fact çıkarımı yapar. Fail-soft çalışır.
    """
    from app.orchestrator_v42.plugins.llm_client_adapter import call_llm_safe
    from app.config import get_settings
    
    system_prompt = """SEN BİR FACT EXTRACTOR (GERÇEK ÇIKARICI) AJANISIN.
Kullanıcının mesajından kendisiyle ilgili kalıcı hatırlanması gereken tercihleri (isim, meslek, kod adı vb.) çıkar.

KURALLAR:
1. SADECE JSON DÖNDÜR. Yorum yok.
2. Eğer kaydedilecek net bir bilgi yoksa "should_promote": false yap.
3. Negatif emirleri ("beni X diye çağırma") kaydetme.
4. Value en fazla 3-4 kelime olsun.

ÇIKTI ŞEMASI (JSON):
{
  "should_promote": true,
  "facts_to_add": [
    {"key": "name_preference", "value": "Kırmızı", "confidence": 0.9, "reason": "Kod adı isteği"}
  ]
}
"""
    try:
        settings = get_settings()
        # [HARDENING] Generic model name usage
        model_id = getattr(settings, "ORCH_FACT_EXTRACTOR_MODEL", None) or "fact_extractor_default"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        content = await call_llm_safe(
            model=model_id,
            messages=messages,
            temperature=0.0,
            max_tokens=250
        )
        
        if not content:
            return None
            
        cleaned = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        return FactExtractionResult(**data)
        
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Fact Extractor Parse Error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Fact Extractor Error: {e}")
        return None
