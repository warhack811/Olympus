import json
import uuid
import traceback
from datetime import datetime
from collections.abc import AsyncGenerator
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.chat.processor import process_chat_message
from app.core.feedback_store import add_feedback
from app.core.logger import get_logger
from app.core.models import User
from app.core.usage_limiter import limiter
from app.memory.conversation import append_message as conv_append
from app.memory.conversation import create_conversation as conv_create
from app.memory.conversation import delete_conversation as conv_delete
from app.memory.conversation import list_conversations as conv_list
from app.memory.conversation import load_messages as conv_load_messages
from app.services import user_preferences
from app.config import get_settings
from app.orchestrator_v42 import gateway as orchestrator_gateway

logger = get_logger(__name__)
router = APIRouter()

# --- ŞEMALAR ---


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    force_local: bool = False
    conversation_id: str | None = None
    model: str | None = None
    stream: bool = False
    # Style preferences: {tone: str, length: str, emoji_level: str}
    style_profile: dict[str, str] | None = None
    images: list[str] | None = None  # List of filenames (e.g. "user/image.jpg")
    image_settings: dict[str, Any] | None = None  # Custom image generation settings


class ConversationSummaryOut(BaseModel):
    id: str
    title: str | None
    created_at: Any
    updated_at: Any


class MessageOut(BaseModel):
    id: int  # ← Backend message ID (frontend eşleştirmesi için)
    role: str
    text: str
    time: Any
    extra_metadata: dict[str, Any] | None = None


class FeedbackIn(BaseModel):
    conversation_id: str | None = None
    message: str = Field(..., min_length=1, max_length=5000)
    feedback: str = Field(..., pattern="^(like|dislike)$")


# --- YARDIMCI FONKSİYONLAR ---


def _build_message_metadata(engine: str, action: str, forced: bool, persona: bool, model: str) -> dict[str, Any]:
    return {
        "engine": engine,
        "action": action,
        "mode": "forced_local" if forced else "normal",
        "persona_applied": persona,
        "model": model,
    }


# --- ENDPOINTS ---


