from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    SYSTEM = "system"
    ROUTING = "routing"
    LLM_REQUEST = "llm_request"
    TOOL_EXECUTION = "tool_execution"
    MEMORY_OP = "memory_op"
    ERROR = "error"
    SECURITY = "security"
    RETRIEVAL = "retrieval"
    LLM_GENERATION_SUCCESS = "llm_generation_success"
    LLM_GENERATION_TIMEOUT = "llm_generation_timeout"
    LLM_GENERATION_ERROR = "llm_generation_error"
    LLM_GENERATION_ALL_FAILED = "llm_generation_all_failed"

class TelemetryEvent(BaseModel):
    trace_id: str
    timestamp: float = Field(default_factory=lambda: __import__("time").time())
    type: EventType
    component: str
    data: Dict[str, Any]
    
    class Config:
        use_enum_values = True
