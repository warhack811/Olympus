# app/orchestrator_v42/observability.py

import logging
import uuid
import json
from datetime import datetime

logger = logging.getLogger("orchestrator")

def generate_trace_id() -> str:
    """İstek döngüsü için benzersiz bir İzleme Kimliği (Trace ID) oluşturur."""
    return f"orch-{uuid.uuid4().hex[:8]}"

def log_event(trace_id: str, event: str, metadata: dict = None):
    """
    Bir olayı, yapılandırılmış metadata ile birlikte güvenli JSON formatında loglar.
    Loglama hatalarının uygulama akışını bozmasını engeller.
    """
    meta_str = ""
    if metadata:
        try:
            # Bilinmeyen tipler için default=str kullanarak güvenli serileştirme
            meta_json = json.dumps(metadata, default=str, ensure_ascii=False)
            meta_str = f" | {meta_json}"
        except Exception:
            # Serileştirme hatası durumunda yalın string dönüşümü
            meta_str = f" | {str(metadata)}"
            
    logger.info(f"[{trace_id}] {event}{meta_str}")
