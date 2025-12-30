# app/orchestrator_v42/plugins/rag_adapter.py

import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger("orchestrator.rag_adapter")

from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags

def fetch_context(query: str, user_id: str | None, extra: Dict[str, Any] | None = None, flags: OrchestratorFeatureFlags | None = None) -> Dict[str, Any]:
    """
    RAG Adaptörü (RAG Adapter).
    
    Orchestrator ile Legacy RAG v2 servisi arasındaki köprüdür.
    
    Özellikler:
    - Dry-Run Modu: Gerçek RAG çağrısı yapmadan sahte veri döner (Test için).
    - Fail-Safe: Gerçek çağrı başarısız olursa çökmez, dry-run çıktısına düşer.
    - Contract: Çıktı formatı her zaman deterministiktir.
    
    Args:
        query: Aranacak metin.
        user_id: Kullanıcı ID (owner).
        extra: Opsiyonel parametreler (scope vb).
        flags: Özellik bayrakları (Opsiyonel).
        
    Returns:
        RagAdapterReport (dict)
    """
    
    # 1. ORTAM KONTROLÜ
    # Varsayılan olarak DRY-RUN=TRUE (Güvenlik için)
    # Eğer flags verilmişse oradan oku, yoksa ENV'den, o da yoksa True.
    if flags:
        is_dry_run = flags.rag_dry_run
    else:
        is_dry_run = os.environ.get("ORCH_RAG_DRY_RUN", "true").lower() == "true"
    
    ran = False
    doc_count = 0
    docs = []
    notes = "Başlatıldı."
    
    try:
        if not is_dry_run:
            # --- GERÇEK RAG ÇAĞRISI (LEGACY) ---
            try:
                # Gecikmeli Import (Sadece ihtiyaç anında)
                # KANIT (Aşama 12.1): app.memory.rag_service modülündeki rag_service instance'ı
                from app.memory.rag_service import rag_service
                
                owner = user_id if user_id else "unknown_user"
                scope = (extra or {}).get("scope", "user")
                
                # Gerçek Fonksiyon Çağrısı
                # rag_service.search(query: str, owner: str, scope: Literal, limit: int) -> list[dict]
                real_results = rag_service.search(query=query, owner=owner, scope=scope, limit=3)
                
                # Dönüşüm (Mapping)
                for r in real_results:
                    docs.append({
                        "id": str(r.get("id", "unknown")),
                        "text": str(r.get("text", "")),
                        "source": "v2_hybrid",
                        "score": float(r.get("score", 0.0))
                    })
                
                ran = True
                doc_count = len(docs)
                notes = f"Gerçek RAG v2 çağrısı yapıldı. {doc_count} doküman bulundu."
                
            except ImportError:
                # Modül yoksa (Test ortamı vb)
                logger.warning("app.memory.rag_service import edilemedi. Fallback yapılıyor.")
                is_dry_run = True # Fallback to dry run logic
                notes = "RAG servisi bulunamadı (ImportError). Dry-run yedeğine geçildi."
            except Exception as call_err:
                # Çalışma hatası
                logger.error(f"RAG Service runtime hatası: {call_err}")
                is_dry_run = True # Fallback to dry run logic
                notes = f"RAG çağrısı hata aldı: {call_err}. Dry-run yedeğine geçildi."

        # 2. DRY-RUN VEYA FALLBACK MANTIĞI
        if is_dry_run:
            # Deterministik Mock Veri
            ran = True
            docs = [
                {
                    "id": "mock_doc_1", 
                    "text": f"BU BIR TEST DOKUMANIDIR (1). Konu: {query[:20]}...", 
                    "source": "dry_run", 
                    "score": 0.95
                },
                {
                    "id": "mock_doc_2", 
                    "text": "BU BIR TEST DOKUMANIDIR (2). RAG sistemi dry-run modunda çalışıyor.", 
                    "source": "dry_run", 
                    "score": 0.88
                }
            ]
            doc_count = 2
            # Eğer notlar başlangıç notuysa (örn "Başlatıldı."), dry-run notunu yaz.
            # Yoksa (Fallbak/Error notu varsa) aynen koru.
            if notes == "Başlatıldı.":
                notes = "Dry-run modu aktif. Sahte veri dönüldü."

        # 3. ÇIKTI OLUŞTURMA
        return {
            "ran": ran,
            "dry_run": is_dry_run,
            "doc_count": doc_count,
            "docs": docs,
            "notes": notes
        }

    except Exception as e:
        logger.error(f"RAG Adapter critical error: {e}")
        return {
            "ran": False,
            "dry_run": is_dry_run,
            "doc_count": 0,
            "docs": [],
            "notes": f"Kritik Adaptör Hatası: {e}"
        }
