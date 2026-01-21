from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth.dependencies import get_current_active_user
from app.core.logger import get_logger
from app.core.models import User
from app.memory.rag_service import rag_service
from app.memory import rag_v2_summary_processor

logger = get_logger(__name__)
router = APIRouter()

UPLOAD_ROOT = Path("data") / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# --- ENDPOINTS ---


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: str | None = Form(None),
    user: User = Depends(get_current_active_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı bulunamadı.")

    filename = file.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    ALLOWED_DOCS = ("pdf", "txt")
    ALLOWED_IMAGES = ("jpg", "jpeg", "png", "webp")

    if ext not in ALLOWED_DOCS and ext not in ALLOWED_IMAGES:
        raise HTTPException(status_code=400, detail="Desteklenmeyen dosya türü. (PDF, TXT, JPG, PNG)")

    user_dir = UPLOAD_ROOT / user.username
    # Resimler için ayrı klasör
    if ext in ALLOWED_IMAGES:
        user_dir = user_dir / "images"

    user_dir.mkdir(parents=True, exist_ok=True)

    safe_name = filename.replace("/", "_").replace("\\", "_")
    dest_path = user_dir / safe_name

    content = await file.read()
    with dest_path.open("wb") as out:
        out.write(content)

    # --- IMAGE FLOW (RAG SKIP) ---
    if ext in ALLOWED_IMAGES:
        return {
            "ok": True,
            "filename": filename,
            "type": "image",
            "path": f"{user.username}/images/{safe_name}",
            "rag_v2_indexed": False,
        }

    # --- DOCUMENT FLOW (RAG SERVICE) ---
    # Artık tüm logic (extraction, chunking, v1/v2 decision) servis içinde
    chunks_count = 0
    try:
        # Dosya tipine göre işle
        if ext == "pdf":
            chunks_count = rag_service.add_file(
                file_path=dest_path,
                filename=filename,
                owner=user.username,
                scope="user",
                conversation_id=conversation_id
            )
            
            # Background summary processing for large docs
            if chunks_count > 50:  # ~100+ pages
                try:
                    await rag_v2_summary_processor.queue_summary_job(
                        upload_id=dest_path.stem,  # Use filename as upload_id
                        filename=filename,
                        owner=user.username,
                        file_path=str(dest_path),
                        scope="user"
                    )
                    logger.info(f"[Documents] Summary processing queued for {filename}")
                except Exception as e:
                    # Non-critical - don't fail upload if summary job fails
                    logger.warning(f"[Documents] Failed to queue summary job: {e}")
        else: # For other document types like TXT
            chunks_count = rag_service.add_file(
                file_path=dest_path, filename=filename, owner=user.username, scope="user", conversation_id=conversation_id
            )
    except Exception as e:
        # Error logging with traceback (exc_info=True)
        logger.error(f"[UPLOAD] RAG ingestion failed: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Belge işlenirken hata: {str(e)}")

    if chunks_count == 0:
        raise HTTPException(status_code=400, detail="Belge işlenemedi veya boş.")

    return {
        "ok": True,
        "filename": filename,
        "chunks": chunks_count,
        "rag_v2_indexed": True,  # rag_service varsayılan olarak v2 kullanıyor
        "rag_v2_chunks": chunks_count,
    }


@router.get("/documents")
async def list_user_documents(user: User = Depends(get_current_active_user)):
    """Kullanıcının yüklediği dokümanları listeler."""
    return rag_service.list_user_documents(owner=user.username)


@router.delete("/documents/{filename}")
async def delete_user_document(filename: str, user: User = Depends(get_current_active_user)):
    """Dosya adına göre doküman siler."""
    deleted_count = rag_service.delete_document_by_filename(filename, user.username)

    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı veya silinemedi.")

    return {"ok": True, "deleted": deleted_count}
