"""
Mami AI - Notification Gatekeeper (Atlas Sovereign Edition)
-----------------------------------------------------------
Bildirim bekçisi - Sistem kullanıcıya bir şey söylemek istediğinde
"Şu an uygun mu?" kararını verir.

Kurallar:
1. Quiet Hours: Uyku saatindeyse bildirim atma
2. Fatigue Control: Günde X bildirimden fazlasını atma
3. Priority Override: ACİL işaretli bildirimler kuralları ezebilir
"""

import logging
from typing import Tuple, Optional, Dict, Any
from datetime import datetime

from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger(__name__)


# Default settings
DEFAULT_QUIET_HOURS = (23, 7)  # 23:00 - 07:00
DEFAULT_DAILY_LIMIT = 10
PRIORITY_KEYWORDS = ["acil", "urgent", "hemen", "kritik", "son dakika"]


def is_in_quiet_hours(
    current_hour: int,
    quiet_start: int = DEFAULT_QUIET_HOURS[0],
    quiet_end: int = DEFAULT_QUIET_HOURS[1]
) -> bool:
    """
    Şu an sessiz saatlerde mi kontrol et.
    
    Args:
        current_hour: Şu anki saat (0-23)
        quiet_start: Sessiz saat başlangıcı
        quiet_end: Sessiz saat bitişi
    
    Returns:
        True ise sessiz saatlerde
    """
    # Handle wrap-around (e.g., 23:00 - 07:00)
    if quiet_start > quiet_end:
        return current_hour >= quiet_start or current_hour < quiet_end
    else:
        return quiet_start <= current_hour < quiet_end


def is_priority_message(message: str) -> bool:
    """Mesajda öncelik anahtar kelimesi var mı kontrol et."""
    message_lower = message.lower()
    return any(kw in message_lower for kw in PRIORITY_KEYWORDS)


async def get_user_notification_settings(
    user_id: str,
    graph_repo = None
) -> Dict[str, Any]:
    """
    Kullanıcının bildirim ayarlarını Neo4j'den çeker.
    
    Returns:
        {"quiet_start": int, "quiet_end": int, "daily_limit": int, "timezone": str}
    """
    default_settings = {
        "quiet_start": DEFAULT_QUIET_HOURS[0],
        "quiet_end": DEFAULT_QUIET_HOURS[1],
        "daily_limit": DEFAULT_DAILY_LIMIT,
        "timezone": "Europe/Istanbul"
    }
    
    if not graph_repo:
        return default_settings
    
    try:
        query = """
        MATCH (u:User {id: $uid})
        RETURN u.notification_quiet_start as quiet_start,
               u.notification_quiet_end as quiet_end,
               u.notification_daily_limit as daily_limit,
               u.timezone as timezone
        """
        result = await graph_repo.query(query, {"uid": user_id})
        
        if result and result[0]:
            r = result[0]
            return {
                "quiet_start": r.get("quiet_start") or default_settings["quiet_start"],
                "quiet_end": r.get("quiet_end") or default_settings["quiet_end"],
                "daily_limit": r.get("daily_limit") or default_settings["daily_limit"],
                "timezone": r.get("timezone") or default_settings["timezone"]
            }
            
    except Exception as e:
        logger.warning(f"[Gatekeeper] Settings fetch error: {e}")
    
    return default_settings


async def get_today_notification_count(
    user_id: str,
    graph_repo = None
) -> int:
    """Bugün gönderilen bildirim sayısını al."""
    if not graph_repo:
        return 0
    
    try:
        query = """
        MATCH (u:User {id: $uid})-[:HAS_NOTIFICATION]->(n:Notification)
        WHERE date(n.created_at) = date()
        RETURN count(n) as count
        """
        result = await graph_repo.query(query, {"uid": user_id})
        return result[0]["count"] if result else 0
        
    except Exception as e:
        logger.warning(f"[Gatekeeper] Count fetch error: {e}")
        return 0


