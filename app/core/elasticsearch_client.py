"""
Elasticsearch İstemci Modülü
=============================

Bu modül, Elasticsearch'e bağlantı ve log yönetimini sağlar.

Özellikler:
    - Elasticsearch bağlantı yönetimi
    - Günlük dönen index'ler (daily rotation)
    - Log gönderimi ve sorgulaması
    - Log retention policy'si (90 gün)
    - Backup ve disaster recovery
    - Gzip sıkıştırması
    - Batch işleme

Kullanım:
    from app.core.elasticsearch_client import get_elasticsearch_client, send_log, query_logs

    es_client = get_elasticsearch_client()
    send_log(es_client, {"message": "Test log", "level": "INFO"})
    results = query_logs(es_client, "error", days=7)

Ortam Değişkenleri:
    ELASTICSEARCH_URL: Elasticsearch sunucusu URL'si (varsayılan: http://localhost:9200)
    ELASTICSEARCH_USERNAME: Kullanıcı adı (opsiyonel)
    ELASTICSEARCH_PASSWORD: Şifre (opsiyonel)
    LOG_RETENTION_DAYS: Log saklama süresi gün cinsinden (varsayılan: 90)
"""

import asyncio
import gzip
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError

# =============================================================================
# YAPILANDIRMA SABİTLERİ
# =============================================================================

# Elasticsearch bağlantı ayarları
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD")

# Log retention policy
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "90"))

# Index ayarları
INDEX_PREFIX = "logs"
INDEX_PATTERN = f"{INDEX_PREFIX}-*"

# Batch işleme ayarları
BATCH_SIZE = 100
BATCH_TIMEOUT_SECONDS = 5

# Backup ayarları
BACKUP_DIR = Path("data/elasticsearch_backups")

# =============================================================================
# ELASTICSEARCH İSTEMCİ YÖNETİMİ
# =============================================================================

_elasticsearch_client: Optional[Elasticsearch] = None
_logger = logging.getLogger(__name__)


def get_elasticsearch_client() -> Elasticsearch:
    """
    Elasticsearch istemcisini al veya oluştur (singleton pattern).
    
    Returns:
        Elasticsearch: Elasticsearch istemcisi
        
    Raises:
        ConnectionError: Elasticsearch'e bağlanılamadığında
    """
    global _elasticsearch_client
    
    if _elasticsearch_client is None:
        # Bağlantı parametrelerini hazırla (her çağrıda ortam değişkenlerini oku)
        es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        es_username = os.getenv("ELASTICSEARCH_USERNAME")
        es_password = os.getenv("ELASTICSEARCH_PASSWORD")
        
        connection_params = {
            "hosts": [es_url],
            "verify_certs": False,  # Geliştirme için SSL doğrulamasını devre dışı bırak
            "ssl_show_warn": False,
        }
        
        # Kimlik doğrulama (varsa)
        if es_username and es_password:
            connection_params["basic_auth"] = (es_username, es_password)
        
        try:
            _elasticsearch_client = Elasticsearch(**connection_params)
            
            # Bağlantıyı test et
            info = _elasticsearch_client.info()
            _logger.info(f"Elasticsearch'e başarıyla bağlandı: {info['version']['number']}")
            
        except ConnectionError as e:
            _logger.error(f"Elasticsearch'e bağlanılamadı: {e}")
            raise
    
    return _elasticsearch_client


def close_elasticsearch_client() -> None:
    """Elasticsearch istemcisini kapat."""
    global _elasticsearch_client
    
    if _elasticsearch_client is not None:
        try:
            _elasticsearch_client.close()
            _logger.info("Elasticsearch istemcisi kapatıldı")
        except Exception as e:
            _logger.error(f"Elasticsearch istemcisi kapatılırken hata: {e}")
        finally:
            _elasticsearch_client = None


# =============================================================================
# INDEX YÖNETİMİ
# =============================================================================


def get_index_name(date: Optional[datetime] = None) -> str:
    """
    Tarih için index adını al (günlük dönen format).
    
    Args:
        date: Tarih (varsayılan: bugün)
        
    Returns:
        str: Index adı (örn: logs-2024-01-15)
    """
    if date is None:
        date = datetime.utcnow()
    
    return f"{INDEX_PREFIX}-{date.strftime('%Y-%m-%d')}"


