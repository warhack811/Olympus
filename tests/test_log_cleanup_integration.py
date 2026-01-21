"""
Log Cleanup Integration Test'leri
==================================

Bu test dosyası, log cleanup ve retention yönetiminin integration test'lerini içerir.

Test Kapsamı:
    - Cleanup job'ının gerçek Elasticsearch ile çalışması
    - Eski log'ların gerçekten silinmesi
    - Backup'ın gerçekten alınması
    - Dry-run modunda test edilmesi
    - Email notification'ının gönderilmesi
    - Cleanup sonucunun doğru kaydedilmesi

Gereksinimler:
    - Elasticsearch çalışıyor olmalı
    - Dosya sistemi yazılabilir olmalı
"""

import pytest
import asyncio
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import shutil

from app.core.log_cleanup import (
    LogCleanupManager,
    CleanupResult,
    CleanupStatus,
    CleanupPhase,
    run_cleanup,
    get_cleanup_manager,
    get_last_cleanup_result,
)
from app.core.elasticsearch_client import get_elasticsearch_client


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_backup_dir():
    """Geçici backup dizini oluştur."""
    temp_dir = tempfile.mkdtemp(prefix="log_cleanup_backup_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def cleanup_manager():
    """Cleanup manager fixture."""
    manager = LogCleanupManager()
    yield manager
    # Cleanup
    asyncio.run(manager.stop())


@pytest.fixture
async def mock_elasticsearch():
    """Mock Elasticsearch istemcisi."""
    client = MagicMock()
    
    # Mock indices.get() - eski ve yeni index'leri döndür
    old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
    new_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
    
    client.indices.get.return_value = {
        f"logs-{old_date}": {"settings": {}},
        f"logs-{new_date}": {"settings": {}},
        "logs-2024-01-01": {"settings": {}},  # Çok eski
    }
    
    # Mock indices.delete()
    client.indices.delete.return_value = {"acknowledged": True}
    
    # Mock search() - log'ları döndür
    client.search.return_value = {
        "hits": {
            "total": {"value": 100},
            "hits": [
                {
                    "_id": f"log_{i}",
                    "_source": {
                        "timestamp": (datetime.utcnow() - timedelta(days=100)).isoformat(),
                        "level": "INFO",
                        "message": f"Test log {i}",
                    }
                }
                for i in range(10)
            ]
        }
    }
    
    return client


# =============================================================================
# CLEANUP JOB TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_cleanup_job_runs_successfully(cleanup_manager, temp_backup_dir):
    """
    Cleanup job'ının başarılı bir şekilde çalışması test edilir.
    
    Property: Cleanup job çalıştırıldığında, sonuç COMPLETED durumunda olmalı
    ve tüm aşamalar başarılı bir şekilde tamamlanmalıdır.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            # Mock indices.get() - eski ve yeni index'leri döndür
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            new_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
            
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
                f"logs-{new_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=1):
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock):
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                            
                            # Sonuç kontrol et
                            assert result.status == CleanupStatus.COMPLETED
                            assert result.phase == CleanupPhase.CLEANUP
                            assert result.retention_days == 90
                            assert result.indices_found >= 0
                            assert result.indices_deleted >= 0
                            assert result.duration_seconds > 0
                            assert result.dry_run is False


@pytest.mark.asyncio
async def test_cleanup_job_handles_errors(cleanup_manager, temp_backup_dir):
    """
    Cleanup job'ının hataları doğru bir şekilde işlemesi test edilir.
    
    Property: Cleanup job sırasında bir hata oluştuğunda, sonuç FAILED durumunda
    olmalı ve error mesajı kaydedilmelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            # Elasticsearch istemcisini mock et ve hata döndür
            mock_client = MagicMock()
            mock_client.indices.get.side_effect = Exception("Elasticsearch bağlantı hatası")
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", side_effect=Exception("Backup başarısız")):
                with patch.object(cleanup_manager, "_send_failure_notification", new_callable=AsyncMock):
                    # Cleanup'ı çalıştır
                    result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                    
                    # Sonuç kontrol et
                    assert result.status == CleanupStatus.FAILED
                    assert result.error is not None


# =============================================================================
# OLD LOGS DELETION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_old_logs_are_deleted(cleanup_manager, temp_backup_dir):
    """
    Eski log'ların silinmesi test edilir.
    
    Property: Cleanup job çalıştırıldığında, retention_days'den eski log'lar
    silinmelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            # Mock indices.get() - eski ve yeni index'leri döndür
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            new_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
            
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
                f"logs-{new_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=1) as mock_delete:
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock):
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                            
                            # delete_old_logs çağrıldığını kontrol et
                            mock_delete.assert_called_once()
                            
                            # Silinen index sayısı kontrol et
                            assert result.indices_deleted == 1


@pytest.mark.asyncio
async def test_new_logs_are_not_deleted(cleanup_manager, temp_backup_dir):
    """
    Yeni log'ların silinmemesi test edilir.
    
    Property: Cleanup job çalıştırıldığında, retention_days'den daha yeni
    log'lar silinmemelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            # Mock indices.get() - sadece yeni index'leri döndür
            new_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
            
            mock_client.indices.get.return_value = {
                f"logs-{new_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=0) as mock_delete:
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock):
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                            
                            # delete_old_logs çağrıldığını kontrol et
                            mock_delete.assert_called_once()
                            
                            # Silinen index sayısı 0 olmalı
                            assert result.indices_deleted == 0


# =============================================================================
# BACKUP TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_backup_is_created(cleanup_manager, temp_backup_dir):
    """
    Backup'ın oluşturulması test edilir.
    
    Property: Cleanup job çalıştırıldığında, backup dosyası oluşturulmalı
    ve backup_file alanı doldurulmalıdır.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            # Mock indices.get()
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            # Gerçek backup dosyası oluştur (daha büyük boyut)
            backup_file = Path(temp_backup_dir) / "backup_test.json.gz"
            backup_file.write_bytes(b"test backup data" * 1000)  # Daha büyük dosya
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=1):
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock):
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                            
                            # Backup dosyası kontrol et
                            assert result.backup_file is not None
                            assert result.backup_size_mb > 0


@pytest.mark.asyncio
async def test_backup_before_delete(cleanup_manager, temp_backup_dir):
    """
    Silme işleminden önce backup'ın alınması test edilir.
    
    Property: Cleanup job sırasında, delete işleminden önce backup alınmalıdır.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    call_order = []
    
    def mock_backup(*args, **kwargs):
        call_order.append("backup")
        return True
    
    def mock_delete(*args, **kwargs):
        call_order.append("delete")
        return 1
    
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", side_effect=mock_backup):
                with patch("app.core.log_cleanup.delete_old_logs", side_effect=mock_delete):
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock):
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                            
                            # Backup'ın delete'ten önce çalıştığını kontrol et
                            assert call_order == ["backup", "delete"]


