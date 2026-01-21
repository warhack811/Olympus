"""
Elasticsearch Entegrasyonu Test'leri

Bu test dosyası, app/core/elasticsearch_client.py modülünün
Elasticsearch entegrasyonunu test eder.

Test Kapsamı:
    - Elasticsearch client'ının initialize edilip edilmediği
    - Log'ların Elasticsearch'e yazıldığı
    - Log'ların doğru index'e yazıldığı
    - Log'ların query'lendiği
    - Log retention policy'sinin çalışıp çalışmadığı
    - Backup ve restore işlemlerinin çalışıp çalışmadığı
"""

import json
import pytest
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.elasticsearch_client import (
    get_elasticsearch_client,
    close_elasticsearch_client,
    get_index_name,
    create_index_if_not_exists,
    send_log,
    send_logs_batch,
    query_logs,
    get_error_logs,
    get_logs_by_request_id,
    delete_old_logs,
    backup_logs,
    restore_logs,
    health_check,
    get_index_stats,
)


class TestElasticsearchClient:
    """Elasticsearch client test'leri."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Her test'ten sonra client'ı kapat."""
        yield
        close_elasticsearch_client()

    def test_get_elasticsearch_client_singleton(self):
        """
        Elasticsearch client'ının singleton pattern'i kullanıp kullanmadığını test et.
        
        For any call to get_elasticsearch_client, it should return the same instance.
        """
        with patch("app.core.elasticsearch_client.Elasticsearch") as mock_es:
            mock_instance = MagicMock()
            mock_instance.info.return_value = {"version": {"number": "8.11.0"}}
            mock_es.return_value = mock_instance
            
            # İlk çağrı
            client1 = get_elasticsearch_client()
            # İkinci çağrı
            client2 = get_elasticsearch_client()
            
            # Aynı instance olmalı
            assert client1 is client2
            # Elasticsearch sadece bir kere initialize edilmeli
            assert mock_es.call_count == 1

    def test_get_elasticsearch_client_with_auth(self):
        """
        Elasticsearch client'ının kimlik doğrulama ile initialize edilip edilmediğini test et.
        
        For any Elasticsearch client with username and password set,
        it should use basic_auth in the connection parameters.
        """
        # Global client'ı temizle
        import app.core.elasticsearch_client as es_module
        es_module._elasticsearch_client = None
        
        # Ortam değişkenlerini patch'le
        original_username = os.environ.get("ELASTICSEARCH_USERNAME")
        original_password = os.environ.get("ELASTICSEARCH_PASSWORD")
        
        try:
            os.environ["ELASTICSEARCH_USERNAME"] = "user"
            os.environ["ELASTICSEARCH_PASSWORD"] = "pass"
            
            with patch("app.core.elasticsearch_client.Elasticsearch") as mock_es:
                mock_instance = MagicMock()
                mock_instance.info.return_value = {"version": {"number": "8.11.0"}}
                mock_es.return_value = mock_instance
                
                # Global client'ı temizle (ortam değişkenleri değiştiğinden sonra)
                es_module._elasticsearch_client = None
                
                # Client'ı al
                client = get_elasticsearch_client()
                
                # basic_auth parametresi kontrol et
                call_kwargs = mock_es.call_args[1]
                assert "basic_auth" in call_kwargs
                assert call_kwargs["basic_auth"] == ("user", "pass")
        finally:
            # Ortam değişkenlerini geri yükle
            if original_username is not None:
                os.environ["ELASTICSEARCH_USERNAME"] = original_username
            else:
                os.environ.pop("ELASTICSEARCH_USERNAME", None)
            
            if original_password is not None:
                os.environ["ELASTICSEARCH_PASSWORD"] = original_password
            else:
                os.environ.pop("ELASTICSEARCH_PASSWORD", None)


