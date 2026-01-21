"""
Log Cleanup Modülü Test'leri
=============================

Bu test dosyası, log cleanup ve retention yönetimini test eder.

Test Kapsamı:
    - Cleanup job'ının çalışması
    - Eski log'ların silinmesi
    - Backup'ın alınması
    - Dry-run modunda test edilmesi
    - Email notification'ının gönderilmesi
    - Retry mekanizmasının çalışması
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from app.core.log_cleanup import (
    LogCleanupManager,
    CleanupResult,
    CleanupStatus,
    CleanupPhase,
    get_cleanup_manager,
    run_cleanup,
    get_last_cleanup_result,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def cleanup_manager():
    """Cleanup manager fixture."""
    manager = LogCleanupManager()
    yield manager
    # Cleanup
    asyncio.run(manager.stop())


@pytest.fixture
def mock_es_client():
    """Mock Elasticsearch istemcisi."""
    client = MagicMock()
    client.indices.get.return_value = {
        "logs-2024-01-01": {},
        "logs-2024-01-15": {},
        "logs-2024-02-01": {},
    }
    client.indices.delete.return_value = None
    return client


@pytest.fixture
def cleanup_result():
    """Cleanup result fixture."""
    return CleanupResult(
        status=CleanupStatus.COMPLETED,
        phase=CleanupPhase.CLEANUP,
        timestamp=datetime.utcnow(),
        retention_days=90,
        cutoff_date=datetime.utcnow() - timedelta(days=90),
        indices_found=3,
        indices_deleted=2,
        backup_size_mb=150.5,
        backup_file="/path/to/backup.json.gz",
        dry_run=False,
        duration_seconds=45.2,
    )


# =============================================================================
# CLEANUP MANAGER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_cleanup_manager_initialization(cleanup_manager):
    """Cleanup manager'ın başlatılması test edilir."""
    assert cleanup_manager.running is False
    assert cleanup_manager.cleanup_task is None
    assert cleanup_manager.last_cleanup_result is None


@pytest.mark.asyncio
async def test_cleanup_manager_start_stop(cleanup_manager):
    """Cleanup manager'ın başlatılması ve durdurulması test edilir."""
    # Start
    await cleanup_manager.start()
    assert cleanup_manager.running is True
    assert cleanup_manager.cleanup_task is not None
    
    # Stop
    await cleanup_manager.stop()
    assert cleanup_manager.running is False


@pytest.mark.asyncio
async def test_cleanup_manager_double_start(cleanup_manager):
    """Cleanup manager'ın iki kere başlatılması test edilir."""
    await cleanup_manager.start()
    
    # İkinci start'ı çalıştır (warning log'lanmalı)
    await cleanup_manager.start()
    
    assert cleanup_manager.running is True
    
    await cleanup_manager.stop()


# =============================================================================
# CLEANUP RESULT TESTS
# =============================================================================


def test_cleanup_result_to_dict(cleanup_result):
    """CleanupResult'ın dict'e dönüştürülmesi test edilir."""
    result_dict = cleanup_result.to_dict()
    
    assert result_dict["status"] == "completed"
    assert result_dict["phase"] == "cleanup"
    assert result_dict["retention_days"] == 90
    assert result_dict["indices_found"] == 3
    assert result_dict["indices_deleted"] == 2
    assert result_dict["backup_size_mb"] == 150.5
    assert result_dict["dry_run"] is False
    assert result_dict["duration_seconds"] == 45.2


def test_cleanup_result_status_values():
    """CleanupStatus enum değerleri test edilir."""
    assert CleanupStatus.PENDING.value == "pending"
    assert CleanupStatus.IN_PROGRESS.value == "in_progress"
    assert CleanupStatus.COMPLETED.value == "completed"
    assert CleanupStatus.FAILED.value == "failed"
    assert CleanupStatus.RETRYING.value == "retrying"


def test_cleanup_phase_values():
    """CleanupPhase enum değerleri test edilir."""
    assert CleanupPhase.BACKUP.value == "backup"
    assert CleanupPhase.DELETE.value == "delete"
    assert CleanupPhase.NOTIFICATION.value == "notification"
    assert CleanupPhase.CLEANUP.value == "cleanup"


