# app/orchestrator_v42/response_postprocess.py

from typing import Dict, Any
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
from app.orchestrator_v42.plugins import output_sanitizer, streaming_rewriter

async def postprocess_response_text(
    text: str, 
    flags: OrchestratorFeatureFlags, 
    trace_id: str | None = None
) -> Dict[str, Any]:
    """
    Adapter yanıtını son işlemden geçirir (Async).
    
    İşlemler:
    1. Boş metin kontrolü.
    2. Output Sanitizer (Fence onarımı, whitespace temizliği).
    3. Streaming Rewriter simülasyonu (Streaming flag açık ise).
    
    Dönüş:
    {
        "text": str,   # İşlenmiş metin
        "was_sanitized": bool, 
        "was_stream_rewritten": bool,
        "notes": str   # İşlem notları veya hata mesajı
    }
    """
    
    result = {
        "text": text,
        "was_sanitized": False,
        "was_stream_rewritten": False,
        "notes": "İşlem tamamlandı"
    }
    
    # 1. Boş Metin Kontrolü
    if not text:
        result["notes"] = "Girdi metni boş"
        return result

    try:
        # 2. Sanitizer (Sync çalışır)
        sanitized = output_sanitizer.sanitize(text)
        if sanitized != text:
            result["text"] = sanitized
            result["was_sanitized"] = True
            
        # 3. Streaming Rewrite (Async çalışır)
        if flags.streaming_enabled:
            chunk_size = 30
            # Metni simülasyon için parçalara böl
            chunks = [result["text"][i:i+chunk_size] for i in range(0, len(result["text"]), chunk_size)]
            
            rewriter = streaming_rewriter.StreamingRewriter()
            # rewrite_chunks -> (final_text, report)
            final_stream_text, _ = await rewriter.rewrite_chunks(chunks)
            
            if final_stream_text: 
                result["text"] = final_stream_text
                result["was_stream_rewritten"] = True
            
    except Exception as e:
        # Hata durumunda akışı bozma, not düş (Fail-soft)
        result["notes"] = f"Son işleme hatası: {str(e)}"

    return result
