from contextvars import ContextVar
import uuid

# Global Context Variables (Thread-Safe)
_trace_id_ctx = ContextVar("trace_id", default=None)
_user_id_ctx = ContextVar("user_id", default=None)

def get_trace_id() -> str:
    tid = _trace_id_ctx.get()
    if not tid:
        # Fallback: Eğer context set edilmemişse yeni üret (Development kolaylığı)
        tid = uuid.uuid4().hex[:8]
        _trace_id_ctx.set(tid)
    return tid

def set_trace_id(tid: str):
    _trace_id_ctx.set(tid)

def get_user_id() -> str | None:
    return _user_id_ctx.get()

def set_user_id(uid: str):
    _user_id_ctx.set(uid)