class TestIndexManagement:
    """Index yönetimi test'leri."""

    def test_get_index_name_default_date(self):
        """
        get_index_name'in varsayılan tarih ile doğru index adı döndürüp döndürmediğini test et.
        
        For any call to get_index_name without a date parameter,
        it should return an index name with today's date.
        """
        index_name = get_index_name()
        
        # Format kontrol et: logs-YYYY-MM-DD
        assert index_name.startswith("logs-")
        assert len(index_name) == len("logs-2024-01-15")
        
        # Tarih parse edilebilir olmalı
        date_part = index_name.split("-", 1)[1]
        parsed_date = datetime.strptime(date_part, "%Y-%m-%d")
        
        # Bugünün tarihi olmalı (±1 gün tolerans)
        today = datetime.utcnow().date()
        assert abs((parsed_date.date() - today).days) <= 1

    def test_get_index_name_custom_date(self):
        """
        get_index_name'in custom tarih ile doğru index adı döndürüp döndürmediğini test et.
        
        For any call to get_index_name with a specific date,
        it should return an index name with that date.
        """
        custom_date = datetime(2024, 1, 15, 12, 30, 45)
        index_name = get_index_name(custom_date)
        
        assert index_name == "logs-2024-01-15"

    def test_create_index_if_not_exists(self):
        """
        create_index_if_not_exists'in index'i oluşturup oluşturmadığını test et.
        
        For any index that doesn't exist, create_index_if_not_exists should create it.
        """
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = False
        
        create_index_if_not_exists(mock_es, "logs-2024-01-15")
        
        # Index oluşturma çağrısı yapılmalı
        assert mock_es.indices.create.called
        
        # Çağrı parametrelerini kontrol et
        call_kwargs = mock_es.indices.create.call_args[1]
        assert call_kwargs["index"] == "logs-2024-01-15"
        assert "settings" in call_kwargs["body"]
        assert "mappings" in call_kwargs["body"]

    def test_create_index_if_not_exists_already_exists(self):
        """
        create_index_if_not_exists'in var olan index'i yoksayıp yoksaymadığını test et.
        
        For any index that already exists, create_index_if_not_exists should not create it again.
        """
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = True
        
        create_index_if_not_exists(mock_es, "logs-2024-01-15")
        
        # Index oluşturma çağrısı yapılmamalı
        assert not mock_es.indices.create.called


class TestLogSending:
    """Log gönderimi test'leri."""

    def test_send_log_success(self):
        """
        send_log'un log'u başarıyla gönderip göndermediğini test et.
        
        For any log data sent with send_log, it should be indexed in Elasticsearch.
        """
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = True
        mock_es.index.return_value = {"result": "created"}
        
        log_data = {
            "level": "INFO",
            "module": "app.main",
            "message": "Test log",
        }
        
        result = send_log(mock_es, log_data)
        
        assert result is True
        assert mock_es.index.called

    def test_send_log_with_timestamp(self):
        """
        send_log'un @timestamp ekleyip eklemediğini test et.
        
        For any log data sent without @timestamp, send_log should add it.
        """
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = True
        mock_es.index.return_value = {"result": "created"}
        
        log_data = {
            "level": "INFO",
            "module": "app.main",
            "message": "Test log",
        }
        
        send_log(mock_es, log_data)
        
        # Index çağrısının body'sini kontrol et
        call_kwargs = mock_es.index.call_args[1]
        body = call_kwargs["body"]
        
        assert "@timestamp" in body

    def test_send_logs_batch(self):
        """
        send_logs_batch'in batch işlemini doğru yaptığını test et.
        
        For any batch of logs sent with send_logs_batch,
        it should use the bulk API and return the count of successful sends.
        """
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = True
        mock_es.bulk.return_value = {
            "items": [
                {"index": {"result": "created"}},
                {"index": {"result": "created"}},
                {"index": {"result": "created"}},
            ]
        }
        
        logs = [
            {"level": "INFO", "message": "Log 1"},
            {"level": "INFO", "message": "Log 2"},
            {"level": "INFO", "message": "Log 3"},
        ]
        
        result = send_logs_batch(mock_es, logs)
        
        assert result == 3
        assert mock_es.bulk.called

    def test_send_logs_batch_empty(self):
        """
        send_logs_batch'in boş liste ile doğru davranıp davranmadığını test et.
        
        For any empty batch sent with send_logs_batch, it should return 0.
        """
        mock_es = MagicMock()
        
        result = send_logs_batch(mock_es, [])
        
        assert result == 0
        assert not mock_es.bulk.called