@router.post("/chat", response_model=MessageOut, response_model_exclude_none=True)
async def chat(payload: ChatRequest, user: User = Depends(get_current_active_user)):
    """Kullanici ile sohbet endpoint'i. Stream destekler."""
    if user.id is None:
        raise HTTPException(status_code=400, detail="Geçersiz kullanıcı")
    user_id = user.id
    limiter.check_limits_pre_flight(user_id)
    username = user.username
    trace_id = f"req-{uuid.uuid4().hex[:6]}"
    logger.info(f"[CHAT_ENTRY] {username} | trace={trace_id} | m='{payload.message[:50]}'")

    conv_id = payload.conversation_id
    if not conv_id:
        summary = conv_create(username=username, first_message=payload.message)
        conv_id = summary.id

    conv_append(username=username, conv_id=conv_id, role="user", text=payload.message)

    persona_applied = user_preferences.get_effective_preferences(user_id) != {}

    # ORCHESTRATOR GATEWAY (v4.2)
    settings = get_settings()
    if settings.ORCH_ENABLED:
        try:
            logger.info(f"[ORCHESTRATOR] Calling gateway for user {username}")
            # Gateway denemesi - Başarısız olursa veya passthrough verirse legacy'e düşer
            orch_res = await orchestrator_gateway.try_handle(
                username=username,
                message=payload.message,
                user=user,
                payload=payload,
                conversation_id=conv_id,
                trace_id=trace_id # Trace ID'yi eşleştir
            )
            
            if orch_res and orch_res.response_text:
                print(f"DEBUG: [CHAT] Archestrator Success! Text Len: {len(orch_res.response_text)}")
                # [FIX] Persistence: Save orchestrator response
                # [FIX] Persistence: Save orchestrator response
                msg_obj = conv_append(
                    username=username,
                    conv_id=conv_id,
                    role="assistant",
                    text=orch_res.response_text,
                    extra_metadata={
                        "engine": "orchestrator",
                        "trace_id": trace_id,
                        "model": orch_res.model_name
                    }
                )
                msg_id = msg_obj.id if msg_obj else -1

                # Orchestrator cevabını hazırla
                metadata = _build_message_metadata(
                    engine="orchestrator",
                    action="generate",
                    forced=False,
                    persona=False,
                    model=orch_res.model_name
                )
                
                # Streaming ise stream'e bağla, değilse direkt dön
                # Streaming ise stream'e bağla, değilse direkt dön
                if payload.stream:
                    async def orch_stream():
                        # Frontend Stream Protokolü: [CONV_ID:...] ile başlamalı
                        yield f"[CONV_ID:{conv_id}]"
                        # Frontend plain-text beklediği için raw text dönüyoruz
                        yield orch_res.response_text
                    
                    return StreamingResponse(orch_stream(), media_type="text/plain", headers={"X-Conversation-ID": conv_id})
                else:
                    msg_out = MessageOut(
                        id=msg_id,
                        role="assistant",
                        text=orch_res.response_text,
                        time=datetime.now(),
                        extra_metadata=metadata
                    )
                    print("DEBUG: [CHAT] Returning MessageOut JSON")
                    return msg_out
                    
        except orchestrator_gateway.LegacyFallbackRequired as e:
            print(f"DEBUG: [ORCHESTRATOR] Fallback because: {e}")
            logger.info(f"[ORCHESTRATOR] [TRACE={trace_id}] Fallback triggered: {e}")
        except Exception as e:
            print(f"DEBUG: [ORCHESTRATOR] CRITICAL: {e}")
            traceback.print_exc() # Stack trace'i terminale bas
            logger.error(f"[ORCHESTRATOR] [TRACE={trace_id}] Gateway critical failure: {e}", exc_info=True)
            logger.info(f"[CHAT] [TRACE={trace_id}] Proceeding with Legacy Fallback due to error.")

    # PERSONA BAZLI MODEL ROUTING
    # Eğer kullanıcı model belirtmediyse, aktif persona'ya bakarak otomatik belirle
    requested_model = payload.model
    if not requested_model:
        from app.core.dynamic_config import config_service

        active_persona_name = user.active_persona or "standard"
        active_persona = config_service.get_persona(active_persona_name)

        if active_persona and active_persona.get("requires_uncensored", False):
            # Persona sansürsüz model gerektiriyorsa otomatik "local" set et
            requested_model = "local"
            logger.info(f"[CHAT] Persona '{active_persona_name}' requires_uncensored=True, model set to 'local'")

    # --- STREAMING AKTİFSE ---
    if payload.stream:

        async def stream_and_save():
            # İlk chunk olarak conversation_id gönder (header'a güvenemeyen durumlar için)
            yield f"[CONV_ID:{conv_id}]"
            
            full_reply = ""
            # process_chat_message stream modunda bir generator döndürür
            result_generator = await process_chat_message(
                username=username,
                message=payload.message,
                user=user,
                force_local=payload.force_local,
                conversation_id=conv_id,
                requested_model=requested_model,
                stream=True,
                style_profile=payload.style_profile,
                images=payload.images,
                image_settings=payload.image_settings,
            )

            # Streaming olmayan (ör. image/internet/local) yanıtlar için güvenli fallback
            if isinstance(result_generator, tuple) and len(result_generator) >= 2:
                # Tuple döndü (non-stream mode): (reply, semantic)
                full_reply = str(result_generator[0] or "")
                if full_reply:
                    # IMAGE_PENDING ve IMAGE_QUEUED marker'larını strip et - bunlar frontend için değil
                    if "[IMAGE_PENDING]" in full_reply:
                        full_reply = full_reply.replace("[IMAGE_PENDING]", "").strip()
                    if "[IMAGE_QUEUED" in full_reply:
                        # IMAGE_QUEUED geldiğinde hiçbir şey gönderme - pending mesaj zaten DB'de
                        full_reply = ""
                    if full_reply:
                        yield full_reply
            elif hasattr(result_generator, "__aiter__"):
                # AsyncGenerator döndü (stream mode)
                async for chunk in result_generator:
                    if "[IMAGE_PENDING]" in chunk:
                        chunk = chunk.replace("[IMAGE_PENDING]", "").strip()
                    if "[IMAGE_QUEUED" in chunk:
                        # IMAGE_QUEUED geldiğinde skip - pending mesaj zaten DB'de
                        continue
                    if chunk:
                        full_reply += chunk
                        yield chunk
            else:
                # Beklenmeyen durum - string olarak işle
                full_reply = str(result_generator or "")
                if full_reply:
                    yield full_reply

            # Stream bittikten sonra tam cevabı ve metadatayı kaydet
            logger.info(f"[CHAT_STREAM_END] User: {username}, Full reply length: {len(full_reply)}")

            # Metadata ve kullanım limiti
            engine = "groq"
            action = "GROQ_REPLY"
            if full_reply.startswith("[LOCAL]") or payload.force_local:
                engine = "local"
                action = "LOCAL_CHAT"
            meta = _build_message_metadata(
                engine=engine,
                action=action,
                forced=payload.force_local,
                persona=persona_applied,
                model=payload.model or "default",
            )
            # Prefix'siz kaydet
            save_text = full_reply.strip()

            # Eğer cevap boşsa (örn. sadece IMAGE_QUEUED döndüyse) kaydetme
            if save_text:
                conv_append(username=username, conv_id=conv_id, role="bot", text=save_text, extra_metadata=meta)
                limiter.consume_usage(user_id, engine=engine)

        return StreamingResponse(stream_and_save(), media_type="text/plain", headers={"X-Conversation-ID": conv_id})

    # --- STREAMING KAPALIYSA (NORMAL YANIT) ---
    else:
        try:
            result = await process_chat_message(
                username=username,
                message=payload.message,
                user=user,
                force_local=payload.force_local,
                conversation_id=conv_id,
                requested_model=requested_model,
                stream=False,
                style_profile=payload.style_profile,
                images=payload.images,
                image_settings=payload.image_settings,
            )
            # Runtime type guard ile explicit casting
            if hasattr(result, "__aiter__"):
                # AsyncGenerator döndü (stream=False olmasına rağmen)
                chunks = []
                async_gen = cast(AsyncGenerator[str, None], result)
                async for chunk in async_gen:
                    chunks.append(chunk)
                reply = "".join(chunks)
                semantic = None
            else:
                # Tuple döndü
                tuple_result = cast(tuple[str, Any], result)
                reply, semantic = tuple_result
        except Exception as e:
            logger.error(f"[CHAT] process_chat_message hata: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Bir hata oluştu (Legacy).")

        # IMAGE_QUEUED kontrolü (Non-stream)
        if "[IMAGE_QUEUED" in reply:
            reply = ""

        # Eğer cevap boşsa (örn. sadece IMAGE_QUEUED döndüyse) işlem yapma
        if not reply.strip():
            # Boş yanıt durumunda anlamlı bir hata dön
            raise HTTPException(status_code=500, detail="İşlemci boş yanıt döndürdü.")

        # Engine tipi belirleme (artık prefix yerine request parametrelerine göre)
        if payload.force_local or requested_model == "local":
            engine = "local"
            action = "LOCAL_CHAT"
        elif "[NET]" in reply or "[INTERNET]" in reply:
            engine = "internet"
            action = "INTERNET"
        elif "[IMAGE" in reply or "[FLUX]" in reply:
            engine = "image"
            action = "IMAGE"
        else:
            engine = "groq"
            action = "GROQ_REPLY"

        try:
            limiter.consume_usage(user_id, engine=engine)
        except Exception as e:
            logger.debug(f"[CHAT] Usage limit consume failed: {e}")

        meta = _build_message_metadata(
            engine=engine,
            action=action,
            forced=payload.force_local,
            persona=persona_applied,
            model=payload.model or "default",
        )
        conv_append(username=username, conv_id=conv_id, role="bot", text=reply, extra_metadata=meta)

        follow_body = reply
        follow_obj = None
        if "FOLLOWUPS_JSON:" in reply:
            try:
                body, json_part = reply.split("FOLLOWUPS_JSON:", 1)
                follow_body = body.strip()
                follow_obj = json.loads(json_part.strip())
            except Exception as e:
                logger.debug(f"[CHAT] Followups JSON parse failed: {e}")

        return MessageOut(
            id=-1,
            role="assistant",
            text=follow_body,
            time=datetime.now(),
            extra_metadata=meta
        )


