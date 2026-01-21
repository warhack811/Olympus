import asyncio
import json
import uuid
import logging
import traceback
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.chat.processor import process_chat_message
from app.core.logger import get_logger
from app.core.models import User
from app.core.usage_limiter import limiter
from app.memory.conversation import (
    append_message as conv_append,
    create_conversation as conv_create,
    delete_conversation as conv_delete,
    list_conversations as conv_list,
    load_messages as conv_load_messages,
    update_message as conv_update
)
from app.services.brain.engine import brain_engine
from app.schemas.chat import ChatRequest, StyleProfile

logger = get_logger(__name__)
router = APIRouter()

# --- HELPER ---
def _build_meta(engine: str, action: str, forced: bool, persona: Any, model: str) -> dict[str, Any]:
    return {
        "engine": engine,
        "action": action,
        "mode": "forced_local" if forced else "normal",
        "persona_applied": str(persona),
        "model": model,
        "timestamp": datetime.now().isoformat()
    }

# --- SCHEMAS ---
class ConversationSummaryOut(BaseModel):
    id: str
    title: str | None
    created_at: Any
    updated_at: Any

class MessageOut(BaseModel):
    id: int
    role: str
    text: str
    time: Any
    extra_metadata: dict[str, Any] | None = None

class FeedbackIn(BaseModel):
    conversation_id: str | None = None
    message: str = Field(..., min_length=1)
    feedback: str = Field(..., pattern="^(like|dislike)$")