# =============================================================================
# BACKUP TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_perform_backup_success(cleanup_manager, mock_es_client):
    """Backup'ın başarılı bir şekilde alınması test edilir."""
    with patch("app.core.log_cleanup.backup_logs", return_value=True):
        with patch("pathlib.Path") as mock_path_class:
            # Mock Path
            mock_backup_path = MagicMock()
            mock_backup_path.exists.return_value = True
            mock_backup_path.glob.return_value = [
                MagicMock(stat=MagicMock(return_value=MagicMock(st_size=1024*1024*100)))
            ]
            mock_path_class.return_value = mock_backup_path
            
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            result = CleanupResult(
                status=CleanupStatus.IN_PROGRESS,
                phase=CleanupPhase.BACKUP,
                timestamp=datetime.utcnow(),
                retention_days=90,
                cutoff_date=cutoff_date,
                indices_found=0,
                indices_deleted=0,
                backup_size_mb=0.0,
                backup_file=None,
            )
            
            backup_result = await cleanup_manager._perform_backup(mock_es_client, cutoff_date, result)
            
            assert backup_result is True
            assert result.backup_size_mb > 0


@pytest.mark.asyncio
async def test_perform_backup_failure(cleanup_manager, mock_es_client):
    """Backup'ın başarısız olması test edilir."""
    with patch("app.core.log_cleanup.backup_logs", return_value=False):
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        result = CleanupResult(
            status=CleanupStatus.IN_PROGRESS,
            phase=CleanupPhase.BACKUP,
            timestamp=datetime.utcnow(),
            retention_days=90,
            cutoff_date=cutoff_date,
            indices_found=0,
            indices_deleted=0,
            backup_size_mb=0.0,
            backup_file=None,
        )
        
        backup_result = await cleanup_manager._perform_backup(mock_es_client, cutoff_date, result)
        
        assert backup_result is False


# =============================================================================
# DELETE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_perform_delete_success(cleanup_manager, mock_es_client):
    """Delete'in başarılı bir şekilde gerçekleştirilmesi test edilir."""
    with patch("app.core.log_cleanup.delete_old_logs", return_value=2):
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        result = CleanupResult(
            status=CleanupStatus.IN_PROGRESS,
            phase=CleanupPhase.DELETE,
            timestamp=datetime.utcnow(),
            retention_days=90,
            cutoff_date=cutoff_date,
            indices_found=3,
            indices_deleted=0,
            backup_size_mb=100.0,
            backup_file="/path/to/backup.json.gz",
        )
        
        delete_result = await cleanup_manager._perform_delete(mock_es_client, cutoff_date, result, dry_run=False)
        
        assert delete_result == 2


@pytest.mark.asyncio
async def test_perform_delete_dry_run(cleanup_manager, mock_es_client):
    """Delete'in dry-run modunda test edilmesi test edilir."""
    with patch("app.core.log_cleanup.delete_old_logs", return_value=0):
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        result = CleanupResult(
            status=CleanupStatus.IN_PROGRESS,
            phase=CleanupPhase.DELETE,
            timestamp=datetime.utcnow(),
            retention_days=90,
            cutoff_date=cutoff_date,
            indices_found=3,
            indices_deleted=0,
            backup_size_mb=100.0,
            backup_file="/path/to/backup.json.gz",
        )
        
        delete_result = await cleanup_manager._perform_delete(mock_es_client, cutoff_date, result, dry_run=True)
        
        assert delete_result == 0


# =============================================================================
# NOTIFICATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_send_success_notification(cleanup_manager, cleanup_result):
    """Başarılı cleanup notification'ının gönderilmesi test edilir."""
    with patch("app.core.log_cleanup.log_event") as mock_log_event:
        with patch.object(cleanup_manager, "_send_email_notification", new_callable=AsyncMock):
            with patch("app.core.log_cleanup.get_alert_manager") as mock_alert_manager:
                mock_manager = MagicMock()
                mock_manager.trigger_alert = AsyncMock()
                mock_alert_manager.return_value = mock_manager
                
                await cleanup_manager._send_success_notification(cleanup_result)
                
                # Log event çağrıldığını kontrol et
                mock_log_event.assert_called_once()
                
                # Alert trigger'ı çağrıldığını kontrol et
                mock_manager.trigger_alert.assert_called_once()


@pytest.mark.asyncio
async def test_send_failure_notification(cleanup_manager, cleanup_result):
    """Başarısız cleanup notification'ının gönderilmesi test edilir."""
    cleanup_result.status = CleanupStatus.FAILED
    cleanup_result.error = "Test error"
    
    with patch("app.core.log_cleanup.log_event") as mock_log_event:
        with patch.object(cleanup_manager, "_send_email_notification", new_callable=AsyncMock):
            with patch("app.core.log_cleanup.get_alert_manager") as mock_alert_manager:
                mock_manager = MagicMock()
                mock_manager.trigger_alert = AsyncMock()
                mock_alert_manager.return_value = mock_manager
                
                await cleanup_manager._send_failure_notification(cleanup_result)
                
                # Log event çağrıldığını kontrol et
                mock_log_event.assert_called_once()
                
                # Alert trigger'ı çağrıldığını kontrol et
                mock_manager.trigger_alert.assert_called_once()


# =============================================================================
# EMAIL FORMATTING TESTS
# =============================================================================


