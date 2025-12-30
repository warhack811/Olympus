# app/orchestrator_v42/plugins/output_sanitizer.py

import logging

logger = logging.getLogger("orchestrator.sanitizer")

def sanitize(text: str) -> str:
    """
    Çıktı Temizleyici - Kural Tabanlı.
    
    1. Kapanmamış Markdown kod bloklarını (fence) kapatır.
    2. Satır sonlarındaki gereksiz boşlukları (trailing whitespace) temizler.
    3. (Faz 10.0) Semantik koruma sağlar (içeriği bozmaz).
    """
    try:
        if not text:
            return ""
            
        # 1. Trailing Whitespace Temizliği (Satır bazlı)
        lines = text.split('\n')
        # Her satırın sağ tarafındaki boşlukları sil
        cleaned_lines = [line.rstrip() for line in lines]
        sanitized_text = '\n'.join(cleaned_lines)
        
        # 2. Markdown Fence Kontrolü
        # ``` dizisinin sayısı tek ise, sonuna bir tane ekle
        fence_count = sanitized_text.count("```")
        if fence_count % 2 != 0:
            # Eğer son satır boş değilse yeni satıra geç
            if sanitized_text and not sanitized_text.endswith('\n'):
                sanitized_text += "\n"
            sanitized_text += "```"
            
        return sanitized_text

    except Exception as e:
        logger.error(f"Sanitizer hatası: {e}")
        # Fail-safe: Orijinal metni olduğu gibi dön
        return text
