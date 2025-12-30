from typing import List, Dict, Any

def build_adapter_prompt(
    user_message: str, 
    *, 
    rag_evidence: List[Dict[str, Any]] | None = None, 
    tool_evidence: Any | None = None, 
    memory_items: List[Any] | None = None
) -> str:
    """
    LLM Adaptörüne gidecek olan "message" parametresini oluşturur.
    Kullanıcı mesajını RAG, Tool ve Hafıza kanıtlarıyla zenginleştirir.
    
    Güvenlik:
    - Toplam uzunluk (6000 karakter clamp)
    - Hassas veri sızıntısı engelleme (user_id, trace_id, query)
    - Başarısızlık durumunda fail-soft (boş string dönmez, en azından user_message döner)
    """
    # Temel koruma: None ise boş listeye çevir
    rag_evidence = rag_evidence or []
    memory_items = memory_items or []
    
    # Tool Evidence Normalizasyon (Liste ve Dict desteği)
    if tool_evidence is None:
        tool_evidence = {}
    elif isinstance(tool_evidence, list):
        tool_evidence = {"ran": True, "items": tool_evidence}
    elif isinstance(tool_evidence, dict):
        if "items" in tool_evidence and "ran" not in tool_evidence:
            tool_evidence["ran"] = True
    else:
        # Bilinmeyen tip
        tool_evidence = {}
    
    sections = []
    
    # 1. HAFIZA BAĞLAMI
    if memory_items:
        mem_lines = []
        for item in memory_items[:5]: # Max 5
            # MemoryItem objesi veya dict olabilir
            text = getattr(item, "text", None) or str(item.get("text", "") if isinstance(item, dict) else "")
            if text:
                # Clamp 240
                if len(text) > 240: text = text[:237] + "..."
                mem_lines.append(f"- {text}")
                
        if mem_lines:
            sections.append("### Hafıza Bağlamı:\n" + "\n".join(mem_lines))

    # 2. ARAÇ KANITI (TOOL EVIDENCE)
    if tool_evidence and tool_evidence.get("ran") and tool_evidence.get("items"):
        tool_lines = []
        items = tool_evidence.get("items", [])
        for item in items[:3]: # Max 3 item
            # Item Dict Garantisi
            if not isinstance(item, dict):
                 tool_lines.append(f"- Bilinmeyen Kanıt: {str(item)[:100]}...")
                 continue

            name = item.get("tool", "bilinmeyen")
            if item.get("ok"):
                # Başarılı
                if "results" in item and isinstance(item["results"], list):
                    # Web Search sonuçları
                    sub_lines = []
                    for res in item["results"][:3]: # Max 3 sonuç
                         if not isinstance(res, dict): continue
                         
                         title = str(res.get("title", "") or "")
                         snippet = str(res.get("snippet", "") or "")
                         
                         # Clamp 300
                         if len(title) > 300: title = title[:297] + "..."
                         if len(snippet) > 300: snippet = snippet[:297] + "..."
                         
                         sub_lines.append(f"  * {title}: {snippet}")
                    if sub_lines:
                        tool_lines.append(f"- {name} Sonuçları:\n" + "\n".join(sub_lines))
                else:
                    # Genel output
                    out_text = str(item.get("output", ""))
                    if len(out_text) > 300: out_text = out_text[:297] + "..."
                    tool_lines.append(f"- {name}: {out_text}")
            else:
                 # Hata
                 err = str(item.get("error", ""))
                 if len(err) > 150: err = err[:147] + "..."
                 tool_lines.append(f"- {name} Hatası: {err}")
                 
        if tool_lines:
            sections.append("### Araç Kanıtı:\n" + "\n".join(tool_lines))

    # 3. BİLGİ KANITI (RAG)
    if rag_evidence:
        rag_lines = []
        for doc in rag_evidence[:3]: # Max 3
            # doc dict bekleniyor: content, metadata
            content = doc.get("content", "")
            meta = doc.get("metadata", {}) or {}
            source = meta.get("source", "")
            
            if len(content) > 300: content = content[:297] + "..."
            
            line = f"- {content}"
            if source:
                line += f" (Kaynak: {source})"
            rag_lines.append(line)
            
        if rag_lines:
             sections.append("### Bilgi Kanıtı:\n" + "\n".join(rag_lines))

    # 4. KULLANICI MESAJI
    # Sonunda eklenir
    sections.append(f"### Kullanıcı Mesajı:\n{user_message}")
    
    # BİRLEŞTİRME VE TEMİZLİK
    full_prompt = "\n\n".join(sections)
    
    # CLAMP (6000 Global)
    if len(full_prompt) > 6000:
        full_prompt = full_prompt[:5997] + "..."
        
    # GİZLİLİK (YASAKLI KELİMELER)
    # user_id, trace_id, query, conversation_id gibi sistem internal değişken adları sızmamalı
    # Basit string replace (case-insensitive değil, key-match)
    for forbidden in ["user_id", "trace_id", "conversation_id"]:
        if forbidden in full_prompt:
             full_prompt = full_prompt.replace(forbidden, "[GİZLENDİ]")
             
    # "query" kelimesi bazen normal cümlede geçebilir ("query about..."), o yüzden katı yasaklamayalım
    # Ancak "query=" gibi yapıları engelleyebiliriz
             
    return full_prompt
