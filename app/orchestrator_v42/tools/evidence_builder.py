from typing import List, Dict, Any
from app.orchestrator_v42.tools.types import ToolResult

def build_tool_evidence(results: List[ToolResult]) -> Dict[str, Any]:
    """
    Specialist için standardize edilmiş, güvenli tool kanıtı oluşturur.
    
    Amaç:
    1. Yüksek kardinalite veriyi (query, user_id) filtrelemek.
    2. Aşırı uzun metinleri kırkmak.
    3. Hata/Başarı durumlarını özetlemek.
    
    Args:
        results: Çalıştırılan araçların sonuçları.
        
    Returns:
        Dict: Specialist'e gönderilecek execution context (tool_evidence).
    """
    if not results:
        return {
            "ran": False,
            "ok_count": 0,
            "error_count": 0,
            "items": [],
            "notes": "Araç çalıştırılmadı."
        }
        
    ok_count = sum(1 for r in results if r.ok)
    err_count = sum(1 for r in results if not r.ok)
    
    # Max 3 item (En son 3 sonuç veya önemli olanlar)
    # Şimdilik sırayla ilk 3
    items_limited = results[:3]
    
    evidence_items = []
    
    for res in items_limited:
        item_data = {
            "tool": res.name,
            "ok": res.ok
        }
        
        if res.ok:
            # Başarılı Sonuç
            # Web Search için özel formatlama
            if res.name == "web_search" and isinstance(res.output, dict):
                raw_results = res.output.get("results", [])
                # Max 3 sonuç
                trimmed_results = []
                for sub in raw_results[:3]: # Zaten adapter 5 dönüyor, burada 3'e iniyoruz
                    if not isinstance(sub, dict):
                         continue
                         
                    title = str(sub.get("title", "") or "")
                    url = str(sub.get("url", "") or "")
                    snippet = str(sub.get("snippet", "") or "")
                    
                    # Ekstra güvenlik: 300 char clamp (Adapter yapıyor ama garanti olsun)
                    if len(snippet) > 300: snippet = snippet[:297] + "..."
                    if len(title) > 300: title = title[:297] + "..."
                    if len(url) > 300: url = url[:297] + "..."
                    
                    trimmed_results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
                    
                item_data["results"] = trimmed_results
                item_data["notes"] = res.output.get("notes", "")
                
            else:
                # Diğer araçlar (Generic)
                # Output string ise veya dict ise güvenli hale getir
                raw_out = str(res.output)
                if len(raw_out) > 500:
                    raw_out = raw_out[:497] + "..."
                item_data["output"] = raw_out
                
        else:
            # Hata Durumu
            err_msg = str(res.error or "Bilinmeyen hata")
            if len(err_msg) > 200:
                err_msg = err_msg[:197] + "..."
            item_data["error"] = err_msg
            
        evidence_items.append(item_data)
        
    return {
        "ran": True,
        "ok_count": ok_count,
        "error_count": err_count,
        "items": evidence_items,
        "notes": f"Toplam {len(results)} işlem. {len(evidence_items)} tanesi eklendi."
    }
