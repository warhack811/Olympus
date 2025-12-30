from typing import List
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
from app.orchestrator_v42.tools.types import ToolPlan, ToolCall

def compile_tool_plan(
    message: str,
    required_capabilities: List[str],
    flags: OrchestratorFeatureFlags
) -> ToolPlan:
    """
    Kullanıcı mesajına ve yeteneklere göre deterministik bir araç planı oluşturur.
    Bu fazda sadece 'web_search' destekleniyor.
    """
    calls = []
    
    # Eğer max çağrı sayısı 0 ise hiç plan yapma
    if flags.tools_max_calls <= 0:
        return ToolPlan(calls=[])
        
    # Şimdilik sadece "arama" veya "search" capability varsa web_search ekle
    # Veya mesaj içinde belirgin bir sinyal varsa (ileride intent'ten gelecek)
    
    normalized_caps = [c.lower() for c in required_capabilities]
    needs_search = any(c in ["search", "arama", "web", "internet"] for c in normalized_caps)
    
    if needs_search:
        # Tek bir arama çağrısı oluştur
        calls.append(ToolCall(
            id="tool_1",
            name="web_search",
            arguments={"query": message}
        ))
        
    # Limit (flags.tools_max_calls) kadarını al (zaten şu an en fazla 1 üretiyoruz ama genel kural)
    calls = calls[:flags.tools_max_calls]
    
    return ToolPlan(calls=calls)

def compile_tool_plan_from_tasks(
    tasks: List[dict],
    flags: OrchestratorFeatureFlags
) -> ToolPlan:
    """
    Task Graph'tan gelen görevleri araç planına çevirir (Multi-Tool).
    Max 2 araç çağrısı ile sınırlıdır (MVP).
    """
    if flags.tools_max_calls <= 0 or not tasks:
        return ToolPlan(calls=[])

    calls = []
    # Hard clamp: Max 2 (Flags ne derse desin MVP için güvenli sınır)
    max_mvp_calls = min(2, flags.tools_max_calls)
    
    notes = []

    for i, task in enumerate(tasks):
        if len(calls) >= max_mvp_calls:
            notes.append(f"MVP limiti ({max_mvp_calls}) nedeniyle {len(tasks) - i} görev atlandı.")
            break

        t_type = str(task.get("type", "")).lower()
        
        # Query bulma mantığını güçlendir (meta.desc desteği)
        t_query = task.get("query") or task.get("description") or task.get("meta", {}).get("desc") or ""
        t_query = str(t_query)
        
        # Argument Clamp (200 char)
        if len(t_query) > 200:
            t_query = t_query[:197] + "..."

        if t_type in ["research", "search", "web", "internet", "web_search", "tool_use"]:
            calls.append(ToolCall(
                id=f"tool_{len(calls)+1}",
                name="web_search",
                arguments={"query": t_query}
            ))
            
    return ToolPlan(calls=calls, notes="; ".join(notes) if notes else None)
