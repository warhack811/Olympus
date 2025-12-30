# app/orchestrator_v42/plugin_host.py

from typing import Any, Dict, Optional

class PluginHost:
    """
    Minimal Plugin Barındırıcısı.
    
    Şu katmanlar arasında sınır görevi görür:
    - Core Orchestrator (Zamanlayıcı, Güvenlik, İzlenebilirlik)
    - Pluginler (Yönlendirme, Araçlar, RAG Stratejisi)
    
    Bu yapı, tasarımın 'Arayüz Çekirdekte, Uygulama Pluginde' ilkesine sadık kalır.
    """
    def __init__(self):
        self._plugins: Dict[str, Any] = {}

    def register(self, name: str, plugin: Any) -> None:
        """Yeni bir plugin örneğini ismine göre kaydeder."""
        self._plugins[name] = plugin
        
    def get_plugin(self, name: str) -> Optional[Any]:
        """Kayıtlı bir plugin'i ismine göre getirir, yoksa None döner."""
        return self._plugins.get(name)
