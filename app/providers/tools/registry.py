"""
Mami AI - Tool Registry (Atlas Sovereign Edition)
-------------------------------------------------
Sistemdeki tüm araçların merkezi kayıt yöneticisi.

Temel Özellikler:
1. Singleton Pattern: Tek instance tüm araçları yönetir
2. Dinamik Kayıt: Runtime'da araç ekleme
3. OpenAI Schemas: LLM function-calling için şema export
"""

import logging
from typing import Dict, Optional, List, Any

from app.providers.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Sistemdeki tüm tool'ları yöneten merkezi kayıt sınıfı (Singleton)."""
    
    _instance = None
    _tools: Dict[str, BaseTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._tools = {}
        self._register_builtin_tools()
        self._initialized = True
    
    def _register_builtin_tools(self):
        """Yerleşik araçları kaydet."""
        try:
            from app.providers.tools.image_gen import image_gen_tool
            self._tools["image_gen"] = image_gen_tool
            logger.info("Registered tool: image_gen")
        except Exception as e:
            logger.warning(f"Could not register image_gen: {e}")
        
        try:
            from app.providers.tools.time_tool import time_tool
            self._tools["time"] = time_tool
            logger.info("Registered tool: time")
        except Exception as e:
            logger.warning(f"Could not register time: {e}")
    
    def register_tool(self, name: str, tool_instance: BaseTool):
        """Manuel olarak bir tool kaydeder."""
        self._tools[name] = tool_instance
        logger.info(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """İsmi verilen tool'u döndürür."""
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, BaseTool]:
        """Yüklü tüm tool'ları döndürür."""
        return self._tools.copy()
    
    def get_tool_names(self) -> List[str]:
        """Yüklü tool isimlerini döndürür."""
        return list(self._tools.keys())
    
    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        """Tüm tool'ların OpenAI function şemalarını döndürür."""
        schemas = []
        for tool in self._tools.values():
            try:
                schemas.append(tool.to_openai_function())
            except Exception as e:
                logger.warning(f"Could not get schema for {tool.name}: {e}")
        return schemas
    
    async def execute_tool(self, name: str, **kwargs) -> Any:
        """Belirtilen tool'u çalıştırır."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        
        return await tool.execute_with_telemetry(**kwargs)


# Singleton
tool_registry = ToolRegistry()