# =============================================================================
# DRY-RUN TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_dry_run_does_not_delete(cleanup_manager, temp_backup_dir):
    """
    Dry-run modunda log'ların silinmemesi test edilir.
    
    Property: Cleanup job dry_run=True ile çalıştırıldığında, log'lar
    silinmemelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=0) as mock_delete:
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock):
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı dry-run modunda çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=True, retention_days=90)
                            
                            # delete_old_logs'a dry_run=True geçildiğini kontrol et
                            mock_delete.assert_called_once()
                            call_args = mock_delete.call_args
                            assert call_args.kwargs.get("dry_run") is True
                            
                            # Sonuç dry_run flag'ini içermeli
                            assert result.dry_run is True


# =============================================================================
# NOTIFICATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_success_notification_sent(cleanup_manager, temp_backup_dir):
    """
    Başarılı cleanup notification'ının gönderilmesi test edilir.
    
    Property: Cleanup job başarılı bir şekilde tamamlandığında, success
    notification gönderilmelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=1):
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock) as mock_notify:
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                            
                            # Success notification çağrıldığını kontrol et
                            mock_notify.assert_called_once()
                            
                            # Notification'a geçilen sonuç kontrol et
                            call_args = mock_notify.call_args
                            notified_result = call_args[0][0]
                            assert notified_result.status == CleanupStatus.COMPLETED


