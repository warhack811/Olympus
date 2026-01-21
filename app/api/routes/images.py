from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_active_user
from app.core.models import Conversation, Message, User
from app.image.gpu_state import get_state
from app.image.job_queue import job_queue
from app.image.pending_state import list_pending_jobs_for_user
import shutil
import os
from pathlib import Path
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()

# --- ŞEMALAR ---


class UserImageOut(BaseModel):
    index: int
    image_url: str
    prompt: str
    created_at: Any
    conversation_id: str | None = None


# --- ENDPOINTS ---


@router.get("/image/status")
async def check_image_status(user: User = Depends(get_current_active_user)):
    status = job_queue.get_queue_status()
    state_val = get_state()
    status["gpu_mode"] = state_val.value if hasattr(state_val, "value") else str(state_val)
    status["pending_jobs"] = list_pending_jobs_for_user(user.username)
    return status


@router.get("/image/job/{job_id}/status")
async def get_job_status_endpoint(job_id: str, user: User = Depends(get_current_active_user)):
    """
    Belirli bir job'un durumunu döndürür.
    Sayfa yenilendiğinde pending job'ların durumunu öğrenmek için kullanılır.
    """
    from app.image.pending_state import get_job_status

    job = get_job_status(job_id)
    if not job:
        # Job kuyrukta yok. Belki tamamlanmıştır?
        from sqlmodel import select
        from app.core.database import get_session
        from app.core.models import Message

        with get_session() as session:
            stmt = select(Message).where(Message.role == "bot").order_by(Message.created_at.desc()).limit(100)
            candidates = session.exec(stmt).all()
            
            for m in candidates:
                meta = m.extra_metadata or {}
                if meta.get("job_id") == job_id:
                    status = meta.get("status", "unknown")
                    return {
                        "job_id": job_id,
                        "status": status,
                        "progress": 100 if status == "complete" else 0,
                        "queue_position": 0,
                        "image_url": meta.get("image_url"),
                        "error": meta.get("error"),
                        "conversation_id": m.conversation_id,
                        "from_db": True
                    }

        return {
            "job_id": job_id,
            "status": "unknown",
            "progress": 0,
            "queue_position": 0,
            "message": "Job bulunamadı - tamamlanmış veya geçersiz olabilir",
        }

    # Sadece bu kullanıcıya ait job'ları göster
    if job.get("username") != user.username:
        return {"job_id": job_id, "status": "unknown", "progress": 0, "queue_position": 0, "message": "Erişim izni yok"}

    return {
        "job_id": job_id,
        "status": "processing" if job.get("progress", 0) > 0 else "queued",
        "progress": job.get("progress", 0),
        "queue_position": job.get("queue_pos", 1),
        "conversation_id": job.get("conversation_id"),
    }


@router.post("/image/job/{job_id}/cancel")
async def cancel_job_endpoint(job_id: str, user: User = Depends(get_current_active_user)):
    """
    Kuyruktaki bir görsel isteğini iptal eder.
    Sadece kuyrukta bekleyen işler iptal edilebilir.
    """
    success = await job_queue.cancel_job(job_id, user.username)

    if success:
        # Mesajı da güncelle
        from app.image.pending_state import get_job_status

        job = get_job_status(job_id)
        if job:
            # Burada message_id yok, pending_state'te tutmuyoruz
            # WebSocket zaten cancelled durumunu gönderdi
            pass

        return {"success": True, "message": "Job iptal edildi"}

    return {"success": False, "message": "Job bulunamadı veya zaten işleniyor"}


@router.get("/images", response_model=list[UserImageOut])
async def list_user_images(limit: int = 50, user: User = Depends(get_current_active_user)):
    from sqlmodel import col, select

    from app.core.database import get_session

    with get_session() as session:
        stmt = (
            select(Message)
            .join(Conversation)
            .where(Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == user.id)
            .where(Message.role == "bot")
            .order_by(col(Message.created_at).desc())
            .limit(limit * 3)
        )
        messages = session.exec(stmt).all()
        result = []
        for idx, msg in enumerate(messages):
            image_url = None
            meta = msg.extra_metadata or {}
            
            # 1. New metadata system check
            if meta.get("type") == "image" and meta.get("image_url"):
                image_url = meta.get("image_url")
            
            # 2. Legacy marker check
            elif "IMAGE_PATH:" in msg.content:
                image_url = msg.content.split("IMAGE_PATH:")[1].strip().split()[0]
            
            if image_url:
                result.append(
                    UserImageOut(
                        index=idx,
                        image_url=image_url,
                        prompt=meta.get("prompt", "") or "Görsel",
                        created_at=msg.created_at,
                        conversation_id=msg.conversation_id,
                    )
                )
            
            if len(result) >= limit:
                break
        return result


@router.post("/images/internal-upload")
async def internal_upload_image(
    file: UploadFile = File(...),
    x_forge_worker_token: str = Header(...),
):
    """
    Local Worker'dan gelen görseli güvenli bir şekilde sunucuya kaydeder.
    RAM Koruması: shutil.copyfileobj kullanılarak stream edilir.
    """
    if x_forge_worker_token != settings.INTERNAL_UPLOAD_TOKEN:
        logger.warning(f"[UPLOAD] Unauthorized internal upload attempt with token: {x_forge_worker_token}")
        raise HTTPException(status_code=403, detail="Invalid worker token")

    # Dosya yolunu belirle
    IMAGES_DIR = Path("data") / "images"
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Dosya adını güvenli hale getir veya olduğu gibi kullan (Worker zaten uniqleştiriyor)
    file_path = IMAGES_DIR / file.filename
    
    try:
        # RAM Korumalı Kayıt: Dosya içeriği belleğe alınmadan doğrudan diske stream edilir.
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Absolute URL support for cross-domain stability
        image_url = f"/images/{file.filename}"
        if settings.ATLAS_API_BASE_URL:
            base = settings.ATLAS_API_BASE_URL.rstrip("/")
            image_url = f"{base}/images/{file.filename}"

        logger.info(f"[UPLOAD] Image saved successfully: {file.filename} -> {image_url}")
        return {
            "success": True, 
            "image_url": image_url,
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"[UPLOAD] Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")