def create_index_if_not_exists(es_client: Elasticsearch, index_name: str) -> None:
    """
    Index'i oluştur (varsa yoksay).
    
    Args:
        es_client: Elasticsearch istemcisi
        index_name: Index adı
    """
    try:
        if not es_client.indices.exists(index=index_name):
            # Index ayarları
            settings = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index.lifecycle.name": "logs-policy",
                    "index.lifecycle.rollover_alias": "logs-alias",
                },
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "level": {"type": "keyword"},
                        "module": {"type": "keyword"},
                        "message": {"type": "text"},
                        "request_id": {"type": "keyword"},
                        "context": {"type": "object", "enabled": True},
                        "exception": {"type": "object", "enabled": True},
                        "@timestamp": {"type": "date"},
                    }
                },
            }
            
            es_client.indices.create(index=index_name, body=settings)
            _logger.info(f"Index oluşturuldu: {index_name}")
    
    except Exception as e:
        _logger.error(f"Index oluşturulurken hata: {e}")


# =============================================================================
# LOG GÖNDERIMI
# =============================================================================


def send_log(
    es_client: Elasticsearch,
    log_data: Dict[str, Any],
    index_name: Optional[str] = None,
) -> bool:
    """
    Tek bir log mesajını Elasticsearch'e gönder.
    
    Args:
        es_client: Elasticsearch istemcisi
        log_data: Log verisi (dict)
        index_name: Index adı (varsayılan: bugünün index'i)
        
    Returns:
        bool: Başarılı olup olmadığı
    """
    try:
        if index_name is None:
            index_name = get_index_name()
        
        # Index'i oluştur (varsa yoksay)
        create_index_if_not_exists(es_client, index_name)
        
        # @timestamp ekle (Elasticsearch tarafından kullanılır)
        if "@timestamp" not in log_data:
            log_data["@timestamp"] = datetime.utcnow().isoformat()
        
        # Log'u gönder
        result = es_client.index(index=index_name, body=log_data)
        
        return result.get("result") in ["created", "updated"]
    
    except Exception as e:
        _logger.error(f"Log gönderilirken hata: {e}")
        return False


def send_logs_batch(
    es_client: Elasticsearch,
    logs: List[Dict[str, Any]],
    index_name: Optional[str] = None,
) -> int:
    """
    Birden fazla log mesajını batch halinde Elasticsearch'e gönder.
    
    Args:
        es_client: Elasticsearch istemcisi
        logs: Log verisi listesi
        index_name: Index adı (varsayılan: bugünün index'i)
        
    Returns:
        int: Başarıyla gönderilen log sayısı
    """
    if not logs:
        return 0
    
    try:
        if index_name is None:
            index_name = get_index_name()
        
        # Index'i oluştur (varsa yoksay)
        create_index_if_not_exists(es_client, index_name)
        
        # Bulk işlemi için veri hazırla
        bulk_data = []
        for log_data in logs:
            # @timestamp ekle
            if "@timestamp" not in log_data:
                log_data["@timestamp"] = datetime.utcnow().isoformat()
            
            # Bulk işlemi için metadata ve data ekle
            bulk_data.append({"index": {"_index": index_name}})
            bulk_data.append(log_data)
        
        # Bulk işlemini yap
        result = es_client.bulk(body=bulk_data)
        
        # Başarıyla gönderilen sayıyı hesapla
        success_count = sum(1 for item in result.get("items", []) if item.get("index", {}).get("result") in ["created", "updated"])
        
        return success_count
    
    except Exception as e:
        _logger.error(f"Batch log gönderilirken hata: {e}")
        return 0


# =============================================================================
# LOG SORGUSU
# =============================================================================


