"""
WebSocket İletişim Modülü
=========================

Bu modül, gerçek zamanlı bildirimler için WebSocket mesajlarını yönetir.
(Eski: app/web socket_sender.py)

Desteklenen Mesaj Tipleri:
    - image_progress: Görsel üretim ilerleme durumu
    - image_complete: Görsel üretim tamamlandı
    - image_error: Görsel üretim hatası
    - notification: Genel bildirimler
"""

import logging
import json
import asyncio
import threading
import os
from enum import Enum
from typing import Any, Literal, Set
from fastapi import WebSocket
import redis.asyncio as redis
from app.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)

# Lightweight metrics (internal memory)
metrics = {
    "ws_image_event_sent_count": 0,
    "ws_image_event_dropped_no_target_count": 0,
    "ws_image_event_no_recipient_count": 0
}
metrics_lock = threading.Lock()

# WebSocket bağlantıları: {ws: {user_id_str, username}} identity set mapping
connected: dict[Any, Set[str]] = {}


class ImageJobStatus(str, Enum):
    """Görsel üretim iş durumları."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


def register_connection(ws: WebSocket, user_id: Any, username: str):
    """
    Register WebSocket connection with an identity set for dual-target matching (ID or Name).
    """
    # Create a set containing both the string version of user_id and the username
    identity_set = {str(user_id), str(username)}
    connected[ws] = identity_set
    logger.info(f"[WS] Registered: {username} (total: {len(connected)})")


def unregister_connection(ws: WebSocket) -> None:
    """WebSocket bağlantısını kaldır."""
    if ws in connected:
        identity_set = connected[ws]
        logger.info(f"[WS] Unregistered: {identity_set}")
        del connected[ws]


async def send_image_progress(
    username: str,
    conversation_id: str | None,
    job_id: str,
    status: ImageJobStatus,
    progress: int = 0,
    queue_position: int = 1,
    prompt: str | None = None,
    image_url: str | None = None,
    error: str | None = None,
    estimated_seconds: int | None = None,
    message_id: int | None = None,
) -> int:
    """
    Görsel üretim ilerlemesini WebSocket üzerinden gönderir.

    Args:
        username: Kullanıcı adı
        conversation_id: Sohbet ID'si
        job_id: İş ID'si (benzersiz)
        status: İş durumu (queued, processing, complete, error)
        progress: İlerleme yüzdesi (0-100)
        queue_position: Kuyruk pozisyonu
        prompt: Görsel prompt'u (kısa versiyon)
        image_url: Tamamlanmış görsel URL'i
        error: Hata mesajı (error durumunda)
        estimated_seconds: Tahmini kalan süre (saniye)

    Returns:
        int: Gönderilen istemci sayısı
    """
    # Validation
    if not conversation_id:
        logger.error("[WS] conversation_id is required but missing")
        return 0
    
    if message_id is None:
        logger.warning(f"[WS] message_id missing for job {job_id[:8]}")
    
    # Payload oluştur
    payload: dict[str, Any] = {
        "type": "image_progress",
        "job_id": job_id,
        "conversation_id": str(conversation_id),
        "status": status.value,
        "progress": min(max(progress, 0), 100),
        "queue_position": queue_position,
        "username": username,
    }

    # Message ID STRING olarak ekle
    if message_id is not None:
        payload["message_id"] = str(message_id)

    # Opsiyonel alanlar
    if prompt:
        # Prompt'u kısalt (max 100 karakter)
        payload["prompt"] = prompt[:100] + "..." if len(prompt) > 100 else prompt

    if image_url:
        payload["image_url"] = image_url

    if error:
        payload["error"] = error

    if estimated_seconds is not None:
        payload["estimated_seconds"] = estimated_seconds

    # Targeted send (broadcast yerine)
    sent_count = await send_to_user(username, payload)

    # Loglama
    log_msg = f"[WS_SENDER] Job {job_id[:8]} | {status.value} | {progress}%"
    if sent_count > 0:
        logger.info(f"{log_msg} → {sent_count} clients")
    else:
        logger.warning(f"{log_msg} → No clients connected!")

    return sent_count


# ═══════════════════════════════════════════════════════════════════════════
# REDIS PUB/SUB BRIDGE (Atlas Hybrid Connectivity)
# ═══════════════════════════════════════════════════════════════════════════

async def start_redis_bridge():
    """
    Subscribe to Redis channel and relay image progress to WebSocket clients.
    """
    try:
        r = redis.from_url(
            settings.get_redis_url(settings.REDIS_DB_QUEUE),
            decode_responses=True
        )
        pubsub = r.pubsub()
        channel_name = "atlas_image_status_stream"
        
        await pubsub.subscribe(channel_name)
        logger.info(f"Redis bridge subscribed to: {channel_name}")
        
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    
                    target = data.get("username") or data.get("user_id")
                    
                    logger.info(f"[WS_BRIDGE] Received event: type={data.get('type')}, target={target}, job_id={data.get('job_id', 'N/A')[:8]}, status={data.get('status')}")
                    
                    if target:
                        sent_count = await send_to_user(str(target), data)
                        if sent_count == 0:
                            logger.warning(f"[WS_BRIDGE] Target '{target}' not connected. Active connections: {len(connected)}")
                            # Log active usernames for debugging
                            active_users = [list(identity_set) for identity_set in connected.values()]
                            logger.debug(f"[WS_BRIDGE] Active users: {active_users}")
                    else:
                        logger.warning("Event received without target username/user_id, dropping")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WS_BRIDGE] Error processing redis message: {e}")
                await asyncio.sleep(2)
                
    except Exception as e:
        logger.error(f"Redis bridge error: {e}", exc_info=True)
        # Auto-retry after delay
        await asyncio.sleep(5)
        asyncio.create_task(start_redis_bridge())


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY - Eski fonksiyon (deprecated)
# ═══════════════════════════════════════════════════════════════════════════


async def send_progress(
    username: str,
    conv_id: str | None,
    prog: int,
    pos: int,
    path: str | None = None,
    job_id: str | None = None,
    prompt: str | None = None,
    message_id: int | None = None,
) -> None:
    """
    DEPRECATED: Eski format için backward compatibility.
    Yeni kod send_image_progress() kullanmalı.
    """
    # Durumu belirle
    if path is not None:
        status = ImageJobStatus.COMPLETE
    elif prog > 0:
        status = ImageJobStatus.PROCESSING
    else:
        status = ImageJobStatus.QUEUED

    await send_image_progress(
        username=username,
        conversation_id=conv_id,
        job_id=job_id or "unknown",
        status=status,
        progress=prog,
        queue_position=pos,
        prompt=prompt,
        image_url=path,
        message_id=message_id,
    )


# ═══════════════════════════════════════════════════════════════════════════
# GENEL BİLDİRİMLER
# ═══════════════════════════════════════════════════════════════════════════


async def send_to_user(username_or_id: str, message: dict[str, Any]) -> int:
    """
    Belirli bir kullanıcıya WebSocket mesajı gönderir.

    Args:
        username_or_id: Hedef kullanıcı adı VEYA user_id (string)
        message: Gönderilecek JSON mesajı

    Returns:
        int: Gönderilen mesaj sayısı
    
    Note:
        Identity set matching sayesinde hem user_id hem username ile hedefleme mümkün.
    """
    sent_count = 0
    target = str(username_or_id)
    
    for ws, identity_set in list(connected.items()):
        if target in identity_set:  # Set membership check
            try:
                await ws.send_json(message)
                sent_count += 1
                logger.debug(f"[WS] Sent to {target}: {message.get('type')}")
            except Exception as e:
                logger.debug(f"[WS] Failed to send to {target}: {e}")
    
    with metrics_lock:
        if sent_count > 0:
            metrics["ws_image_event_sent_count"] += sent_count
        else:
            metrics["ws_image_event_no_recipient_count"] += 1
            logger.warning("[WS] No recipient found for target (PII HIDDEN)")
    
    return sent_count


async def disconnect_user(username_or_id: str) -> int:
    """
    Belirli bir kullanıcının tüm açık WebSocket bağlantılarını sunucu tarafında zorla kapatır.
    Logout veya Ban durumlarında kullanılır.
    """
    closed_count = 0
    target = str(username_or_id)
    
    # Kopyasını alıyoruz çünkü döngü sırasında dictionary değişebilir
    for ws, identity_set in list(connected.items()):
        if target in identity_set:
            try:
                await ws.close(code=1000, reason="Logout")
                # unregister_connection(ws) -> ws.close sonrası main.py'deki loop kırılınca zaten çağrılacak
                closed_count += 1
            except Exception:
                pass
                
    if closed_count > 0:
        logger.info(f"[WS] Forcefully disconnected {closed_count} sessions for {target}")
    return closed_count


async def send_notification(
    username: str,
    title: str,
    message: str,
    notification_type: Literal["info", "success", "warning", "error"] = "info",
) -> int:
    """
    Kullanıcıya bildirim gönderir.

    Args:
        username: Hedef kullanıcı adı
        title: Bildirim başlığı
        message: Bildirim mesajı
        notification_type: Bildirim tipi

    Returns:
        int: Gönderilen mesaj sayısı
    """
    payload = {
        "type": "notification",
        "data": {
            "type": notification_type,
            "title": title,
            "message": message,
        },
    }

    return await send_to_user(username, payload)


async def broadcast(message: dict[str, Any]) -> int:
    """
    Tüm bağlı kullanıcılara mesaj gönderir.

    Args:
        message: Gönderilecek JSON mesajı

    Returns:
        int: Gönderilen mesaj sayısı
    """
    sent_count = 0
    for ws in list(connected.keys()):
        try:
            await ws.send_json(message)
            sent_count += 1
        except Exception as e:
            logger.debug(f"[WS] Failed to broadcast: {e}")

    return sent_count
