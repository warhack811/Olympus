from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RequestContext:
    """
    Request-scoped context container.
    Collects memory context, history, and metadata once per request.
    """

    trace_id: str
    user_id: str
    username: str
    session_id: str
    message: str
    persona: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    style_profile: Optional[Any] = None
    assistant_message_id: Optional[int] = None
    images: List[str] = field(default_factory=list) # Vision Support

    memory_context: str = ""
    history_text: str = ""
    history_list: List[Dict[str, Any]] = field(default_factory=list)
    due_tasks: List[Dict[str, Any]] = field(default_factory=list)
    semantic_memories: str = ""
    graph_memories: str = ""
    plan: Optional[Any] = None
    task_results: List[Dict[str, Any]] = field(default_factory=list)
    tool_outputs: str = ""
    response: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def set_history(self, history_list: List[Dict[str, Any]]) -> None:
        self.history_list = history_list
        self.history_text = "\n".join(
            f"{item.get('role')}: {item.get('content')}"
            for item in history_list
            if item.get("role") and item.get("content") is not None
        )

    def append_context(self, text: str) -> None:
        if not text:
            return
        if self.memory_context:
            self.memory_context = f"{self.memory_context}\n\n{text}"
        else:
            self.memory_context = text