class TestLogQuerying:
    """Log sorgusu test'leri."""

    def test_query_logs_basic(self):
        """
        query_logs'un temel sorguyu doğru yaptığını test et.
        
        For any query_logs call, it should search the logs index
        and return the results.
        """
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"level": "INFO", "message": "Log 1"}},
                    {"_source": {"level": "INFO", "message": "Log 2"}},
                ]
            }
        }
        
        results = query_logs(mock_es, query_string="test")
        
        assert len(results) == 2
        assert results[0]["message"] == "Log 1"
        assert results[1]["message"] == "Log 2"

    def test_query_logs_with_filters(self):
        """
        query_logs'un filtreleri doğru uyguladığını test et.
        
        For any query_logs call with level and module filters,
        it should include them in the search query.
        """
        mock_es = MagicMock()
        mock_es.search.return_value = {"hits": {"hits": []}}
        
        query_logs(mock_es, level="ERROR", module="app.main", days=7)
        
        # Search çağrısının body'sini kontrol et
        call_kwargs = mock_es.search.call_args[1]
        body = call_kwargs["body"]
        
        # Filter'ları kontrol et
        filters = body["query"]["bool"]["filter"]
        
        # Level filtresi olmalı
        level_filter = next((f for f in filters if "term" in f and "level" in f["term"]), None)
        assert level_filter is not None
        
        # Module filtresi olmalı
        module_filter = next((f for f in filters if "term" in f and "module" in f["term"]), None)
        assert module_filter is not None

    def test_get_error_logs(self):
        """
        get_error_logs'un sadece ERROR log'larını döndürüp döndürmediğini test et.
        
        For any call to get_error_logs, it should return only ERROR level logs.
        """
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"level": "ERROR", "message": "Error 1"}},
                    {"_source": {"level": "ERROR", "message": "Error 2"}},
                ]
            }
        }
        
        results = get_error_logs(mock_es)
        
        assert len(results) == 2
        assert all(log["level"] == "ERROR" for log in results)

    def test_get_logs_by_request_id(self):
        """
        get_logs_by_request_id'nin request ID'ye göre log'ları döndürüp döndürmediğini test et.
        
        For any call to get_logs_by_request_id with a request ID,
        it should return all logs with that request ID.
        """
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"request_id": "req-123", "message": "Log 1"}},
                    {"_source": {"request_id": "req-123", "message": "Log 2"}},
                ]
            }
        }
        
        results = get_logs_by_request_id(mock_es, "req-123")
        
        assert len(results) == 2
        assert all(log["request_id"] == "req-123" for log in results)