@router.get("/conversations", response_model=list[ConversationSummaryOut])
async def get_conversations(user: User = Depends(get_current_active_user)):
    convs = conv_list(username=user.username)
    return [
        ConversationSummaryOut(id=c.id, title=c.title, created_at=c.created_at, updated_at=c.updated_at) for c in convs
    ]


@router.get("/conversations/{conversation_id}", response_model=list[MessageOut])
async def get_conversation_endpoint(conversation_id: str, user: User = Depends(get_current_active_user)):
    """
    Frontend Compatibility: Bu endpoint aslında sohbet detayını değil,
    sohbetin MESAJLARINI dönmeli. (Bkz: ui-new/src/api/client.ts:166)
    """
    msgs = conv_load_messages(username=user.username, conv_id=conversation_id)
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            text=m.content if hasattr(m, "content") else m.text,
            time=m.created_at if hasattr(m, "created_at") else m.time,
            extra_metadata=m.extra_metadata if hasattr(m, "extra_metadata") else None,
        )
        for m in msgs
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def get_conversation_messages(conversation_id: str, user: User = Depends(get_current_active_user)):
    msgs = conv_load_messages(username=user.username, conv_id=conversation_id)
    return [
        MessageOut(
            id=m.id,  # ← Backend message ID
            role=m.role,
            text=m.content if hasattr(m, "content") else m.text,
            time=m.created_at if hasattr(m, "created_at") else m.time,
            extra_metadata=m.extra_metadata if hasattr(m, "extra_metadata") else None,
        )
        for m in msgs
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str, user: User = Depends(get_current_active_user)):
    conv_delete(username=user.username, conv_id=conversation_id)
    return {"ok": True}


@router.post("/feedback")
async def submit_feedback(body: FeedbackIn, user: User = Depends(get_current_active_user)):
    add_feedback(
        username=user.username,
        conversation_id=body.conversation_id or "",
        message=body.message,
        feedback=body.feedback,
    )
    return {"ok": True}
