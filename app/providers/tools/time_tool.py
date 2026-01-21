"""
Mami AI - Time Tool (Atlas Sovereign Edition)
---------------------------------------------
Zaman ve bağlam farkındalığı aracı.

Temel Sorumluluklar:
1. Zaman Enjeksiyonu: Güncel tarih ve saat bilgisi
2. Dinamik Selamlama: Günün saatine göre hitap
3. Aciliyet Tespiti: "Acil", "Hemen" gibi kelimeler
4. Yerelleştirme: Türkçe tarih formatı
"""

from datetime import datetime
from typing import Optional, Tuple, List, Any, Dict
from pydantic import BaseModel

from app.providers.tools.base import BaseTool


class TimeInput(BaseModel):
    """Time tool input schema."""
    message: Optional[str] = None


# Türkçe gün isimleri
DAYS_TR = {
    0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe",
    4: "Cuma", 5: "Cumartesi", 6: "Pazar"
}

# Türkçe ay isimleri
MONTHS_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

# Aciliyet anahtar kelimeleri
URGENCY_KEYWORDS = [
    "acil", "hemen", "çabuk", "ivedi", "derhal",
    "deadline", "son tarih", "bugün", "şimdi",
    "urgent", "asap", "immediately"
]


def get_greeting(hour: int = None) -> str:
    """Saat bazlı selamlama döndür."""
    if hour is None:
        hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "Günaydın"
    elif 12 <= hour < 18:
        return "İyi günler"
    elif 18 <= hour < 22:
        return "İyi akşamlar"
    else:
        return "İyi geceler"


def get_time_period(hour: int = None) -> str:
    """Günün zaman dilimini döndür."""
    if hour is None:
        hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "sabah"
    elif 12 <= hour < 14:
        return "öğle"
    elif 14 <= hour < 18:
        return "öğleden sonra"
    elif 18 <= hour < 22:
        return "akşam"
    else:
        return "gece"


def get_formatted_date(now: datetime = None) -> str:
    """Türkçe formatında tarih döndür."""
    if now is None:
        now = datetime.now()
    
    day_name = DAYS_TR[now.weekday()]
    month_name = MONTHS_TR[now.month]
    return f"{now.day} {month_name} {now.year}, {day_name}"


def detect_urgency(message: str) -> Tuple[bool, List[str]]:
    """
    Mesajda aciliyet tespiti yap.
    
    Returns:
        (acil_mi, bulunan_kelimeler)
    """
    message_lower = message.lower()
    found_keywords = [kw for kw in URGENCY_KEYWORDS if kw in message_lower]
    return bool(found_keywords), found_keywords


def get_time_context(message: str = "") -> str:
    """
    LLM için zaman bağlamı oluşturur.
    """
    now = datetime.now()
    parts = []
    
    parts.append("[ZAMAN BAĞLAMI]")
    parts.append(f"Şu an {get_formatted_date(now)}, saat {now.strftime('%H:%M')} ({get_time_period(now.hour)}).")
    
    if message:
        is_urgent, keywords = detect_urgency(message)
        if is_urgent:
            parts.append(f"⚠️ ACİL İŞARETİ: {', '.join(keywords)}")
    
    return "\n".join(parts)


class TimeTool(BaseTool):
    """Zaman ve tarih bilgisi aracı."""
    
    name = "time"
    description = "Güncel tarih, saat ve zaman dilimi bilgisi sağlar."
    input_schema = TimeInput
    
    async def execute(self, message: str = None, **kwargs) -> Dict[str, Any]:
        """Zaman bilgisini döndürür."""
        now = datetime.now()
        
        return {
            "date": get_formatted_date(now),
            "time": now.strftime("%H:%M:%S"),
            "period": get_time_period(now.hour),
            "greeting": get_greeting(now.hour),
            "context": get_time_context(message or ""),
            "urgency": detect_urgency(message or "") if message else (False, [])
        }


# Singleton
time_tool = TimeTool()
