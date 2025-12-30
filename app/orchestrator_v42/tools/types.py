from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class ToolResult:
    id: str
    name: str
    ok: bool
    ok: bool
    output: Any
    error: Optional[str] = None

@dataclass
class ToolPlan:
    calls: List[ToolCall] = field(default_factory=list)
    notes: Optional[str] = None
