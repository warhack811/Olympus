# app/orchestrator_v42/types.py

from typing import Literal, Any, Dict, List, Optional
from pydantic import BaseModel, Field

def dump_model(obj: Any) -> Dict[str, Any]:
    """
    Pydantic modelini veya diğer nesneleri güvenli bir şekilde Sözlüğe (Dict) çevirir.
    Dönüş tipi HER ZAMAN Dict[str, Any] olmak zorundadır.
    
    Kurallar:
    - Dict ise: Aynen döndür.
    - List ise: {"liste": obj} döndür.
    - Pydantic v2: model_dump() kullan.
    - Pydantic v1: dict() kullan.
    - Diğer: {"değer": str(obj)} döndür.
    """
    if isinstance(obj, dict):
        return obj
    
    if isinstance(obj, list):
        return {"liste": obj}
    
    if hasattr(obj, "model_dump"):
        # Pydantic v2
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        # Pydantic v1
        return obj.dict()
    else:
        # Pydantic olmayan tipler için kurtarıcı
        return {"değer": str(obj)}

# --- TEMEL KARAR MODELLERİ ---

class RoutingDecision(BaseModel):
    mode: Literal["legacy_passthrough", "orchestrator"] = "legacy_passthrough"
    reason: str | None = None
    target_model: str | None = None
    
class GatewayResult(BaseModel):
    decision: RoutingDecision | None = None # Backward compat için opsiyonel
    trace_id: str
    payload: Any | None = None
    
    # Faz 13.3 Orchestrator Yanıt Alanları
    response_text: str | None = None
    model_name: str | None = None
    usage_stats: Dict[str, Any] | None = None

# --- RAPORLAMA MODELLERİ (FAZ 1.0 / 7.1 Güncellemesi) ---

class TaskItem(BaseModel):
    id: str
    type: str
    depends_on: List[str] = Field(default_factory=list)
    priority: int = 1
    meta: Dict[str, Any] = Field(default_factory=dict)

class IntentReport(BaseModel):
    tasks: List[TaskItem]
    composer: str
    complexity: str
    domain: str
    rag_decision: str
    tool_hints: List[str] = Field(default_factory=list)
    matched_rules: List[str] = Field(default_factory=list)

class SafetyReport(BaseModel):
    input_safe: bool
    risk: str
    notes: str | None = None
    matched_rules: List[str] = Field(default_factory=list) 

# --- RAPORLAMA MODELLERİ (FAZ 2.0 / 8.0 Güncellemesi) ---

class CapabilityReport(BaseModel):
    required_capabilities: List[str]
    domain: str = "general"
    complexity: str = "low"
    rag_decision: str = "off"
    notes: Optional[str] = None
    matched_rules: List[str] = Field(default_factory=list)

# --- RAPORLAMA MODELLERİ (FAZ 2.0 / 9.0 Güncellemesi) ---

class ModelSelectionReport(BaseModel):
    selected_model_id: str
    score: int
    candidates_considered: int
    reason: str
    missing_capabilities: List[str] = Field(default_factory=list)
    matched_capabilities: List[str] = Field(default_factory=list)
    matched_rules: List[str] = Field(default_factory=list)

# --- RAPORLAMA MODELLERİ (FAZ 3.0) ---

class RuntimePolicyReport(BaseModel):
    selected_key_id: str
    max_key_attempts: int
    cooldown_seconds: int
    timeout_seconds: int
    circuit_breaker_open: bool
    reason: str

# --- RAPORLAMA MODELLERİ (FAZ 4.0) ---

class CodeBlock(BaseModel):
    language: str
    code: str

class SpecialistOutput(BaseModel):
    solution_text: str
    code_blocks: List[CodeBlock] = Field(default_factory=list)
    claims: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)

class ContractedOutput(BaseModel):
    solution_text: str
    code_blocks: List[CodeBlock]
    claims: List[str]
    evidence: List[str]
    immutable_hash: str

class OutputSanitizerReport(BaseModel):
    was_modified: bool
    reason: str | None = None

# --- RAPORLAMA MODELLERİ (FAZ 5.0) ---

class StreamingRewriteReport(BaseModel):
    enabled: bool
    bypassed: bool
    queue_depth: int
    reason: str | None
    chunks_in: int
    chunks_out: int
    modified: bool

class VerifyReport(BaseModel):
    ran: bool
    passed: bool
    risk_level: str
    notes: str | None = None

class JuryReport(BaseModel):
    ran: bool
    chosen: str | None = None
    reason: str | None = None

# --- RAPORLAMA MODELLERİ (FAZ 6.0) ---

class RetrievedDoc(BaseModel):
    id: str
    text: str
    source: str
    score: float

class RagGateReport(BaseModel):
    decision: str  # "on" | "off"
    signal_reasons: List[str]
    quick_check: Dict[str, Any]
    notes: str

class RagAdapterReport(BaseModel):
    ran: bool
    dry_run: bool
    doc_count: int
    docs: List[RetrievedDoc]
    notes: str

class LlmAdapterReport(BaseModel):
    ran: bool
    dry_run: bool
    text: str
    raw: Dict[str, Any]
    used_model_hint: str | None
    text_len: int
    notes: str | None
