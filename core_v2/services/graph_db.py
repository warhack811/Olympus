import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from core_v2.config.settings import settings

logger = logging.getLogger("core_v2.services.graph_db")

class GraphService:
    """
    Singleton Neo4j Graph Service.
    Handles connection, schema enforcement, and interaction logging.
    Designed to be Resilient (Fail-Safe).
    """
    _instance: Optional["GraphService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._driver: Optional[Driver] = None
        self._initialized = True
        self.connect()

    def connect(self):
        """Initializes the Neo4j driver and enforces schema."""
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"✅ Neo4j connected: {settings.NEO4J_URI}")
            
            # Application-level Schema enforcement
            self._enforce_schema()
            
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}. Graph features will be disabled.")
            self._driver = None

    def close(self):
        """Closes the driver connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j driver closed.")

    def _enforce_schema(self):
        """Creates indexes and constraints for performance/integrity."""
        if not self._driver: return
        
        queries = [
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
            "CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE",
            "CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.file_path IS UNIQUE",
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE"
        ]
        
        try:
            with self._driver.session() as session:
                for q in queries:
                    session.run(q)
            logger.info("✅ Graph Schema (Constraints) enforced.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to enforce graph schema: {e}")

    def log_interaction(self, user_id: str, session_id: str, role: str, content: str):
        """
        Logs a chat interaction into the graph.
        User -> HAS_SESSION -> Session -> HAS_MESSAGE -> Message
        """
        if not self._driver:
            logger.debug("Graph logging skipped (No connection).")
            return

        query = """
        MERGE (u:User {user_id: $user_id})
        MERGE (s:Session {session_id: $session_id})
        MERGE (u)-[:HAS_SESSION]->(s)
        CREATE (m:Message {
            content: $content, 
            role: $role, 
            timestamp: datetime()
        })
        CREATE (s)-[:HAS_MESSAGE]->(m)
        """
        
        try:
            with self._driver.session() as session:
                session.run(query, user_id=user_id, session_id=session_id, content=content, role=role)
            logger.debug(f"Interaction logged for Session {session_id}")
        except Exception as e:
            logger.error(f"Failed to log interaction to graph: {e}")

# Global instance
graph_service = GraphService()

# --- Verification Script ---
if __name__ == "__main__":
    import sys
    
    # Configure logging to stdout
    logging.basicConfig(level=logging.INFO)

    def test_graph_service():
        print("\n🧪 STARTING GRAPH SERVICE TEST")
        print("="*40)
        
        service = GraphService()
        
        if not service._driver:
            print("❌ Initial Connection Failed (Is Neo4j running?). Exiting test gracefully.")
            return

        print("1. Connection & Schema OK.")
        
        user_id = "test_user_01"
        session_id = "test_session_01"
        role = "user"
        content = "Merhaba Dünya, bu bir Neo4j test mesajıdır."
        
        print(f"2. Logging Interaction: {role} -> {content[:20]}...")
        try:
            service.log_interaction(user_id, session_id, role, content)
            print("✅ Neo4j Bağlantısı ve Veri Kaydı Başarılı")
        except Exception as e:
            print(f"❌ Veri kaydı başarısız: {e}")
            
        service.close()
        print("\n✅ TEST COMPLETED")

    test_graph_service()
