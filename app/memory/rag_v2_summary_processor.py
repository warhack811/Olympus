"""
RAG v2 Summary Processor
========================

Background processor for generating page summaries after document upload.
This is a post-upload enhancement that doesn't block user upload flow.

Flow:
1. User uploads PDF → Normal chunking happens (fast)
2. Upload completes → User gets "success" message
3. Background: This processor generates summaries for large docs
4. Summary chunks are added to ChromaDB/FTS5
5. Next search automatically benefits from summaries
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def process_document_summaries(
    upload_id: str,
    filename: str,
    owner: str,
    file_path: str,
    scope: str = "user"
) -> Dict[str, Any]:
    """
    Process a document to generate and add page summaries.
    
    This function:
    1. Re-reads the PDF to get page texts
    2. Generates summaries for each page (100+ page docs only)
    3. Adds summary chunks to ChromaDB and FTS5
    
    Args:
        upload_id: Unique upload identifier
        filename: Original filename
        owner: Document owner
        file_path: Path to uploaded PDF
        scope: Document scope (default: "user")
    
    Returns:
        Dict with processing stats
    """
    from app.memory.rag_v2 import _generate_page_summary, _get_rag_v2_collection, _sanitize_filename
    from app.memory import rag_v2_lexical
    import PyPDF2
    
    logger.info(f"[Summary Processor] Starting summary generation for {filename} (upload_id: {upload_id})")
    
    stats = {
        "upload_id": upload_id,
        "filename": filename,
        "summaries_generated": 0,
        "summaries_added": 0,
        "errors": 0,
        "processing_time_ms": 0
    }
    
    start_time = datetime.now()
    
    try:
        # Check if file exists
        pdf_path = Path(file_path)
        if not pdf_path.exists():
            logger.error(f"[Summary Processor] File not found: {file_path}")
            stats["errors"] = 1
            return stats
        
        # Read PDF
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            
            # Only process large documents (100+ pages)
            if num_pages < 100:
                logger.info(f"[Summary Processor] Doc too small ({num_pages} pages), skipping")
                return stats
            
            logger.info(f"[Summary Processor] Processing {num_pages} pages for summaries")
            
            # Get collection
            collection = _get_rag_v2_collection()
            safe_filename = _sanitize_filename(filename)
            now = datetime.utcnow().isoformat()
            
            # Process each page
            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                
                try:
                    # Extract text
                    text = page.extract_text() or ""
                    text = text.strip()
                    
                    if len(text) < 100:
                        continue  # Skip short pages
                    
                    # Generate summary
                    summary = await _generate_page_summary(text, filename, page_num)
                    
                    if not summary:
                        continue  # Summary generation failed or skipped
                    
                    stats["summaries_generated"] += 1
                    
                    # Create summary chunk
                    summary_id = f"{owner}:{safe_filename}:{upload_id}:p{page_num}:summary"
                    summary_meta = {
                        "scope": scope,
                        "owner": owner,
                        "source": "page_summary",
                        "filename": filename,
                        "upload_id": upload_id,
                        "page_number": page_num,
                        "chunk_index": -1,  # Summary marker
                        "ingest_date": now,
                        "is_summary": True
                    }
                    
                    # Add to ChromaDB
                    collection.add(
                        ids=[summary_id],
                        documents=[summary],
                        metadatas=[summary_meta]
                    )
                    
                    # Add to FTS5
                    rag_v2_lexical.upsert_chunk(
                        doc_id=summary_id,
                        text=summary,
                        metadata=summary_meta
                    )
                    
                    stats["summaries_added"] += 1
                    
                    # Rate limiting: Her sayfa özeti sonrası n saniye bekle
                    await asyncio.sleep(2)
                    
                    # Log progress every 20 pages
                    if page_num % 20 == 0:
                        logger.info(f"[Summary Processor] Progress: {page_num}/{num_pages} pages")
                
                except Exception as e:
                    logger.error(f"[Summary Processor] Error processing page {page_num}: {e}", exc_info=True)
                    stats["errors"] += 1
                    continue
        
        # Calculate processing time
        end_time = datetime.now()
        stats["processing_time_ms"] = int((end_time - start_time).total_seconds() * 1000)
        
        logger.info(
            f"[Summary Processor] Completed: {stats['summaries_added']} summaries added "
            f"in {stats['processing_time_ms']}ms (errors: {stats['errors']})"
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"[Summary Processor] Fatal error: {e}", exc_info=True)
        stats["errors"] += 1
        return stats


# Simple in-memory task queue (production'da Redis/Celery kullanılabilir)
_summary_queue: Dict[str, Dict[str, Any]] = {}
_processing_lock: asyncio.Lock | None = None

def get_lock() -> asyncio.Lock:
    global _processing_lock
    if _processing_lock is None:
        _processing_lock = asyncio.Lock()
    return _processing_lock


async def queue_summary_job(
    upload_id: str,
    filename: str,
    owner: str,
    file_path: str,
    scope: str = "user"
):
    """
    Queue a summary processing job.
    
    In production, this would push to Redis/Celery.
    For now, we use a simple in-memory queue.
    """
    async with get_lock():
        _summary_queue[upload_id] = {
            "upload_id": upload_id,
            "filename": filename,
            "owner": owner,
            "file_path": file_path,
            "scope": scope,
            "status": "queued",
            "queued_at": datetime.now().isoformat()
        }
    
    logger.info(f"[Summary Processor] Queued job for {filename} (upload_id: {upload_id})")
    
    # Trigger background processing (non-blocking)
    asyncio.create_task(_background_worker(upload_id))


async def _background_worker(upload_id: str):
    """
    Background worker that processes summary jobs.
    """
    try:
        # Get job from queue
        async with get_lock():
            job = _summary_queue.get(upload_id)
            if not job:
                return
            
            job["status"] = "processing"
            job["started_at"] = datetime.now().isoformat()
        
        # Process summaries
        stats = await process_document_summaries(
            upload_id=job["upload_id"],
            filename=job["filename"],
            owner=job["owner"],
            file_path=job["file_path"],
            scope=job.get("scope", "user")
        )
        
        # Update job status
        async with get_lock():
            if upload_id in _summary_queue:
                _summary_queue[upload_id]["status"] = "completed"
                _summary_queue[upload_id]["completed_at"] = datetime.now().isoformat()
                _summary_queue[upload_id]["stats"] = stats
        
        logger.info(f"[Summary Processor] Job completed: {upload_id}")
        
    except Exception as e:
        logger.error(f"[Summary Processor] Worker error for {upload_id}: {e}", exc_info=True)
        async with get_lock():
            if upload_id in _summary_queue:
                _summary_queue[upload_id]["status"] = "failed"
                _summary_queue[upload_id]["error"] = str(e)


def get_job_status(upload_id: str) -> Dict[str, Any] | None:
    """
    Get the status of a summary processing job.
    
    Returns:
        Job status dict or None if not found
    """
    return _summary_queue.get(upload_id)