def query_logs(
    es_client: Elasticsearch,
    query_string: Optional[str] = None,
    level: Optional[str] = None,
    module: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Log'ları sorgula.
    
    Args:
        es_client: Elasticsearch istemcisi
        query_string: Arama metni (full-text search)
        level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        module: Modül adı
        days: Son kaç gün (varsayılan: 7)
        limit: Sonuç limiti (varsayılan: 100)
        
    Returns:
        List[Dict]: Sorgu sonuçları
    """
    try:
        # Zaman aralığını hesapla
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query oluştur
        query_body = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": start_date.isoformat(),
                                    "lte": datetime.utcnow().isoformat(),
                                }
                            }
                        }
                    ],
                }
            },
            "size": limit,
            "sort": [{"timestamp": {"order": "desc"}}],
        }
        
        # Arama metni ekle
        if query_string:
            query_body["query"]["bool"]["must"].append(
                {"multi_match": {"query": query_string, "fields": ["message", "module"]}}
            )
        
        # Log seviyesi filtresi ekle
        if level:
            query_body["query"]["bool"]["filter"].append({"term": {"level": level}})
        
        # Modül filtresi ekle
        if module:
            query_body["query"]["bool"]["filter"].append({"term": {"module": module}})
        
        # Sorguyu yap
        result = es_client.search(index=INDEX_PATTERN, body=query_body)
        
        # Sonuçları döndür
        return [hit["_source"] for hit in result.get("hits", {}).get("hits", [])]
    
    except Exception as e:
        _logger.error(f"Log sorgulanırken hata: {e}")
        return []


def get_error_logs(
    es_client: Elasticsearch,
    days: int = 7,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Hata log'larını al.
    
    Args:
        es_client: Elasticsearch istemcisi
        days: Son kaç gün
        limit: Sonuç limiti
        
    Returns:
        List[Dict]: Hata log'ları
    """
    return query_logs(es_client, level="ERROR", days=days, limit=limit)


def get_logs_by_request_id(
    es_client: Elasticsearch,
    request_id: str,
) -> List[Dict[str, Any]]:
    """
    Request ID'ye göre log'ları al.
    
    Args:
        es_client: Elasticsearch istemcisi
        request_id: Request ID (correlation ID)
        
    Returns:
        List[Dict]: Log'lar
    """
    try:
        query_body = {
            "query": {"term": {"request_id": request_id}},
            "size": 1000,
            "sort": [{"timestamp": {"order": "asc"}}],
        }
        
        result = es_client.search(index=INDEX_PATTERN, body=query_body)
        return [hit["_source"] for hit in result.get("hits", {}).get("hits", [])]
    
    except Exception as e:
        _logger.error(f"Request ID'ye göre log sorgulanırken hata: {e}")
        return []


# =============================================================================
# LOG RETENTION & CLEANUP
# =============================================================================


def delete_old_logs(
    es_client: Elasticsearch,
    retention_days: int = LOG_RETENTION_DAYS,
    dry_run: bool = False,
) -> int:
    """
    Eski log'ları sil.
    
    Args:
        es_client: Elasticsearch istemcisi
        retention_days: Saklama süresi (gün)
        dry_run: Gerçekten silmeden önce test et
        
    Returns:
        int: Silinen log sayısı
    """
    try:
        # Silme tarihi hesapla
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Silinecek index'leri bul
        indices_to_delete = []
        all_indices = es_client.indices.get(index=INDEX_PATTERN)
        
        for index_name in all_indices.keys():
            # Index adından tarihi çıkar (logs-2024-01-15 formatı)
            try:
                date_str = index_name.split("-", 1)[1]  # "2024-01-15"
                index_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if index_date < cutoff_date:
                    indices_to_delete.append(index_name)
            except (ValueError, IndexError):
                continue
        
        if not indices_to_delete:
            _logger.info("Silinecek eski index bulunamadı")
            return 0
        
        # Dry-run modunda sadece log yaz
        if dry_run:
            _logger.info(f"[DRY-RUN] Silinecek index'ler: {indices_to_delete}")
            return len(indices_to_delete)
        
        # Index'leri sil
        deleted_count = 0
        for index_name in indices_to_delete:
            try:
                es_client.indices.delete(index=index_name)
                _logger.info(f"Index silindi: {index_name}")
                deleted_count += 1
            except Exception as e:
                _logger.error(f"Index silinirken hata ({index_name}): {e}")
        
        return deleted_count
    
    except Exception as e:
        _logger.error(f"Eski log'lar silinirken hata: {e}")
        return 0


# =============================================================================
# BACKUP & DISASTER RECOVERY
# =============================================================================


def backup_logs(
    es_client: Elasticsearch,
    index_name: Optional[str] = None,
    backup_dir: Path = BACKUP_DIR,
) -> bool:
    """
    Log'ları backup'la.
    
    Args:
        es_client: Elasticsearch istemcisi
        index_name: Index adı (varsayılan: tüm index'ler)
        backup_dir: Backup dizini
        
    Returns:
        bool: Başarılı olup olmadığı
    """
    try:
        # Backup dizinini oluştur
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup'lanacak index'leri belirle
        if index_name:
            indices = [index_name]
        else:
            all_indices = es_client.indices.get(index=INDEX_PATTERN)
            indices = list(all_indices.keys())
        
        # Her index'i backup'la
        for idx in indices:
            try:
                # Index verilerini al
                result = es_client.search(index=idx, size=10000, body={"query": {"match_all": {}}})
                
                # Backup dosyasını oluştur
                backup_file = backup_dir / f"{idx}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json.gz"
                
                # Verileri gzip ile sıkıştırarak yaz
                with gzip.open(backup_file, "wt", encoding="utf-8") as f:
                    for hit in result.get("hits", {}).get("hits", []):
                        json.dump(hit["_source"], f)
                        f.write("\n")
                
                _logger.info(f"Index backup'landı: {idx} -> {backup_file}")
            
            except Exception as e:
                _logger.error(f"Index backup'lanırken hata ({idx}): {e}")
                return False
        
        return True
    
    except Exception as e:
        _logger.error(f"Backup işleminde hata: {e}")
        return False


def restore_logs(
    es_client: Elasticsearch,
    backup_file: Path,
    index_name: Optional[str] = None,
) -> int:
    """
    Backup'tan log'ları geri yükle.
    
    Args:
        es_client: Elasticsearch istemcisi
        backup_file: Backup dosyası
        index_name: Hedef index adı (varsayılan: backup dosyasından çıkar)
        
    Returns:
        int: Geri yüklenen log sayısı
    """
    try:
        # Index adını belirle
        if index_name is None:
            # Dosya adından index adını çıkar
            index_name = backup_file.stem.split("_")[0]
        
        # Index'i oluştur
        create_index_if_not_exists(es_client, index_name)
        
        # Backup dosyasını oku ve geri yükle
        restored_count = 0
        with gzip.open(backup_file, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        log_data = json.loads(line)
                        if send_log(es_client, log_data, index_name):
                            restored_count += 1
                    except json.JSONDecodeError:
                        continue
        
        _logger.info(f"Backup geri yüklendi: {backup_file} -> {index_name} ({restored_count} log)")
        return restored_count
    
    except Exception as e:
        _logger.error(f"Backup geri yüklenirken hata: {e}")
        return 0


# =============================================================================
# SAĞLIK KONTROLÜ
# =============================================================================


def health_check(es_client: Elasticsearch) -> Dict[str, Any]:
    """
    Elasticsearch sağlığını kontrol et.
    
    Returns:
        Dict: Sağlık bilgisi
    """
    try:
        health = es_client.cluster.health()
        
        return {
            "status": "healthy" if health.get("status") == "green" else "degraded",
            "cluster_status": health.get("status"),
            "active_shards": health.get("active_shards"),
            "active_primary_shards": health.get("active_primary_shards"),
            "relocating_shards": health.get("relocating_shards"),
            "initializing_shards": health.get("initializing_shards"),
            "unassigned_shards": health.get("unassigned_shards"),
            "number_of_nodes": health.get("number_of_nodes"),
            "number_of_data_nodes": health.get("number_of_data_nodes"),
        }
    
    except Exception as e:
        _logger.error(f"Elasticsearch sağlık kontrolü başarısız: {e}")
        return {"status": "unhealthy", "error": str(e)}


def get_index_stats(es_client: Elasticsearch, index_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Index istatistiklerini al.
    
    Args:
        es_client: Elasticsearch istemcisi
        index_name: Index adı (varsayılan: tüm index'ler)
        
    Returns:
        Dict: Index istatistikleri
    """
    try:
        if index_name is None:
            index_name = INDEX_PATTERN
        
        stats = es_client.indices.stats(index=index_name)
        
        total_docs = 0
        total_size = 0
        
        for index_data in stats.get("indices", {}).values():
            total_docs += index_data.get("primaries", {}).get("docs", {}).get("count", 0)
            total_size += index_data.get("primaries", {}).get("store", {}).get("size_in_bytes", 0)
        
        return {
            "total_docs": total_docs,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
    
    except Exception as e:
        _logger.error(f"Index istatistikleri alınırken hata: {e}")
        return {"error": str(e)}