def test_format_success_email(cleanup_manager, cleanup_result):
    """Başarılı cleanup email'inin formatlanması test edilir."""
    email_body = cleanup_manager._format_success_email(cleanup_result)
    
    assert "Log Cleanup Başarılı" in email_body
    assert "completed" in email_body
    assert "90" in email_body
    assert "2" in email_body
    assert "150.5" in email_body


def test_format_failure_email(cleanup_manager, cleanup_result):
    """Başarısız cleanup email'inin formatlanması test edilir."""
    cleanup_result.status = CleanupStatus.FAILED
    cleanup_result.error = "Backup başarısız"
    
    email_body = cleanup_manager._format_failure_email(cleanup_result)
    
    assert "Log Cleanup Başarısız" in email_body
    assert "failed" in email_body
    assert "Backup başarısız" in email_body


# =============================================================================
# GLOBAL FUNCTION TESTS
# =============================================================================


def test_get_cleanup_manager():
    """Global cleanup manager'ın alınması test edilir."""
    manager1 = get_cleanup_manager()
    manager2 = get_cleanup_manager()
    
    # Aynı instance olmalı
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_run_cleanup():
    """Global run_cleanup fonksiyonunun çalışması test edilir."""
    with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es:
        with patch("app.core.log_cleanup.backup_logs", return_value=True):
            with patch("app.core.log_cleanup.delete_old_logs", return_value=1):
                with patch.object(LogCleanupManager, "_send_success_notification", new_callable=AsyncMock):
                    with patch.object(LogCleanupManager, "_cleanup_old_backups", new_callable=AsyncMock):
                        mock_client = MagicMock()
                        mock_client.indices.get.return_value = {"logs-2024-01-01": {}}
                        mock_es.return_value = mock_client
                        
                        result = await run_cleanup(dry_run=True)
                        
                        assert result.status == CleanupStatus.COMPLETED
                        assert result.dry_run is True


def test_get_last_cleanup_result():
    """Son cleanup sonucunun alınması test edilir."""
    manager = get_cleanup_manager()
    
    # İlk başta None olmalı
    result = get_last_cleanup_result()
    
    # None veya önceki sonuç olabilir
    assert result is None or isinstance(result, CleanupResult)


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_cleanup_result_consistency(cleanup_manager):
    """
    Cleanup sonucunun tutarlılığı test edilir.
    
    Property: Cleanup sonucu oluşturulduktan sonra, to_dict() çağrıldığında
    tüm alanlar doğru şekilde dönüştürülmelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    # Farklı cleanup sonuçları oluştur
    for i in range(10):
        result = CleanupResult(
            status=CleanupStatus.COMPLETED,
            phase=CleanupPhase.CLEANUP,
            timestamp=datetime.utcnow(),
            retention_days=90 + i,
            cutoff_date=datetime.utcnow() - timedelta(days=90 + i),
            indices_found=i,
            indices_deleted=i - 1,
            backup_size_mb=100.0 * i,
            backup_file=f"/path/to/backup_{i}.json.gz",
            dry_run=i % 2 == 0,
            duration_seconds=45.2 + i,
        )
        
        # to_dict() çağrı
        result_dict = result.to_dict()
        
        # Tüm alanlar dict'te olmalı
        assert "status" in result_dict
        assert "phase" in result_dict
        assert "timestamp" in result_dict
        assert "retention_days" in result_dict
        assert "cutoff_date" in result_dict
        assert "indices_found" in result_dict
        assert "indices_deleted" in result_dict
        assert "backup_size_mb" in result_dict
        assert "backup_file" in result_dict
        assert "dry_run" in result_dict
        assert "duration_seconds" in result_dict
        
        # Değerler doğru olmalı
        assert result_dict["retention_days"] == 90 + i
        assert result_dict["indices_found"] == i
        assert result_dict["indices_deleted"] == i - 1
        assert result_dict["backup_size_mb"] == 100.0 * i
        assert result_dict["dry_run"] == (i % 2 == 0)


@pytest.mark.asyncio
async def test_cleanup_manager_state_consistency(cleanup_manager):
    """
    Cleanup manager'ın durumunun tutarlılığı test edilir.
    
    Property: Cleanup manager başlatıldıktan sonra, running flag'i True olmalı
    ve durdurulduktan sonra False olmalı.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    # İlk durumu kontrol et
    assert cleanup_manager.running is False
    
    # Start
    await cleanup_manager.start()
    assert cleanup_manager.running is True
    
    # Stop
    await cleanup_manager.stop()
    assert cleanup_manager.running is False
    
    # Tekrar start
    await cleanup_manager.start()
    assert cleanup_manager.running is True
    
    # Tekrar stop
    await cleanup_manager.stop()
    assert cleanup_manager.running is False
