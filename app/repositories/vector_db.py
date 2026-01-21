import time
import logging
from typing import Any, Dict, List, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from app.config import get_settings
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger("app.repository.vector")

class VectorRepository:
    """
    Atlas Vector Memory Repository.
    Singleton class providing asynchronous access to Qdrant.
    """
    _instance: Optional["VectorRepository"] = None
    _client: Optional[AsyncQdrantClient] = None
    _collection_name = "atlas_memory_v4"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def _initialize(self):
        """Initializes the Qdrant client and ensures the collection exists."""
        if self._client is None:
            settings = get_settings()
            try:
                self._client = AsyncQdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )
                
                # Check for collection existence
                collections = await self._client.get_collections()
                exists = any(c.name == self._collection_name for c in collections.collections)
                
                if not exists:
                    dim = settings.ATLAS_EMBED_DIM
                    await self._client.create_collection(
                        collection_name=self._collection_name,
                        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE)
                    )
                    logger.info(f"Qdrant collection '{self._collection_name}' created (dim={dim}).")
                
                # Ensure user_id index exists (Phase 2 requirement for filtering)
                # This is safe to run even if it exists
                await self._client.create_payload_index(
                    collection_name=self._collection_name,
                    field_name="user_id",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                
                logger.debug("Qdrant client initialized and user_id index ensured.")
            except Exception as e:
                telemetry.emit(
                    EventType.ERROR, 
                    {"component": "qdrant", "message": f"Client init failed: {str(e)}"},
                    component="vector_repo"
                )
                raise

    async def upsert(self, point_id: str, vector: List[float], payload: Dict[str, Any]):
        """Inserts or updates a point in the vector database."""
        await self._initialize()
        start_time = time.time()
        try:
            await self._client.upsert(
                collection_name=self._collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            duration = time.time() - start_time
            telemetry.emit(
                EventType.MEMORY_OP, 
                {"db": "qdrant", "op": "upsert", "id": point_id, "duration": duration},
                component="vector_repo"
            )
        except Exception as e:
            duration = time.time() - start_time
            telemetry.emit(
                EventType.ERROR, 
                {"db": "qdrant", "op": "upsert", "duration": duration, "error": str(e)},
                component="vector_repo"
            )
            raise

    async def search(self, vector: List[float], limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Searches for similar vectors in the database."""
        await self._initialize()
        start_time = time.time()
        try:
            if hasattr(self._client, "search"):
                results = await self._client.search(
                    collection_name=self._collection_name,
                    query_vector=vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
            elif hasattr(self._client, "query_points"):
                response = await self._client.query_points(
                    collection_name=self._collection_name,
                    query=vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
                results = response.points
            else:
                raise AttributeError("AsyncQdrantClient has no search/query_points method")
            
            hits = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]
            
            duration = time.time() - start_time
            telemetry.emit(
                EventType.MEMORY_OP, 
                {"db": "qdrant", "op": "search", "limit": limit, "duration": duration, "hit_count": len(hits)},
                component="vector_repo"
            )
            return hits
        except Exception as e:
            duration = time.time() - start_time
            telemetry.emit(
                EventType.ERROR, 
                {"db": "qdrant", "op": "search", "duration": duration, "error": str(e)},
                component="vector_repo"
            )
            raise

    async def delete(self, point_id: str):
        """Removes a point from the vector database."""
        await self._initialize()
        start_time = time.time()
        try:
            await self._client.delete(
                collection_name=self._collection_name,
                points_selector=models.PointIdsList(points=[point_id])
            )
            duration = time.time() - start_time
            telemetry.emit(
                EventType.MEMORY_OP, 
                {"db": "qdrant", "op": "delete", "id": point_id, "duration": duration},
                component="vector_repo"
            )
        except Exception as e:
            duration = time.time() - start_time
            telemetry.emit(
                EventType.ERROR, 
                {"db": "qdrant", "op": "delete", "duration": duration, "error": str(e)},
                component="vector_repo"
            )
            raise
    
    async def delete_by_filter(self, filter_conditions: Dict[str, Any]) -> int:
        """
        Delete points matching filter conditions.
        Useful for deleting all vectors for a specific user.
        
        Args:
            filter_conditions: e.g. {"user_id": "user_123"}
        
        Returns:
            Placeholder (Qdrant doesn't return exact count)
        """
        await self._initialize()
        start_time = time.time()
        
        try:
            # Build filter
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )
            
            filter_obj = models.Filter(must=conditions)
            
            # Delete with filter
            await self._client.delete(
                collection_name=self._collection_name,
                points_selector=models.FilterSelector(filter=filter_obj)
            )
            
            duration = time.time() - start_time
            telemetry.emit(
                EventType.MEMORY_OP,
                {"db": "qdrant", "op": "delete_by_filter", "filter": str(filter_conditions), "duration": duration},
                component="vector_repo"
            )
            
            logger.info(f"[Qdrant] Deleted points with filter: {filter_conditions}")
            
            return 0  # Qdrant doesn't return exact count
            
        except Exception as e:
            duration = time.time() - start_time
            telemetry.emit(
                EventType.ERROR,
                {"db": "qdrant", "op": "delete_by_filter", "duration": duration, "error": str(e)},
                component="vector_repo"
            )
            logger.error(f"[Qdrant] Filter deletion failed: {e}")
            raise
    
    async def count_by_filter(self, filter_conditions: Dict[str, Any]) -> int:
        """
        Count points matching filter conditions.
        
        Args:
            filter_conditions: e.g. {"user_id": "user_123"}
        
        Returns:
            Approximate count of matching points
        """
        await self._initialize()
        
        try:
            # Build filter (same as delete_by_filter)
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )
            
            filter_obj = models.Filter(must=conditions)
            
            # Count using scroll (get IDs only, limit to avoid memory issue)
            result = await self._client.scroll(
                collection_name=self._collection_name,
                scroll_filter=filter_obj,
                limit=10000,  # Max reasonable count
                with_payload=False,
                with_vectors=False
            )
            
            # result is a tuple: (points, next_page_offset)
            points, _ = result
            count = len(points)
            
            logger.info(f"[Qdrant] Counted {count} points with filter: {filter_conditions}")
            
            return count
            
        except Exception as e:
            logger.error(f"[Qdrant] Count failed: {e}")
            return 0  # Fallback

# Singleton export
vector_repo = VectorRepository()