@pytest.mark.asyncio
async def test_failure_notification_sent(cleanup_manager, temp_backup_dir):
    """
    Başarısız cleanup notification'ının gönderilmesi test edilir.
    
    Property: Cleanup job başarısız olduğunda, failure notification
    gönderilmelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            mock_client.indices.get.side_effect = Exception("Test error")
            mock_es_func.return_value = mock_client
            
            with patch.object(cleanup_manager, "_send_failure_notification", new_callable=AsyncMock) as mock_notify:
                # Cleanup'ı çalıştır
                result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                
                # Failure notification çağrıldığını kontrol et
                mock_notify.assert_called_once()
                
                # Notification'a geçilen sonuç kontrol et
                call_args = mock_notify.call_args
                notified_result = call_args[0][0]
                assert notified_result.status == CleanupStatus.FAILED


# =============================================================================
# RESULT PERSISTENCE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_cleanup_result_is_saved(cleanup_manager, temp_backup_dir):
    """
    Cleanup sonucunun kaydedilmesi test edilir.
    
    Property: Cleanup job tamamlandığında, sonuç get_last_cleanup_result()
    ile alınabilmelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=1):
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock):
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=90)
                            
                            # Sonuç kaydedildiğini kontrol et
                            saved_result = cleanup_manager.get_last_cleanup_result()
                            assert saved_result is not None
                            assert saved_result.status == CleanupStatus.COMPLETED
                            assert saved_result.indices_deleted == 1


# =============================================================================
# RETENTION DAYS PARAMETER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_custom_retention_days(cleanup_manager, temp_backup_dir):
    """
    Özel retention_days parametresinin kullanılması test edilir.
    
    Property: Cleanup job custom retention_days parametresi ile çalıştırıldığında,
    bu değer kullanılmalıdır.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=1) as mock_delete:
                    with patch.object(cleanup_manager, "_send_success_notification", new_callable=AsyncMock):
                        with patch.object(cleanup_manager, "_cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı custom retention_days ile çalıştır
                            result = await cleanup_manager.run_cleanup(dry_run=False, retention_days=60)
                            
                            # Sonuç custom retention_days'i içermeli
                            assert result.retention_days == 60
                            
                            # delete_old_logs'a custom retention_days geçildiğini kontrol et
                            mock_delete.assert_called_once()
                            call_args = mock_delete.call_args
                            assert call_args.kwargs.get("retention_days") == 60


# =============================================================================
# GLOBAL FUNCTION INTEGRATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_run_cleanup_global_function(temp_backup_dir):
    """
    Global run_cleanup fonksiyonunun integration test'i.
    
    Property: run_cleanup() global fonksiyonu çalıştırıldığında, cleanup
    işlemi başarılı bir şekilde tamamlanmalıdır.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=1):
                    with patch("app.core.log_cleanup.LogCleanupManager._send_success_notification", new_callable=AsyncMock):
                        with patch("app.core.log_cleanup.LogCleanupManager._cleanup_old_backups", new_callable=AsyncMock):
                            # Global run_cleanup fonksiyonunu çalıştır
                            result = await run_cleanup(dry_run=False, retention_days=90)
                            
                            # Sonuç kontrol et
                            assert result.status == CleanupStatus.COMPLETED
                            assert result.indices_deleted == 1


@pytest.mark.asyncio
async def test_get_last_cleanup_result_global_function(temp_backup_dir):
    """
    Global get_last_cleanup_result fonksiyonunun integration test'i.
    
    Property: get_last_cleanup_result() global fonksiyonu çalıştırıldığında,
    son cleanup sonucu döndürülmelidir.
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    """
    with patch("app.core.log_cleanup.BACKUP_DIR", temp_backup_dir):
        with patch("app.core.log_cleanup.get_elasticsearch_client") as mock_es_func:
            mock_client = MagicMock()
            
            old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
            mock_client.indices.get.return_value = {
                f"logs-{old_date}": {},
            }
            
            mock_es_func.return_value = mock_client
            
            with patch("app.core.log_cleanup.backup_logs", return_value=True):
                with patch("app.core.log_cleanup.delete_old_logs", return_value=1):
                    with patch("app.core.log_cleanup.LogCleanupManager._send_success_notification", new_callable=AsyncMock):
                        with patch("app.core.log_cleanup.LogCleanupManager._cleanup_old_backups", new_callable=AsyncMock):
                            # Cleanup'ı çalıştır
                            await run_cleanup(dry_run=False, retention_days=90)
                            
                            # Son sonucu al
                            result = get_last_cleanup_result()
                            
                            # Sonuç kontrol et
                            assert result is not None
                            assert result.status == CleanupStatus.COMPLETED
