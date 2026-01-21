"""
Log Retention & Cleanup Modülü
================================

Bu modül, eski log'ları otomatik olarak silmek ve yönetmek için kullanılır.

Özellikler:
    - 90 günden eski log'ları sil
    - Silme işleminden önce backup'la
    - Silme işlemini log'a yaz
    - Admin'e email ile bildir
    - Dry-run modunda test edebilme
    - Başarısız olursa retry mekanizması
    - Scheduled cleanup job'ı (günde bir kere, gece saatlerinde)

Kullanım:
    from app.core.log_cleanup import (
        LogCleanupManager,
        get_cleanup_manager,
        run_cleanup,
    )

    # Cleanup manager'ı başlat
    manager = get_cleanup_manager()
    await manager.start()
    
    # Cleanup'ı manuel olarak çalıştır
    result = await run_cleanup(dry_run=False)

Ortam Değişkenleri:
    LOG_RETENTION_DAYS: Log saklama süresi gün cinsinden (varsayılan: 90)
    LOG_CLEANUP_HOUR: Cleanup'ın çalışacağı saat (varsayılan: 2 - saat 02:00)
    LOG_CLEANUP_ENABLED: Cleanup'ı enable/disable et (varsayılan: true)
    CLEANUP_RETRY_COUNT: Başarısız cleanup'ı kaç kere retry et (varsayılan: 3)
    CLEANUP_RETRY_DELAY_SECONDS: Retry'lar arasında bekleme süresi (varsayılan: 300)
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta, time
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import aiosmtplib
import json

from app.core.logger import get_logger, log_event
from app.core.elasticsearch_client import (
    get_elasticsearch_client,
    delete_old_logs,
    backup_logs,
    get_index_stats,
    get_index_name,
)
from app.core.alerting import (
    get_alert_manager,
    AlertType,
    AlertSeverity,
)

# =============================================================================
# YAPILANDIRMA SABİTLERİ
# =============================================================================

# Log retention policy
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "90"))

# Cleanup schedule (saat cinsinden, 0-23)
LOG_CLEANUP_HOUR = int(os.getenv("LOG_CLEANUP_HOUR", "2"))

# Cleanup enable/disable
LOG_CLEANUP_ENABLED = os.getenv("LOG_CLEANUP_ENABLED", "true").lower() == "true"

# Retry ayarları
CLEANUP_RETRY_COUNT = int(os.getenv("CLEANUP_RETRY_COUNT", "3"))
CLEANUP_RETRY_DELAY_SECONDS = int(os.getenv("CLEANUP_RETRY_DELAY_SECONDS", "300"))

# Backup ayarları
BACKUP_DIR = "data/elasticsearch_backups"

# =============================================================================
# ENUM'LAR
# =============================================================================


class CleanupStatus(str, Enum):
    """Cleanup işleminin durumu."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class CleanupPhase(str, Enum):
    """Cleanup işleminin aşaması."""
    BACKUP = "backup"
    DELETE = "delete"
    NOTIFICATION = "notification"
    CLEANUP = "cleanup"


# =============================================================================
# VERİ YAPILARI
# =============================================================================


@dataclass
class CleanupResult:
    """Cleanup işleminin sonucu."""
    status: CleanupStatus
    phase: CleanupPhase
    timestamp: datetime
    retention_days: int
    cutoff_date: datetime
    indices_found: int
    indices_deleted: int
    backup_size_mb: float
    backup_file: Optional[str]
    error: Optional[str] = None
    retry_count: int = 0
    dry_run: bool = False
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        """Sonucu dict'e dönüştür."""
        return {
            "status": self.status.value,
            "phase": self.phase.value,
            "timestamp": self.timestamp.isoformat(),
            "retention_days": self.retention_days,
            "cutoff_date": self.cutoff_date.isoformat(),
            "indices_found": self.indices_found,
            "indices_deleted": self.indices_deleted,
            "backup_size_mb": self.backup_size_mb,
            "backup_file": self.backup_file,
            "error": self.error,
            "retry_count": self.retry_count,
            "dry_run": self.dry_run,
            "duration_seconds": self.duration_seconds,
        }


