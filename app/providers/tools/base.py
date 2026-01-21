"""
Mami AI - Base Tool (Atlas Sovereign Edition)
---------------------------------------------
Tüm araçların uyması gereken arayüz (interface).

Temel Özellikler:
1. Soyut Sınıf (ABC): Tüm araçlar bu sınıftan türetilmeli
2. Standart Arayüz: name, description ve execute() zorunlu
3. OpenAI Function Format: LLM function-calling uyumu
4. Asenkron Tasarım: execute() async olmalı
5. Telemetry: Otomatik start/success/error event'leri
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel

from app.core.telemetry.service import telemetry, EventType


class BaseTool(ABC):
    """Tüm araçların türetilmesi gereken soyut temel sınıf."""
    
    # Zorunlu alanlar
    name: str = ""
    description: str = ""
    input_schema: Type[BaseModel] = None
    
    def __init__(self, name: str = None, description: str = None, input_schema: Type[BaseModel] = None):
        """Initialize tool with optional name, description, and schema."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if input_schema is not None:
            self.input_schema = input_schema
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Tool'un asıl işini yaptığı metod. Asenkron olmalıdır."""
        pass
    
    async def execute_with_telemetry(self, **kwargs) -> Any:
        """Telemetry wrapper ile execute çağrısı."""
        telemetry.emit(
            EventType.TOOL_EXECUTION,
            {"tool": self.name, "status": "start", "params": list(kwargs.keys())},
            component=f"tool_{self.name}"
        )
        
        try:
            result = await self.execute(**kwargs)
            telemetry.emit(
                EventType.TOOL_EXECUTION,
                {"tool": self.name, "status": "success"},
                component=f"tool_{self.name}"
            )
            return result
        except Exception as e:
            telemetry.emit(
                EventType.TOOL_EXECUTION,
                {"tool": self.name, "status": "error", "error": str(e)},
                component=f"tool_{self.name}"
            )
            raise
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Tool'un LLM'e gönderilecek JSON şemasını döndürür."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema.model_json_schema()
            }
        }
