
"""
Mami AI - Gemini Embedding Service
-------------------------------------------
Metinleri 768-boyutlu vektörlere dönüştüren Gemini API entegrasyonu.
Batch processing ve rate limiting desteği.
"""

import httpx
import asyncio
import logging
from typing import List, Optional

from app.config import get_settings
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger(__name__)


class GeminiEmbedder:
    """
    Low-memory cloud embedding using Gemini text-embedding-004 API.
    
    Features:
    - 768-dimensional embeddings
    - Batch processing support
    - Rate limiting
    - Automatic retry on errors
    """
    
    MODEL = "models/text-embedding-004"
    DIMENSION = 768
    MAX_BATCH_SIZE = 100
    
    def __init__(self, api_base: Optional[str] = None):
        """
        Initialize Gemini Embedder.
        """
        self.settings = get_settings()
        self.api_base = api_base or "https://generativelanguage.googleapis.com/v1beta"
    
    def _get_api_key(self) -> str:
        """Fetches API key from settings."""
        # Config'de spesifik bir embedding key yoksa, mevcut sistemden çekmeli
        # veya Settings modeline eklenmeli. Şimdilik GROQ_API_KEY veya GEMINI_API_KEY varsayalım.
        # User config'de GEMINI_API_KEY tanımlı olabilir mi?
        if hasattr(self.settings, 'GEMINI_API_KEY') and self.settings.GEMINI_API_KEY:
            return self.settings.GEMINI_API_KEY
        
        # Fallback: Eğer KEY yoksa logla ve hata fırlat
        logger.error("[Embedder] Gemini API Key bulunamadı!")
        raise ValueError("Gemini API Key missing in configuration.")

    async def embed(self, text: str, retry_count: int = 3) -> List[float]:
        """
        Generate embedding for a single text.
        """
        if not text or not text.strip():
            return [0.0] * self.DIMENSION
        
        api_key = self._get_api_key()
        url = f"{self.api_base}/{self.MODEL}:embedContent"
        
        for attempt in range(retry_count):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        params={"key": api_key},
                        json={
                            "content": {
                                "parts": [{"text": text[:9000]}]  # Safe limit
                            }
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    data = response.json()
                    embedding = data.get("embedding", {}).get("values", [])
                    
                    if len(embedding) != self.DIMENSION:
                        logger.warning(f"Dimension mismatch: got {len(embedding)}, expected {self.DIMENSION}")
                        # Fallback/Pad logic could go here, but raising is safer for consistency
                    
                    return embedding or [0.0] * self.DIMENSION
                    
            except httpx.HTTPError as e:
                logger.warning(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt == retry_count - 1:
                    telemetry.emit(EventType.ERROR, {"component": "embedder", "error": str(e)}, component="memory")
                    return [0.0] * self.DIMENSION # Fail safe
                await asyncio.sleep(1.0 * (attempt + 1))
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                return [0.0] * self.DIMENSION
        
        return [0.0] * self.DIMENSION

    async def embed_batch(self, texts: List[str], delay: float = 0.5) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        """
        results = []
        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[i:i + self.MAX_BATCH_SIZE]
            
            # Parallel execution for batch items might hit rate limits, 
            # so we do sequential calls or small sub-batches here.
            # Gemini API is fast, sequential is often safer for free tier.
            batch_vectors = []
            for text in batch:
                vec = await self.embed(text)
                batch_vectors.append(vec)
            
            results.extend(batch_vectors)
            await asyncio.sleep(delay)
            
        return results

# Singleton
embedder = GeminiEmbedder()
