import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired, DriverError, Neo4jError
from app.config import get_settings
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger("app.repository.graph")

class GraphRepository:
    """
    Atlas Graph Memory Repository.
    Singleton class providing asynchronous access to Neo4j.
    """
    _instance: Optional["GraphRepository"] = None
    _driver = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def _initialize(self):
        """Initializes the Neo4j driver if not already established."""
        if self._driver is None:
            settings = get_settings()
            try:
                self._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                    max_connection_pool_size=settings.NEO4J_POOL_SIZE,
                    max_connection_lifetime=200,    # Aura limitinden (300s) önce tazelemek için
                    liveness_check_timeout=30,      # Boştaki bağlantıları kullanmadan önce kontrol et
                    connection_timeout=30.0         # İlk bağlantı için zaman aşımı (Cold start desteği)
                )
                logger.info("Neo4j driver initialized.")
            except Exception as e:
                telemetry.emit(
                    EventType.ERROR, 
                    {"component": "neo4j", "message": f"Driver init failed: {str(e)}"},
                    component="graph_repo"
                )
                raise

    async def query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a Cypher query and returns the results as a list of dictionaries.
        
        Args:
            cypher: The Cypher query string.
            params: Optional dictionary of query parameters.
            
        Returns:
            List[Dict]: Records returned by the query.
        """
        max_retries = 3
        for attempt in range(max_retries):
            start_time = time.time()
            try:
                await self._initialize()
                async with self._driver.session() as session:
                    result = await session.run(cypher, params or {})
                    records = await result.data()
                    
                    duration = time.time() - start_time
                    telemetry.emit(
                        EventType.MEMORY_OP, 
                        {
                            "db": "neo4j", 
                            "op": "query",
                            "cypher": cypher[:100] + "..." if len(cypher) > 100 else cypher, 
                            "duration": duration, 
                            "count": len(records),
                            "attempt": attempt + 1
                        },
                        component="graph_repo"
                    )
                    return records
            except (ServiceUnavailable, SessionExpired, ConnectionResetError, DriverError) as e:
                # 'defunct connection' hatası genellikle ServiceUnavailable veya DriverError içinde gelir.
                error_msg = str(e).lower()
                is_transient = any(x in error_msg for x in ["defunct", "reset", "expired", "unavailable", "broken"])
                
                logger.warning(f"[Neo4j] Bağlantı sorunu ({'Geçici' if is_transient else 'Kritik'}), yeniden deneniyor ({attempt+1}/{max_retries}): {e}")
                # Ölü driver'ı temizle
                if self._driver:
                    await self._driver.close()
                    self._driver = None
                
                if attempt == max_retries - 1:
                    logger.error(f"[Neo4j] Kritik Bağlantı Hatası (Tüm denemeler başarısız): {e}")
                    raise
                
                await asyncio.sleep(1) # Kısa bekleme ve tekrar başa (yeni _initialize tetiklenecek)
                
            except Exception as e:
                duration = time.time() - start_time
                telemetry.emit(
                    EventType.ERROR, 
                    {
                        "db": "neo4j", 
                        "op": "query",
                        "cypher": cypher[:100] + "..." if len(cypher) > 100 else cypher,
                        "duration": duration, 
                        "error": str(e)
                    },
                    component="graph_repo"
                )
                logger.error(f"[Neo4j] Sorgu hatası: {str(e)}")
                raise

    async def search_related_nodes(self, user_id: str, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches for nodes and relationships relevant to the query text.
        
        Logic:
        1. Find user node.
        2. Match (User)-[r]->(n)
        3. Where n.name CONTAINS query_text OR n.value CONTAINS query_text
        4. Return formatted strings.
        """
        cypher = """
        MATCH (u:User {id: $user_id})-[r]->(n)
        WHERE (n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($text)) 
           OR (n.value IS NOT NULL AND toLower(n.value) CONTAINS toLower($text))
           OR (type(r) IS NOT NULL AND toLower(type(r)) CONTAINS toLower($text))
        RETURN type(r) as rel, properties(n) as node
        LIMIT $limit
        """
        try:
            results = await self.query(cypher, {"user_id": user_id, "text": query_text, "limit": limit})
            return results
        except Exception:
            return []

    async def close(self):
        """Closes the driver and releases all resources."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed.")

# Singleton export
graph_repo = GraphRepository()
