from app.core.telemetry.service import telemetry, EventType
import uuid

class LiveTracer:
    """
    Legacy Adapter for new Telemetry Service.
    Eski kodlar kırılmasın diye var.
    """
    
    @staticmethod
    def _get_trace_id() -> str:
        # Trace ID yoksa geçici üret (Session bazlı trace yakında gelecek)
        return str(uuid.uuid4())[:8]

    @staticmethod
    def request_in(path: str, method: str):
        telemetry.emit(
            EventType.SYSTEM, 
            LiveTracer._get_trace_id(), 
            {"event": "request_in", "path": path, "method": method}
        )

    @staticmethod
    def routing_decision(route_name: str, confidence: float, reasoning: str = ""):
        telemetry.emit(
            EventType.ROUTING, 
            LiveTracer._get_trace_id(), 
            {"route": route_name, "confidence": confidence, "reasoning": reasoning}
        )

    @staticmethod
    def model_select(model_id: str, provider: str, hint: str):
        telemetry.emit(
            EventType.LLM_REQUEST, 
            LiveTracer._get_trace_id(), 
            {"event": "model_select", "model_id": model_id, "provider": provider, "hint": hint}
        )

    @staticmethod
    def llm_call(model: str, prompt_len: int):
        telemetry.emit(
            EventType.LLM_REQUEST, 
            LiveTracer._get_trace_id(), 
            {"event": "llm_call", "model": model, "prompt_len": prompt_len}
        )

    @staticmethod
    def llm_response(duration_ms: float, token_usage: int = 0):
        telemetry.emit(
            EventType.LLM_REQUEST, 
            LiveTracer._get_trace_id(), 
            {"event": "llm_response", "duration_ms": duration_ms, "token_usage": token_usage}
        )

    @staticmethod
    def error(component: str, error_msg: str):
        telemetry.emit(
            EventType.SYSTEM, 
            LiveTracer._get_trace_id(), 
            {"event": "error", "component": component, "message": error_msg}
        )

    @staticmethod
    def warning(component: str, msg: str):
        telemetry.emit(
            EventType.SYSTEM, 
            LiveTracer._get_trace_id(), 
            {"event": "warning", "component": component, "message": msg}
        )