async def should_emit_notification(
    user_id: str,
    message: str = "",
    is_priority: bool = False,
    graph_repo = None
) -> Tuple[bool, str]:
    """
    Bildirim gönderilmeli mi kararı ver.
    
    Args:
        user_id: Kullanıcı ID
        message: Bildirim mesajı (öncelik tespiti için)
        is_priority: Zorla öncelikli mi
        graph_repo: Graph repository
    
    Returns:
        (izin_var_mı, sebep)
    """
    # 1. Priority override check
    if is_priority or is_priority_message(message):
        telemetry.emit(
            EventType.SYSTEM,
            {"op": "gatekeeper_priority_override", "user_id": user_id},
            component="notificator"
        )
        return True, "priority_override"
    
    # 2. Get user settings
    settings = await get_user_notification_settings(user_id, graph_repo)
    
    # 3. Quiet hours check
    current_hour = datetime.now().hour
    if is_in_quiet_hours(current_hour, settings["quiet_start"], settings["quiet_end"]):
        telemetry.emit(
            EventType.SYSTEM,
            {"op": "gatekeeper_blocked", "reason": "quiet_hours", "user_id": user_id},
            component="notificator"
        )
        return False, "quiet_hours"
    
    # 4. Daily limit check
    today_count = await get_today_notification_count(user_id, graph_repo)
    if today_count >= settings["daily_limit"]:
        telemetry.emit(
            EventType.SYSTEM,
            {"op": "gatekeeper_blocked", "reason": "daily_limit", "count": today_count},
            component="notificator"
        )
        return False, f"daily_limit_exceeded ({today_count}/{settings['daily_limit']})"
    
    # 5. All checks passed
    return True, "allowed"


async def create_notification(
    user_id: str,
    message: str,
    notification_type: str = "general",
    source: str = "system",
    related_task_id: Optional[str] = None,
    graph_repo = None
) -> Optional[str]:
    """
    Bildirim oluştur (gatekeeper kontrolünden sonra çağrılmalı).
    
    Returns:
        Notification ID veya None
    """
    import uuid
    notif_id = str(uuid.uuid4())[:8]
    
    if not graph_repo:
        logger.warning("[Notificator] No graph_repo, notification not saved")
        return notif_id
    
    try:
        query = """
        MATCH (u:User {id: $uid})
        CREATE (n:Notification {
            id: $notif_id,
            user_id: $uid,
            message: $message,
            type: $type,
            source: $source,
            related_task_id: $task_id,
            created_at: datetime(),
            read: false
        })
        MERGE (u)-[:HAS_NOTIFICATION]->(n)
        RETURN n.id as id
        """
        
        await graph_repo.query(query, {
            "uid": user_id,
            "notif_id": notif_id,
            "message": message,
            "type": notification_type,
            "source": source,
            "task_id": related_task_id
        })
        
        logger.info(f"[Notificator] Notification created: {notif_id}")
        return notif_id
        
    except Exception as e:
        logger.error(f"[Notificator] Creation error: {e}")
        return None


class NotificationGatekeeper:
    """Notification Gatekeeper singleton wrapper."""
    
    def __init__(self, graph_repo = None):
        self.graph_repo = graph_repo
    
    async def should_emit(self, user_id: str, message: str = "", is_priority: bool = False) -> Tuple[bool, str]:
        return await should_emit_notification(user_id, message, is_priority, self.graph_repo)
    
    async def create_notification(
        self,
        user_id: str,
        message: str,
        notification_type: str = "general",
        source: str = "system",
        related_task_id: str = None
    ) -> Optional[str]:
        return await create_notification(
            user_id, message, notification_type, source, related_task_id, self.graph_repo
        )
    
    async def emit_if_allowed(
        self,
        user_id: str,
        message: str,
        notification_type: str = "general",
        source: str = "system",
        is_priority: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Gatekeeper kontrolü yapıp izin varsa bildirim oluşturur."""
        allowed, reason = await self.should_emit(user_id, message, is_priority)
        
        if allowed:
            notif_id = await self.create_notification(user_id, message, notification_type, source)
            return True, notif_id
        else:
            return False, None


notification_gatekeeper = NotificationGatekeeper()
