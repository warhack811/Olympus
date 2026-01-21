"""
Mami AI - Oturum Yönetimi
=========================

Bu modül, kullanıcı oturumlarını (session) yönetir.

Özellikler:
    - Güvenli token oluşturma (secrets modülü)
    - Oturum süresi yönetimi (varsayılan 24 saat)
    - Session touch (keep-alive)
    - Otomatik temizlik (expired sessions)

Kullanım:
    from app.auth.session import create_session, invalidate_session

    # Oturum oluştur
    session = create_session(user, user_agent="Mozilla/5.0...")

    # Oturumu sonlandır
    invalidate_session(session.id)

Güvenlik:
    - Token: secrets.token_urlsafe(32) - 256-bit entropi
    - Süresi dolmuş oturumlar otomatik reddedilir
    - Banlı kullanıcıların oturumları geçersizleştirilir
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from fastapi import Request
from sqlmodel import select

# Modül logger'ı
logger = logging.getLogger(__name__)

# =============================================================================
# SABİTLER
# =============================================================================

SESSION_DEFAULT_TTL_MINUTES = 60 * 24  # 24 saat
"""Varsayılan oturum süresi (dakika cinsinden)."""



from app.config import get_settings
from app.core.database import get_session
from app.auth.models import Session, User
from app.auth.dependencies import SESSION_COOKIE_NAME
from app.auth import remember as remember_mgr



# =============================================================================
# OTURUM YÖNETİMİ
# =============================================================================


def create_session(
    user,
    user_agent: str | None = None,
    ip_address: str | None = None,
):
    """
    Yeni oturum oluşturur.

    Args:
        user: Kullanıcı nesnesi (User model)
        user_agent: Tarayıcı bilgisi (opsiyonel)
        ip_address: IP adresi (opsiyonel, gelecekte kullanılabilir - şu an kullanılmıyor)

    Returns:
        Session: Oluşturulan oturum kaydı

    Raises:
        Exception: Veritabanı hatası durumunda

    Example:
        >>> session = create_session(user, user_agent=request.headers.get("user-agent"))
        >>> response.set_cookie("session_token", session.id)
    """

    # Lazy import only for user_manager to avoid potential circular dependency if it imports session
    # But since models are split, this should be safer, but let's keep it minimal.
    # Actually, we can try importing it at top level if user_manager doesn't import session.
    # Check shows user_manager imports: logging, typing, passlib, sqlmodel. No session import.
    # But let's check if it imports models that import session.
    from app.auth.user_manager import get_user_by_id


    token = secrets.token_urlsafe(32)  # 256-bit güvenli token
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=SESSION_DEFAULT_TTL_MINUTES)

    new_session = Session(
        id=token,
        user_id=user.id,
        type="active_session",
        expires_at=expires_at,
        user_agent=user_agent,
        created_at=now,
    )

    with get_session() as db:
        try:
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            logger.info(f"[SESSION] Yeni oturum açıldı: user_id={user.id}")
            return new_session
        except Exception as e:
            db.rollback()
            logger.error(f"[SESSION] Oturum oluşturma hatası: {e}")
            raise


def get_session_by_token(token: str):
    """
    Token'a ait geçerli oturumu getirir.

    Args:
        token: Oturum token'ı

    Returns:
        Session veya None: Geçerli oturum varsa döndürür
    """
    if not token:
        return None


    now = datetime.utcnow()

    with get_session() as db:
        stmt = select(Session).where(
            Session.id == token,
            Session.expires_at > now,
        )
        return db.exec(stmt).first()


def invalidate_session(token: str) -> bool:
    """
    Oturumu sonlandırır (Logout).

    Args:
        token: Sonlandırılacak oturum token'ı

    Returns:
        bool: Başarılı ise True
    """
    if not token:
        return False



    with get_session() as db:
        session_obj = db.get(Session, token)
        if not session_obj:
            return False

        try:
            db.delete(session_obj)
            db.commit()
            logger.info(f"[SESSION] Oturum sonlandırıldı: {token[:8]}...")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"[SESSION] Oturum kapatma hatası: {e}")
            return False


def touch_session(token: str) -> bool:
    """
    Oturum süresini uzatır (keep-alive).

    Her istek sonrası çağrılarak oturumun süresini yeniler.

    Args:
        token: Oturum token'ı

    Returns:
        bool: Başarılı ise True
    """
    if not token:
        return False


    now = datetime.utcnow()

    with get_session() as db:
        session_obj = db.get(Session, token)
        if not session_obj:
            return False

        # Süresi dolmuşsa uzatma
        if session_obj.expires_at <= now:
            return False

        session_obj.expires_at = now + timedelta(minutes=SESSION_DEFAULT_TTL_MINUTES)

        try:
            db.add(session_obj)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.debug(f"[SESSION] Touch hatası: {e}")
            return False


def get_user_from_session_token(token: str):
    """
    Session token'ından kullanıcıyı çözer.

    İşlem: Token → Session → User

    Args:
        token: Oturum token'ı

    Returns:
        User veya None: Geçerli kullanıcı varsa döndürür

    Note:
        Banlı kullanıcıların oturumları otomatik sonlandırılır.
    """
    from app.auth.user_manager import get_user_by_id

    session_obj = get_session_by_token(token)
    if not session_obj:
        return None

    user = get_user_by_id(session_obj.user_id)
    if not user:
        invalidate_session(token)
        return None

    if user.is_banned:
        logger.warning(f"[SESSION] Banlı kullanıcı erişim denemesi: {user.username}")
        invalidate_session(token)
        return None

    return user


def cleanup_expired_sessions(_max_age_minutes: int = 1440) -> int:
    """
    Süresi dolmuş oturumları temizler.

    Periyodik bakım görevi olarak çalıştırılmalıdır.

    Args:
        _max_age_minutes: Maksimum oturum yaşı (şu an kullanılmıyor, expires_at kullanılıyor)

    Returns:
        int: Temizlenen oturum sayısı
    """

    now = datetime.utcnow()
    removed = 0

    with get_session() as db:
        stmt = select(Session).where(Session.expires_at <= now)
        expired_sessions = db.exec(stmt).all()

        for sess in expired_sessions:
            db.delete(sess)
            removed += 1

        if removed > 0:
            try:
                db.commit()
                logger.info(f"[SESSION] {removed} adet süresi dolmuş oturum temizlendi.")
            except Exception as e:
                db.rollback()
                logger.error(f"[SESSION] Temizlik hatası: {e}")

    return removed


def get_username_from_request(request: Request) -> str | None:
    """
    HTTP isteğinden kullanıcı adını çıkarır.

    Öncelik sırası:
    1. Normal session cookie
    2. Remember me token

    Args:
        request: FastAPI Request nesnesi

    Returns:
        str veya None: Kullanıcı adı
    """


    # 1) Normal session cookie
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    if sid:
        try:
            with get_session() as db:
                sess = db.exec(select(Session).where(Session.id == sid)).first()

                if sess and (sess.expires_at is None or sess.expires_at > datetime.utcnow()):
                    user = db.get(User, sess.user_id)
                    if user:
                        return user.username
        except Exception as e:
            logger.error(f"[SESSION] get_username_from_request session hatası: {e}")

    # 2) Remember me cookie
    token = request.cookies.get(remember_mgr.REMEMBER_COOKIE_NAME)
    if not token:
        return None

    username = remember_mgr.get_username_from_token(token)
    if username:
        return username

    return None


