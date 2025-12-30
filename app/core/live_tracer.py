"""
Mami AI - Live Tracer
=====================
Sistemin çalışma mantığını canlı olarak terminale basan yardımcı modül.
Prodüksiyon loglarından farklı olarak, geliştiriciye "ne oluyor?" sorusunun cevabını
anlık ve renkli olarak verir.
"""

import sys
from datetime import datetime

class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

class LiveTracer:
    """
    Sistem akışını terminale renkli basan tracer.
    Statik metodlar kullanır, instance yaratmaya gerek yoktur.
    """
    
    ENABLED = True
    
    @classmethod
    def _print(cls, color: str, component: str, event: str, detail: str = ""):
        if not cls.ENABLED:
            return
            
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # Format: [TIME] [COMPONENT] EVENT | Detail
        prefix = f"{Ansi.WHITE}[{time_str}]{Ansi.RESET} {Ansi.BOLD}{color}[{component.upper()}]{Ansi.RESET}"
        message = f"{Ansi.BOLD}{event}{Ansi.RESET}"
        
        if detail:
            message += f" | {detail}"
            
        print(f"{prefix} {message}")
        sys.stdout.flush()

    @classmethod
    def request_in(cls, path: str, method: str):
        """Yeni bir istek geldiğinde."""
        cls._print(Ansi.BLUE, "GATEWAY", "Request In", f"{method} {path}")

    @classmethod
    def routing_decision(cls, route_name: str, confidence: float, reasoning: str = ""):
        """Router karar verdiğinde."""
        conf_str = f"{confidence:.2f}"
        detail = f"Dest: {route_name} (Conf: {conf_str})"
        if reasoning:
            detail += f" - {reasoning}"
        cls._print(Ansi.MAGENTA, "ROUTER", "Decision", detail)

    @classmethod
    def model_select(cls, model_id: str, provider: str, hint: str):
        """Model seçildiğinde."""
        cls._print(Ansi.CYAN, "ADAPTER", "Model Check", f"{provider.upper()} -> {model_id} (Hint: {hint})")

    @classmethod
    def llm_call(cls, model: str, prompt_len: int):
        """LLM API çağrısı yapılıyor."""
        cls._print(Ansi.YELLOW, "LLM", "Calling API", f"Model: {model} | Prompt Len: {prompt_len}")

    @classmethod
    def llm_response(cls, duration_ms: float, token_usage: int = 0):
        """LLM yanıt döndü."""
        cls._print(Ansi.GREEN, "LLM", "Response OK", f"Took: {duration_ms:.0f}ms")

    @classmethod
    def error(cls, component: str, error_msg: str):
        """Hata oluştu."""
        cls._print(Ansi.RED, component, "ERROR", error_msg)

    @classmethod
    def warning(cls, component: str, msg: str):
        """Uyarı."""
        cls._print(Ansi.YELLOW, component, "WARNING", msg)
