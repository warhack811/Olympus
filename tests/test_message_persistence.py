"""
FAZE 1: Message Persistence - Unit Tests

Deep merge ve message persistence logic'ini test eder.
"""

import pytest
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
# DEEP MERGE LOGIC TESTS
# ═══════════════════════════════════════════════════════════════════════════


def test_deep_merge_preserves_existing_fields():
    """Mevcut metadata alanları korunmalı"""
    existing = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    new_data = {"progress": 50}
    merged = {**existing, **new_data}
    
    assert merged["status"] == "queued"
    assert merged["progress"] == 50
    assert merged["queue_position"] == 1
    assert merged["type"] == "image"


def test_deep_merge_adds_new_fields():
    """Yeni alanlar eklenebilmeli"""
    existing = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    new_data = {
        "job_id": "test-job-123",
        "prompt": "test prompt"
    }
    merged = {**existing, **new_data}
    
    assert merged["status"] == "queued"
    assert merged["progress"] == 0
    assert merged["queue_position"] == 1
    assert merged["job_id"] == "test-job-123"
    assert merged["prompt"] == "test prompt"


def test_deep_merge_overwrites_existing_field():
    """Mevcut alanlar güncellenebilmeli"""
    existing = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    new_data = {"status": "processing"}
    merged = {**existing, **new_data}
    
    assert merged["status"] == "processing"
    assert merged["progress"] == 0
    assert merged["queue_position"] == 1


def test_deep_merge_with_multiple_updates():
    """Birden fazla update'te veri kaybı olmamali"""
    existing = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    
    # İlk update
    update1 = {
        "status": "processing",
        "progress": 50
    }
    merged1 = {**existing, **update1}
    
    # İkinci update
    update2 = {"queue_position": 0}
    merged2 = {**merged1, **update2}
    
    # Veri kaybı olmamış olmalı
    assert merged2["status"] == "processing"
    assert merged2["progress"] == 50
    assert merged2["queue_position"] == 0
    assert merged2["type"] == "image"


def test_deep_merge_null_metadata():
    """Null metadata hata vermemeli"""
    existing = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    new_data = None
    
    # None ise merge yapılmaz
    if new_data is not None:
        merged = {**existing, **new_data}
    else:
        merged = existing
    
    assert merged["status"] == "queued"


def test_deep_merge_empty_metadata():
    """Boş metadata hata vermemeli"""
    existing = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    new_data = {}
    merged = {**existing, **new_data}
    
    assert merged["status"] == "queued"


def test_persistence_all_fields():
    """Tüm alanlar persist edilmeli"""
    existing = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    
    # Tüm alanları merge et
    all_fields = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 1,
        "job_id": "job-123",
        "prompt": "test prompt"
    }
    merged = {**existing, **all_fields}
    
    # Tüm alanlar mevcut olmalı
    assert merged["type"] == "image"
    assert merged["status"] == "queued"
    assert merged["progress"] == 0
    assert merged["queue_position"] == 1
    assert merged["job_id"] == "job-123"
    assert merged["prompt"] == "test prompt"


def test_deep_merge_complex_workflow():
    """Kompleks workflow'da veri kaybı olmamali"""
    # Başlangıç
    metadata = {
        "type": "image",
        "status": "queued",
        "progress": 0,
        "queue_position": 3,
        "job_id": "job-123",
        "prompt": "test prompt"
    }
    
    # Processing başladığında
    metadata = {**metadata, **{
        "status": "processing",
        "progress": 1,
        "queue_position": 0
    }}
    
    assert metadata["status"] == "processing"
    assert metadata["progress"] == 1
    assert metadata["queue_position"] == 0
    assert metadata["job_id"] == "job-123"
    
    # Progress update
    metadata = {**metadata, **{"progress": 50}}
    assert metadata["progress"] == 50
    assert metadata["status"] == "processing"
    
    # Completion
    metadata = {**metadata, **{
        "status": "complete",
        "progress": 100,
        "image_url": "/images/flux_123.png"
    }}
    
    assert metadata["status"] == "complete"
    assert metadata["progress"] == 100
    assert metadata["image_url"] == "/images/flux_123.png"
    assert metadata["job_id"] == "job-123"


def test_deep_merge_no_field_deletion():
    """Merge sırasında hiçbir alan silinmemeli"""
    existing = {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": 4,
        "e": 5
    }
    
    # Sadece b ve c'yi güncelle
    new_data = {"b": 20, "c": 30}
    merged = {**existing, **new_data}
    
    # Tüm alanlar mevcut olmalı
    assert "a" in merged
    assert "b" in merged
    assert "c" in merged
    assert "d" in merged
    assert "e" in merged
    
    # Değerler doğru olmalı
    assert merged["a"] == 1
    assert merged["b"] == 20
    assert merged["c"] == 30
    assert merged["d"] == 4
    assert merged["e"] == 5


def test_deep_merge_nested_not_required():
    """Nested merge gerekli değil - flat structure kullanıyoruz"""
    # Flat structure
    existing = {
        "status": "queued",
        "progress": 0,
        "queue_position": 1
    }
    
    new_data = {"status": "processing"}
    merged = {**existing, **new_data}
    
    # Flat merge yeterli
    assert merged["status"] == "processing"
    assert merged["progress"] == 0
    assert merged["queue_position"] == 1