@router.post("/chat")
async def chat(payload: ChatRequest, user: User = Depends(get_current_active_user)):
    """
    Stabilized Chat Endpoint. 
    Handles the immediate persistence for image generation reliability.
    """
    user_id = user.id
    username = user.username
    trace_id = f"req-{uuid.uuid4().hex[:6]}"
    
    logger.info(f"[CHAT_ENTRY] {username} | trace={trace_id} | m='{payload.message[:30]}'")

    # Rate Limiting Check
    try:
        limiter.check_limits_pre_flight(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        # Fail open per fail-soft policy, but log error


    if not payload.stream:
        # Standard non-streaming logic
        try:
            res = await process_chat_message(
                username=username, message=payload.message, user=user,
                force_local=payload.force_local, conversation_id=payload.conversation_id,
                requested_model=payload.model, stream=False
            )
            return MessageOut(id=res.get("id", -1), role="assistant", text=res.get("text", ""), time=datetime.now(), extra_metadata=res.get("extra_metadata"))
        except Exception as e:
            logger.error(f"Chat Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # STREAMING LOGIC
    # Pre-create conversation to set header before streaming starts
    local_conv_id = payload.conversation_id
    if not local_conv_id:
        summary = await asyncio.to_thread(conv_create, username=username, first_message=payload.message)
        local_conv_id = summary.id
        
        # Analytics: Chat start event'ini track et
        try:
            from app.core.analytics import track_chat_start
            track_chat_start(
                user_id=user_id,
                conversation_id=int(local_conv_id) if local_conv_id.isdigit() else hash(local_conv_id) % (10**8),
            )
        except Exception as e:
            logger.error(f"[Analytics] Chat start event tracking hatası: {e}")
    
    async def stream_and_save():
        full_reply = ""
        reasoning_log = []
        unified_sources = []
        stream_metadata = {}
        assistant_msg_id = None
        
        # 1. Establish IDs immediately (conversation already created above)
        try:
            # Add user message
            await asyncio.to_thread(
                conv_append, 
                username=username, 
                conv_id=local_conv_id, 
                role="user", 
                text=payload.message,
                images=payload.images # Vision Support
            )
            
            # Analytics: Message sent event'ini track et
            try:
                from app.core.analytics import track_message_sent
                track_message_sent(
                    user_id=user_id,
                    conversation_id=int(local_conv_id) if local_conv_id.isdigit() else hash(local_conv_id) % (10**8),
                    message_length=len(payload.message),
                    has_image=bool(payload.images),
                )
            except Exception as e:
                logger.error(f"[Analytics] Message sent event tracking hatası: {e}")
            
            # Assistant placeholder create
            initial_meta = _build_meta(
                engine="atlas", action="STREAM_START", forced=payload.force_local,
                persona=payload.persona or user.active_persona or "standard",
                model="brain-engine"
            )
            initial_meta["status"] = "streaming"
            
            assistant_msg_obj = await asyncio.to_thread(conv_append, username=username, conv_id=local_conv_id, role="bot", text="", extra_metadata=initial_meta)
            assistant_msg_id = assistant_msg_obj.id
            
            # HANDSHAKE: Send real IDs to frontend immediately
            yield json.dumps({"type": "metadata", "conversation_id": local_conv_id, "assistant_message_id": assistant_msg_id}) + "\n"
            
            # 2. Engine Run
            sp = payload.style_profile
            if isinstance(sp, dict): sp = StyleProfile(**sp)
            
            async for event in brain_engine.process_request_stream(
                user_id=str(user_id), username=username, message=payload.message,
                session_id=local_conv_id, persona=payload.persona or user.active_persona or "standard",
                style_profile=sp, message_id=assistant_msg_id,
                images=payload.images # Pass images to engine
            ):
                event_type = event.get("type", "")
                if event_type in ["chunk", "content"]:
                    full_reply += (event.get("content", "") or event.get("data", "") or "")
                elif event_type == "task_result":
                    res = event.get("result", {})
                    if res.get("type") == "tool" and res.get("tool_name") == "flux_tool":
                        out = res.get("output", {})
                        if isinstance(out, dict) and out.get("job_id"):
                            stream_metadata.update({"type": "image", "status": "queued", "job_id": out.get("job_id")})
                            # Intermediate update for image job persistence
                            await asyncio.to_thread(conv_update, assistant_msg_id, None, {**initial_meta, **stream_metadata})
                elif event_type == "thought":
                    reasoning_log.append({**event, "timestamp": int(datetime.now().timestamp() * 1000)})
                elif event_type == "sources":
                    unified_sources.extend(event.get("data", []))

                yield json.dumps(event) + "\n"
                
        except Exception as e:
            logger.error(f"[STREAM_ERR] {e}")
            yield json.dumps({"type": "error", "content": f"Bağlantı hatası: {str(e)}"}) + "\n"
        
        finally:
            # 3. Final Sync (GUARANTEED EXECUTION)
            # This block runs even if client disconnects (GeneratorExit) or error occurs
            if assistant_msg_id:
                try:
                    logger.info(f"[CHAT_FINAL_SYNC] Veritabanı güncelleniyor: MsgID={assistant_msg_id} Len={len(full_reply)}")
                    final_meta = {**initial_meta, **stream_metadata, "reasoning_log": reasoning_log, "unified_sources": unified_sources, "status": "complete" if not stream_metadata.get("job_id") else "queued"}
                    
                    # Ensure full_reply is not empty if we have data
                    content_to_save = full_reply.strip()
                    
                    if not content_to_save and not stream_metadata.get("job_id"):
                         logger.warning(f"[CHAT_FINAL_SYNC] Uyarı: İçerik boş! (Hata oluşmuş olabilir)")

                    await asyncio.to_thread(conv_update, assistant_msg_id, content_to_save, final_meta)
                except Exception as fe:
                    logger.error(f"[FINAL_ERR] Veritabanı kayıt hatası: {fe}")

    # Create response with X-Conversation-ID header
    response = StreamingResponse(stream_and_save(), media_type="application/x-ndjson")
    response.headers["X-Conversation-ID"] = local_conv_id
    return response

# --- OTHER ENDPOINTS ---
@router.get("/conversations", response_model=list[ConversationSummaryOut])
async def get_conversations(user: User = Depends(get_current_active_user)):
    convs = await asyncio.to_thread(conv_list, username=user.username)
    return [ConversationSummaryOut(id=c.id, title=c.title, created_at=c.created_at, updated_at=c.updated_at) for c in convs]

@router.get("/conversations/{conversation_id}", response_model=list[MessageOut])
async def get_conversation_endpoint(conversation_id: str, user: User = Depends(get_current_active_user)):
    messages = await asyncio.to_thread(conv_load_messages, username=user.username, conv_id=conversation_id)
    return [MessageOut(id=m.id, role=m.role, text=m.content, time=m.created_at, extra_metadata=m.extra_metadata) for m in messages]

@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str, user: User = Depends(get_current_active_user)):
    success = await asyncio.to_thread(conv_delete, username=user.username, conv_id=conversation_id)
    return {"status": "success" if success else "error"}