# =============================================================================
# LOG CLEANUP MANAGER
# =============================================================================


class LogCleanupManager:
    """
    Log cleanup ve retention yönetimi.
    
    Özellikler:
    - Scheduled cleanup job'ı (günde bir kere)
    - Eski log'ları sil
    - Silme işleminden önce backup'la
    - Silme işlemini log'a yaz
    - Admin'e email ile bildir
    - Dry-run modunda test edebilme
    - Başarısız olursa retry mekanizması
    """
    
    def __init__(self):
        """Cleanup manager'ı başlat."""
        self.logger = get_logger(__name__)
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        self.last_cleanup_result: Optional[CleanupResult] = None
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Cleanup manager'ı başlat."""
        if self.running:
            self.logger.warning("Log cleanup manager zaten çalışıyor")
            return
        
        if not LOG_CLEANUP_ENABLED:
            self.logger.info("Log cleanup disabled")
            return
        
        self.running = True
        self.cleanup_task = asyncio.create_task(self._scheduler_loop())
        self.logger.info(f"Log cleanup manager başlatıldı (cleanup saati: {LOG_CLEANUP_HOUR}:00)")
    
    async def stop(self) -> None:
        """Cleanup manager'ı durdur."""
        if not self.running:
            return
        
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Log cleanup manager durduruldu")
    
    async def _scheduler_loop(self) -> None:
        """
        Scheduler loop'u.
        
        Her gün belirtilen saatte cleanup'ı çalıştırır.
        """
        while self.running:
            try:
                # Sonraki cleanup zamanını hesapla
                now = datetime.now()
                cleanup_time = now.replace(hour=LOG_CLEANUP_HOUR, minute=0, second=0, microsecond=0)
                
                # Eğer cleanup zamanı geçtiyse, yarın aynı saate ayarla
                if cleanup_time <= now:
                    cleanup_time += timedelta(days=1)
                
                # Bekleme süresi
                wait_seconds = (cleanup_time - now).total_seconds()
                
                self.logger.debug(f"Sonraki cleanup: {cleanup_time.isoformat()} ({wait_seconds:.0f} saniye sonra)")
                
                # Cleanup zamanını bekle
                await asyncio.sleep(wait_seconds)
                
                if not self.running:
                    break
                
                # Cleanup'ı çalıştır
                await self.run_cleanup(dry_run=False)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Scheduler loop'unda hata: {e}", exc_info=True)
                # Hata durumunda 1 saat bekle ve tekrar dene
                await asyncio.sleep(3600)
    
    async def run_cleanup(
        self,
        dry_run: bool = False,
        retention_days: Optional[int] = None,
    ) -> CleanupResult:
        """
        Cleanup'ı çalıştır.
        
        Args:
            dry_run: Gerçekten silmeden önce test et
            retention_days: Log saklama süresi (varsayılan: ortam değişkeninden)
            
        Returns:
            CleanupResult: Cleanup işleminin sonucu
        """
        start_time = datetime.utcnow()
        
        if retention_days is None:
            retention_days = LOG_RETENTION_DAYS
        
        # Cutoff tarihini hesapla
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Sonuç nesnesi oluştur
        result = CleanupResult(
            status=CleanupStatus.IN_PROGRESS,
            phase=CleanupPhase.BACKUP,
            timestamp=start_time,
            retention_days=retention_days,
            cutoff_date=cutoff_date,
            indices_found=0,
            indices_deleted=0,
            backup_size_mb=0.0,
            backup_file=None,
            dry_run=dry_run,
        )
        
        try:
            async with self._lock:
                # Elasticsearch istemcisini al
                es_client = get_elasticsearch_client()
                
                # 1. BACKUP AŞAMASI
                self.logger.info(f"Cleanup başlatıldı (dry_run={dry_run}, retention={retention_days} gün)")
                
                backup_result = await self._perform_backup(es_client, cutoff_date, result)
                if not backup_result:
                    result.status = CleanupStatus.FAILED
                    result.phase = CleanupPhase.BACKUP
                    result.error = "Backup başarısız"
                    await self._send_failure_notification(result)
                    return result
                
                # 2. DELETE AŞAMASI
                result.phase = CleanupPhase.DELETE
                
                delete_result = await self._perform_delete(es_client, cutoff_date, result, dry_run)
                if delete_result is None:
                    result.status = CleanupStatus.FAILED
                    result.phase = CleanupPhase.DELETE
                    result.error = "Delete başarısız"
                    await self._send_failure_notification(result)
                    return result
                
                result.indices_deleted = delete_result
                
                # 3. NOTIFICATION AŞAMASI
                result.phase = CleanupPhase.NOTIFICATION
                
                await self._send_success_notification(result)
                
                # 4. CLEANUP AŞAMASI (eski backup dosyalarını sil)
                result.phase = CleanupPhase.CLEANUP
                
                await self._cleanup_old_backups()
                
                # Başarılı
                result.status = CleanupStatus.COMPLETED
                result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
                
                self.logger.info(
                    f"Cleanup tamamlandı: {result.indices_deleted} index silindi, "
                    f"backup: {result.backup_file}, "
                    f"süre: {result.duration_seconds:.2f}s"
                )
                
                # Sonucu kaydet
                self.last_cleanup_result = result
                
                return result
        
        except Exception as e:
            self.logger.error(f"Cleanup işleminde hata: {e}", exc_info=True)
            
            result.status = CleanupStatus.FAILED
            result.error = str(e)
            result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            
            await self._send_failure_notification(result)
            
            return result
    
    async def _perform_backup(
        self,
        es_client,
        cutoff_date: datetime,
        result: CleanupResult,
    ) -> bool:
        """
        Backup'ı gerçekleştir.
        
        Args:
            es_client: Elasticsearch istemcisi
            cutoff_date: Cutoff tarihi
            result: Cleanup sonucu
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        try:
            self.logger.info("Backup aşaması başlatıldı")
            
            # Silinecek index'leri bul
            all_indices = es_client.indices.get(index="logs-*")
            indices_to_backup = []
            
            for index_name in all_indices.keys():
                try:
                    # Index adından tarihi çıkar (logs-2024-01-15 formatı)
                    date_str = index_name.split("-", 1)[1]  # "2024-01-15"
                    index_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if index_date < cutoff_date:
                        indices_to_backup.append(index_name)
                except (ValueError, IndexError):
                    continue
            
            result.indices_found = len(indices_to_backup)
            
            if not indices_to_backup:
                self.logger.info("Silinecek eski index bulunamadı")
                return True
            
            self.logger.info(f"Backup'lanacak index'ler: {indices_to_backup}")
            
            # Backup'ı al
            backup_success = backup_logs(es_client, backup_dir=BACKUP_DIR)
            
            if not backup_success:
                self.logger.error("Backup başarısız")
                return False
            
            # Backup dosyasının boyutunu hesapla
            import os
            from pathlib import Path
            
            backup_path = Path(BACKUP_DIR)
            if backup_path.exists():
                total_size = sum(f.stat().st_size for f in backup_path.glob("**/*") if f.is_file())
                result.backup_size_mb = round(total_size / (1024 * 1024), 2)
                
                # En son backup dosyasını bul
                backup_files = sorted(backup_path.glob("*.json.gz"), key=lambda x: x.stat().st_mtime, reverse=True)
                if backup_files:
                    result.backup_file = str(backup_files[0])
            
            self.logger.info(f"Backup tamamlandı: {result.backup_size_mb} MB")
            return True
        
        except Exception as e:
            self.logger.error(f"Backup aşamasında hata: {e}", exc_info=True)
            return False
    
    async def _perform_delete(
        self,
        es_client,
        cutoff_date: datetime,
        result: CleanupResult,
        dry_run: bool = False,
    ) -> Optional[int]:
        """
        Delete'i gerçekleştir.
        
        Args:
            es_client: Elasticsearch istemcisi
            cutoff_date: Cutoff tarihi
            result: Cleanup sonucu
            dry_run: Gerçekten silmeden önce test et
            
        Returns:
            int: Silinen index sayısı veya None (hata)
        """
        try:
            self.logger.info(f"Delete aşaması başlatıldı (dry_run={dry_run})")
            
            # Delete'i çalıştır
            deleted_count = delete_old_logs(
                es_client,
                retention_days=result.retention_days,
                dry_run=dry_run,
            )
            
            self.logger.info(f"Delete tamamlandı: {deleted_count} index silindi")
            return deleted_count
        
        except Exception as e:
            self.logger.error(f"Delete aşamasında hata: {e}", exc_info=True)
            return None
    
    async def _cleanup_old_backups(self, retention_days: int = 30) -> None:
        """
        Eski backup dosyalarını sil.
        
        Args:
            retention_days: Backup saklama süresi (gün)
        """
        try:
            from pathlib import Path
            import os
            
            backup_path = Path(BACKUP_DIR)
            if not backup_path.exists():
                return
            
            cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
            
            for backup_file in backup_path.glob("*.json.gz"):
                file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_mtime < cutoff_time:
                    try:
                        backup_file.unlink()
                        self.logger.info(f"Eski backup dosyası silindi: {backup_file.name}")
                    except Exception as e:
                        self.logger.error(f"Backup dosyası silinirken hata: {e}")
        
        except Exception as e:
            self.logger.error(f"Eski backup'lar temizlenirken hata: {e}", exc_info=True)
    
    async def _send_success_notification(self, result: CleanupResult) -> None:
        """
        Başarılı cleanup notification'ı gönder.
        
        Args:
            result: Cleanup sonucu
        """
        try:
            # Log'a yaz
            log_event(
                self.logger,
                event_type="cleanup",
                event_name="success",
                data=result.to_dict(),
            )
            
            # Email gönder
            await self._send_email_notification(result, success=True)
            
            # Alert gönder (info seviyesi)
            alert_manager = get_alert_manager()
            await alert_manager.trigger_alert(
                alert_type=AlertType.CUSTOM,
                severity=AlertSeverity.INFO,
                message=f"Log cleanup başarılı: {result.indices_deleted} index silindi",
                data=result.to_dict(),
            )
        
        except Exception as e:
            self.logger.error(f"Success notification gönderilemedi: {e}", exc_info=True)
    
    async def _send_failure_notification(self, result: CleanupResult) -> None:
        """
        Başarısız cleanup notification'ı gönder.
        
        Args:
            result: Cleanup sonucu
        """
        try:
            # Log'a yaz
            log_event(
                self.logger,
                event_type="cleanup",
                event_name="failure",
                data=result.to_dict(),
            )
            
            # Email gönder
            await self._send_email_notification(result, success=False)
            
            # Alert gönder (critical seviyesi)
            alert_manager = get_alert_manager()
            await alert_manager.trigger_alert(
                alert_type=AlertType.CUSTOM,
                severity=AlertSeverity.CRITICAL,
                message=f"Log cleanup başarısız: {result.error}",
                data=result.to_dict(),
            )
        
        except Exception as e:
            self.logger.error(f"Failure notification gönderilemedi: {e}", exc_info=True)
    
    async def _send_email_notification(self, result: CleanupResult, success: bool = True) -> None:
        """
        Email notification'ı gönder.
        
        Args:
            result: Cleanup sonucu
            success: Başarılı olup olmadığı
        """
        try:
            # Environment variables'ı al
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            alert_email_to = os.getenv("ALERT_EMAIL_TO")
            
            # Konfigürasyon kontrol et
            if not all([smtp_server, smtp_username, smtp_password, alert_email_to]):
                self.logger.warning("Email konfigürasyonu eksik, email gönderilemedi")
                return
            
            # Email içeriğini oluştur
            if success:
                subject = f"[SUCCESS] Log Cleanup Tamamlandı"
                body = self._format_success_email(result)
            else:
                subject = f"[FAILURE] Log Cleanup Başarısız"
                body = self._format_failure_email(result)
            
            # Email gönder
            async with aiosmtplib.SMTP(hostname=smtp_server, port=smtp_port) as smtp:
                await smtp.login(smtp_username, smtp_password)
                await smtp.sendmail(
                    sender=smtp_username,
                    recipients=[alert_email_to],
                    message=f"Subject: {subject}\n\n{body}"
                )
            
            self.logger.info(f"Email notification gönderildi: {subject}")
        
        except Exception as e:
            self.logger.error(f"Email notification gönderilemedi: {e}", exc_info=True)
    
    def _format_success_email(self, result: CleanupResult) -> str:
        """Başarılı cleanup email'ini formatla."""
        body = f"""
Log Cleanup Başarılı
====================

Zaman: {result.timestamp.isoformat()}
Durum: {result.status.value}
Süre: {result.duration_seconds:.2f} saniye

Detaylar:
---------
Retention Süresi: {result.retention_days} gün
Cutoff Tarihi: {result.cutoff_date.isoformat()}
Bulunan Index'ler: {result.indices_found}
Silinen Index'ler: {result.indices_deleted}
Backup Boyutu: {result.backup_size_mb} MB
Backup Dosyası: {result.backup_file}
Dry-run: {result.dry_run}

---
Bu email otomatik olarak gönderilmiştir.
"""
        return body
    
    def _format_failure_email(self, result: CleanupResult) -> str:
        """Başarısız cleanup email'ini formatla."""
        body = f"""
Log Cleanup Başarısız
====================

Zaman: {result.timestamp.isoformat()}
Durum: {result.status.value}
Hata: {result.error}
Aşama: {result.phase.value}
Retry Sayısı: {result.retry_count}

Detaylar:
---------
Retention Süresi: {result.retention_days} gün
Cutoff Tarihi: {result.cutoff_date.isoformat()}
Bulunan Index'ler: {result.indices_found}
Silinen Index'ler: {result.indices_deleted}
Backup Boyutu: {result.backup_size_mb} MB
Dry-run: {result.dry_run}

Lütfen sistem yöneticisine başvurunuz.

---
Bu email otomatik olarak gönderilmiştir.
"""
        return body
    
    def get_last_cleanup_result(self) -> Optional[CleanupResult]:
        """
        Son cleanup işleminin sonucunu al.
        
        Returns:
            CleanupResult veya None
        """
        return self.last_cleanup_result


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_cleanup_manager: Optional[LogCleanupManager] = None


def get_cleanup_manager() -> LogCleanupManager:
    """
    Global cleanup manager instance'ını al.
    
    Returns:
        LogCleanupManager: Global instance
    """
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = LogCleanupManager()
    return _cleanup_manager


async def start_cleanup_manager() -> None:
    """Cleanup manager'ı başlat."""
    manager = get_cleanup_manager()
    await manager.start()


async def stop_cleanup_manager() -> None:
    """Cleanup manager'ı durdur."""
    manager = get_cleanup_manager()
    await manager.stop()


async def run_cleanup(
    dry_run: bool = False,
    retention_days: Optional[int] = None,
) -> CleanupResult:
    """
    Cleanup'ı çalıştır.
    
    Args:
        dry_run: Gerçekten silmeden önce test et
        retention_days: Log saklama süresi
        
    Returns:
        CleanupResult: Cleanup işleminin sonucu
    """
    manager = get_cleanup_manager()
    return await manager.run_cleanup(dry_run=dry_run, retention_days=retention_days)


def get_last_cleanup_result() -> Optional[CleanupResult]:
    """
    Son cleanup işleminin sonucunu al.
    
    Returns:
        CleanupResult veya None
    """
    manager = get_cleanup_manager()
    return manager.get_last_cleanup_result()