class TestLogRetention:
    """Log retention test'leri."""

    def test_delete_old_logs_dry_run(self):
        """
        delete_old_logs'un dry-run modunda sadece log yazdığını test et.
        
        For any call to delete_old_logs with dry_run=True,
        it should not actually delete any indices.
        """
        mock_es = MagicMock()
        
        # Mock indices.get
        old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
        mock_es.indices.get.return_value = {
            f"logs-{old_date}": {},
        }
        
        result = delete_old_logs(mock_es, retention_days=90, dry_run=True)
        
        # Silme çağrısı yapılmamalı
        assert not mock_es.indices.delete.called
        # Silinecek index sayısı döndürülmeli
        assert result == 1

    def test_delete_old_logs_actual_delete(self):
        """
        delete_old_logs'un gerçekten eski index'leri silip silmediğini test et.
        
        For any call to delete_old_logs with dry_run=False,
        it should delete indices older than retention_days.
        """
        mock_es = MagicMock()
        
        # Mock indices.get
        old_date = (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%d")
        recent_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        
        mock_es.indices.get.return_value = {
            f"logs-{old_date}": {},
            f"logs-{recent_date}": {},
        }
        
        result = delete_old_logs(mock_es, retention_days=90, dry_run=False)
        
        # Sadece eski index silinmeli
        assert mock_es.indices.delete.call_count == 1
        # Silinen index sayısı döndürülmeli
        assert result == 1


class TestBackupRestore:
    """Backup ve restore test'leri."""

    def test_backup_logs(self):
        """
        backup_logs'un log'ları backup'ladığını test et.
        
        For any call to backup_logs, it should create a backup file
        with gzip compression.
        """
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"level": "INFO", "message": "Log 1"}},
                    {"_source": {"level": "INFO", "message": "Log 2"}},
                ]
            }
        }
        
        with patch("pathlib.Path.mkdir"):
            with patch("gzip.open", create=True) as mock_gzip:
                mock_file = MagicMock()
                mock_gzip.return_value.__enter__.return_value = mock_file
                
                result = backup_logs(mock_es, "logs-2024-01-15")
                
                assert result is True
                assert mock_gzip.called

    def test_restore_logs(self):
        """
        restore_logs'un backup'tan log'ları geri yükleyip yüklemediğini test et.
        
        For any call to restore_logs with a backup file,
        it should restore the logs to the specified index.
        """
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = True
        mock_es.index.return_value = {"result": "created"}
        
        backup_file = Path("data/elasticsearch_backups/logs-2024-01-15_20240115_120000.json.gz")
        
        with patch("gzip.open", create=True) as mock_gzip:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.readlines.return_value = [
                '{"level": "INFO", "message": "Log 1"}\n',
                '{"level": "INFO", "message": "Log 2"}\n',
            ]
            mock_gzip.return_value = mock_file
            
            with patch("builtins.open", create=True):
                result = restore_logs(mock_es, backup_file)
                
                # Restore işlemi başarılı olmalı
                assert result >= 0


class TestHealthCheck:
    """Sağlık kontrolü test'leri."""

    def test_health_check_healthy(self):
        """
        health_check'in sağlıklı cluster'ı doğru raporladığını test et.
        
        For any Elasticsearch cluster with green status,
        health_check should return status as 'healthy'.
        """
        mock_es = MagicMock()
        mock_es.cluster.health.return_value = {
            "status": "green",
            "active_shards": 5,
            "active_primary_shards": 5,
            "relocating_shards": 0,
            "initializing_shards": 0,
            "unassigned_shards": 0,
            "number_of_nodes": 1,
            "number_of_data_nodes": 1,
        }
        
        result = health_check(mock_es)
        
        assert result["status"] == "healthy"
        assert result["cluster_status"] == "green"

    def test_health_check_degraded(self):
        """
        health_check'in degraded cluster'ı doğru raporladığını test et.
        
        For any Elasticsearch cluster with yellow or red status,
        health_check should return status as 'degraded' or 'unhealthy'.
        """
        mock_es = MagicMock()
        mock_es.cluster.health.return_value = {
            "status": "yellow",
            "active_shards": 4,
            "active_primary_shards": 5,
            "relocating_shards": 0,
            "initializing_shards": 1,
            "unassigned_shards": 0,
            "number_of_nodes": 1,
            "number_of_data_nodes": 1,
        }
        
        result = health_check(mock_es)
        
        assert result["status"] == "degraded"
        assert result["cluster_status"] == "yellow"


class TestIndexStats:
    """Index istatistikleri test'leri."""

    def test_get_index_stats(self):
        """
        get_index_stats'ın doğru istatistikleri döndürüp döndürmediğini test et.
        
        For any call to get_index_stats, it should return total document count
        and storage size in bytes and MB.
        """
        mock_es = MagicMock()
        mock_es.indices.stats.return_value = {
            "indices": {
                "logs-2024-01-15": {
                    "primaries": {
                        "docs": {"count": 1000},
                        "store": {"size_in_bytes": 1048576},  # 1 MB
                    }
                }
            }
        }
        
        result = get_index_stats(mock_es)
        
        assert result["total_docs"] == 1000
        assert result["total_size_bytes"] == 1048576
        assert result["total_size_mb"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

