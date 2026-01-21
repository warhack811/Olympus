# app/services/semantic_memory_enhancer.py
"""
Semantic Memory Enhancer - Blueprint v1 Section 8 Layer 3

Enhanced memory service with:
- Double Grader (Scout + Qwen consensus)
- Simhash Deduplication (custom implementation)
- Importance Decay + TTL
- Memory Merge on high similarity

Kullanım:
    from app.services.semantic_memory_enhancer import SemanticMemoryEnhancer
    
    # Duplicate check with Simhash
    is_dup, reason = await SemanticMemoryEnhancer.is_simhash_duplicate(user_id, text)
    
    # Double grading
    result = await SemanticMemoryEnhancer.grade_memory_relevance(query, memories)
    
    # Importance decay
    decayed_count = await SemanticMemoryEnhancer.apply_importance_decay(user_id)
"""

import asyncio
import logging
import hashlib
from datetime import datetime
from typing import Any
from dataclasses import dataclass

from app.chat.decider import _get_llm_generator
from app.core.llm.generator import LLMRequest

logger = logging.getLogger("orchestrator.semantic_memory")


# =============================================================================
# RESULT TYPES
# =============================================================================

@dataclass
class GradeResult:
    """Double grader sonucu."""
    memory_id: str
    scout_score: float      # Scout model skoru (0-1)
    qwen_score: float       # Qwen model skoru (0-1)
    consensus_score: float  # Ortalama skor
    passed: bool            # Threshold geçti mi?
    reason: str


@dataclass
class SimhashResult:
    """Simhash duplicate check sonucu."""
    is_duplicate: bool
    existing_id: str | None = None
    hamming_distance: int = 64  # 0 = exact match, 64 = completely different
    similarity: float = 0.0


@dataclass
class DecayResult:
    """Importance decay sonucu."""
    memories_processed: int
    memories_decayed: int
    memories_expired: int


# =============================================================================
# SIMHASH IMPLEMENTATION (Custom - No external dependency)
# =============================================================================

class Simhash:
    """
    Simhash algoritması - Locality Sensitive Hashing.
    
    Benzer metinler benzer hash'ler üretir.
    Hamming distance ile benzerlik ölçülür.
    """
    
    # 64-bit hash
    HASH_BITS = 64
    
    def __init__(self, text: str):
        self.value = self._compute(text)
    
    def _tokenize(self, text: str) -> list[str]:
        """Metni n-gram'lara ayırır."""
        # Normalize
        text = text.lower().strip()
        
        # 3-gram'lar (shingling)
        tokens = []
        n = 3
        for i in range(len(text) - n + 1):
            tokens.append(text[i:i+n])
        
        # Kelime bazlı tokenlar da ekle
        words = text.split()
        tokens.extend(words)
        
        return tokens
    
    def _hash_token(self, token: str) -> int:
        """Token'ı 64-bit integer'a hash'ler."""
        h = hashlib.md5(token.encode('utf-8')).hexdigest()[:16]
        return int(h, 16)
    
    def _compute(self, text: str) -> int:
        """Simhash hesaplar."""
        if not text:
            return 0
            
        tokens = self._tokenize(text)
        if not tokens:
            return 0
        
        # Bit count array (64 bit)
        v = [0] * self.HASH_BITS
        
        for token in tokens:
            token_hash = self._hash_token(token)
            
            for i in range(self.HASH_BITS):
                bit = (token_hash >> i) & 1
                if bit == 1:
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # Final hash: majority vote
        fingerprint = 0
        for i in range(self.HASH_BITS):
            if v[i] > 0:
                fingerprint |= (1 << i)
        
        return fingerprint
    
    def distance(self, other: "Simhash") -> int:
        """Hamming distance hesaplar (XOR sonrası 1 sayısı)."""
        x = self.value ^ other.value
        return bin(x).count('1')
    
    def similarity(self, other: "Simhash") -> float:
        """Benzerlik skoru (0-1)."""
        dist = self.distance(other)
        return 1.0 - (dist / self.HASH_BITS)


# =============================================================================
# SIMHASH STORE (In-memory cache for fast lookup)
# =============================================================================

# =============================================================================
# REDIS SIMHASH STORE
# =============================================================================

class SimhashStore:
    """
    Simhash değerlerini tutar ve hızlı benzerlik araması yapar.
    Redis-backed implementation.
    """
    
    # Redis Keys
    KEY_PREFIX = "simhash:"
    
    # Similarity threshold
    SIMILARITY_THRESHOLD = 0.95
    HAMMING_THRESHOLD = 3
    
    @classmethod
    async def add(cls, user_id: int, memory_id: str, text: str) -> Simhash:
        """Redis'e Simhash ekler."""
        from app.core.redis_client import get_redis
        
        redis = await get_redis()
        sh = Simhash(text)
        
        if redis:
            key = f"{cls.KEY_PREFIX}{user_id}"
            # Store as hash: field=memory_id, value=simhash_int
            await redis.hset(key, memory_id, str(sh.value))
            # Set TTL (e.g. 30 days) to match importance decay roughly, or keep it consistent
            # For now, let's keep it persistent like memory
        else:
            logger.warning("[SIMHASH] Redis unavailable, skipping save.")
            
        return sh
    
    @classmethod
    async def find_similar(cls, user_id: int, text: str) -> SimhashResult:
        """Redis'te benzer memory arar."""
        from app.core.redis_client import get_redis
        
        new_sh = Simhash(text)
        redis = await get_redis()
        
        if not redis:
            logger.warning("[SIMHASH] Redis unavailable, skipping check.")
            return SimhashResult(is_duplicate=False)
            
        key = f"{cls.KEY_PREFIX}{user_id}"
        
        # Get all hashes for user
        # Note: If user has 10k memories, this might be heavy. 
        # But for active usage it's acceptable.
        # Future optimization: Use LSH buckets or Vector DB
        all_hashes = await redis.hgetall(key)
        
        if not all_hashes:
            return SimhashResult(is_duplicate=False)
            
        for memory_id, val_str in all_hashes.items():
            try:
                existing_val = int(val_str)
                # Create rudimentary Simhash obj
                existing_sh = Simhash("")
                existing_sh.value = existing_val
                
                dist = new_sh.distance(existing_sh)
                sim = new_sh.similarity(existing_sh)
                
                if dist <= cls.HAMMING_THRESHOLD:
                    return SimhashResult(
                        is_duplicate=True,
                        existing_id=memory_id,
                        hamming_distance=dist,
                        similarity=sim
                    )
            except ValueError:
                continue
        
        return SimhashResult(is_duplicate=False, similarity=0.0)
    
    @classmethod
    async def remove(cls, user_id: int, memory_id: str) -> bool:
        """Redis'ten Simhash siler."""
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if not redis:
            return False
            
        key = f"{cls.KEY_PREFIX}{user_id}"
        result = await redis.hdel(key, memory_id)
        return result > 0
    
    @classmethod
    async def clear_user(cls, user_id: int) -> int:
        """Kullanıcının tüm simhash'lerini siler."""
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if not redis:
            return 0
            
        key = f"{cls.KEY_PREFIX}{user_id}"
        count = await redis.hlen(key)
        await redis.delete(key)
        return count


# =============================================================================
# DOUBLE GRADER
# =============================================================================

SCOUT_GRADER_PROMPT = """
You are a fast relevance filter (Scout).
Rate the relevance of the MEMORY to the QUERY on a scale of 0.0 to 1.0.
- 1.0: Extremely relevant / Direct answer
- 0.5: Somewhat relevant / Related topic
- 0.0: Irrelevant / Noise

QUERY: {query}
MEMORY: {memory}

Rules:
- Output ONLY the float number.
- No explanation.
"""

QWEN_GRADER_PROMPT = """
You are a semantic integrity judge (Qwen).
Analyze the relevance of the MEMORY to the QUERY context.

QUERY: {query}
MEMORY: {memory}

Assess:
- Entity overlap (names, places)
- Topic alignment
- Temporal relevance

Output ONLY a float score between 0.0 and 1.0.
"""

class DoubleGrader:
    """
    Double Grader - Scout + Qwen Consensus (REAL LLM IMPLEMENTATION).
    
    Blueprint v1: "Scout grader (Fast) → Qwen grader (Quality) → Consensus"
    Her ikisi de threshold'u geçerse kabul.
    """
    
    # Thresholds
    GRADE_THRESHOLD = 0.6      # Hafif gevşek tutarak LLM'e alan bırakalım
    
    # Timeouts (Real/Networked)
    SCOUT_TIMEOUT = 2.0        # Fast model response time
    QWEN_TIMEOUT = 4.0         # Large model response time
    
    @classmethod
    async def grade_memory(
        cls,
        query: str,
        memory_text: str,
        memory_id: str
    ) -> GradeResult:
        """
        Memory'yi query'ye göre puanlar (Gerçek LLM çağrıları ile).
        """
        try:
            # Scout grading (Fast/Instant Model)
            scout_score = await cls._scout_grade(query, memory_text)
            
            # Fail-fast: Scout çok düşük verirse Qwen'i yorma (Cost optimization)
            if scout_score < 0.4:
                return GradeResult(
                    memory_id=memory_id,
                    scout_score=scout_score,
                    qwen_score=0.0,
                    consensus_score=scout_score,
                    passed=False,
                    reason="scout_filtered"
                )
            
            # Qwen grading (Quality/Versatile Model)
            qwen_score = await cls._qwen_grade(query, memory_text)
            
            # Consensus: (Scout + Qwen) / 2
            consensus = (scout_score + qwen_score) / 2
            passed = consensus >= cls.GRADE_THRESHOLD
            
            return GradeResult(
                memory_id=memory_id,
                scout_score=scout_score,
                qwen_score=qwen_score,
                consensus_score=consensus,
                passed=passed,
                reason="consensus_passed" if passed else "consensus_low"
            )
            
        except Exception as e:
            logger.error(f"[GRADER] Error grading memory {memory_id}: {e}")
            # Fail-safe: Hata durumunda (örn. API gitti) 0.5 ile şansı sürdür
            return GradeResult(
                memory_id=memory_id,
                scout_score=0.5,
                qwen_score=0.5,
                consensus_score=0.5,
                passed=False,
                reason=f"error_fallback: {e}"
            )
    
    @classmethod
    async def _scout_grade(cls, query: str, memory_text: str) -> float:
        """
        Scout Grade: Fast Model (role="fast").
        """
        prompt = SCOUT_GRADER_PROMPT.format(query=query, memory=memory_text)
        
        try:
            generator = _get_llm_generator()
            request = LLMRequest(
                role="fast",  # Uses Llama-3-8b or similar fast model
                prompt=prompt,
                temperature=0.1 # Deterministic
            )
            
            result = await generator.generate(request)
            if result.ok:
                try:
                    score = float(result.text.strip())
                    return max(0.0, min(1.0, score))
                except ValueError:
                    logger.warning(f"[SCOUT] Invalid float response: {result.text}")
                    return 0.5 # Parsing error fallback
            
            return 0.0 # Generation failed
            
        except Exception as e:
            logger.warning(f"[SCOUT] call failed: {e}")
            return 0.0

    @classmethod
    async def _qwen_grade(cls, query: str, memory_text: str) -> float:
        """
        Qwen Grade: Quality Model (role="answer" or "semantic").
        """
        prompt = QWEN_GRADER_PROMPT.format(query=query, memory=memory_text)
        
        try:
            generator = _get_llm_generator()
            request = LLMRequest(
                role="answer",  # Uses Llama-3-70b/Qwen or similar quality model
                prompt=prompt,
                temperature=0.1
            )
            
            result = await generator.generate(request)
            if result.ok:
                try:
                    score = float(result.text.strip())
                    return max(0.0, min(1.0, score))
                except ValueError:
                    logger.warning(f"[QWEN] Invalid float response: {result.text}")
                    return 0.5
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"[QWEN] call failed: {e}")
            return 0.0



# =============================================================================
# IMPORTANCE DECAY
# =============================================================================

class ImportanceDecay:
    """
    Importance Decay - Eski memorylerin önemini azaltır.
    
    Blueprint v1: "Importance decay + TTL"
    """
    
    # Decay parameters
    DECAY_RATE = 0.95           # Her 30 günde %5 düşüş
    DECAY_PERIOD_DAYS = 30
    MIN_IMPORTANCE = 0.1        # Minimum değer
    ARCHIVE_THRESHOLD = 0.2     # Bu altına düşenler arşivlenir
    
    @classmethod
    def calculate_decayed_importance(
        cls,
        original_importance: float,
        created_at: datetime,
        now: datetime | None = None
    ) -> float:
        """
        Decay uygulanmış importance hesaplar.
        
        Args:
            original_importance: Orijinal importance (0-1)
            created_at: Oluşturulma zamanı
            now: Şu anki zaman (test için override)
            
        Returns:
            float: Decay sonrası importance
        """
        if now is None:
            now = datetime.utcnow()
        
        days_old = (now - created_at).days
        decay_periods = days_old // cls.DECAY_PERIOD_DAYS
        
        if decay_periods <= 0:
            return original_importance
        
        decayed = original_importance * (cls.DECAY_RATE ** decay_periods)
        return max(cls.MIN_IMPORTANCE, decayed)
    
    @classmethod
    def should_archive(cls, current_importance: float) -> bool:
        """Archive olmalı mı?"""
        return current_importance < cls.ARCHIVE_THRESHOLD


# =============================================================================
# MAIN SERVICE
# =============================================================================

class SemanticMemoryEnhancer:
    """
    Semantic Memory Enhancement Service.
    
    Blueprint v1 Section 8 Layer 3 ana servisi.
    """
    
    @classmethod
    async def is_simhash_duplicate(
        cls,
        user_id: int,
        text: str
    ) -> tuple[bool, SimhashResult]:
        """
        Simhash ile duplicate kontrolü yapar.
        
        Returns:
            Tuple[bool, SimhashResult]: (is_duplicate, result)
        """
        result = await SimhashStore.find_similar(user_id, text)
        return result.is_duplicate, result
    
    @classmethod
    async def register_memory_simhash(
        cls,
        user_id: int,
        memory_id: str,
        text: str
    ) -> Simhash:
        """Memory için Simhash kaydeder."""
        """Memory için Simhash kaydeder."""
        return await SimhashStore.add(user_id, memory_id, text)
    
    @classmethod
    async def grade_memories(
        cls,
        query: str,
        memories: list[dict[str, Any]],
        min_consensus: float = 0.7
    ) -> list[dict[str, Any]]:
        """
        Double grader ile memoryleri puanlar.
        
        Args:
            query: Kullanıcı sorgusu
            memories: Memory listesi
            min_consensus: Minimum consensus skoru
            
        Returns:
            List[dict]: Puanlanmış ve filtrelenmiş memoryler
        """
        graded = []
        
        for memory in memories:
            memory_id = memory.get("id", "")
            memory_text = memory.get("text", "")
            
            grade = await DoubleGrader.grade_memory(query, memory_text, memory_id)
            
            if grade.passed and grade.consensus_score >= min_consensus:
                memory["grade"] = {
                    "scout_score": grade.scout_score,
                    "qwen_score": grade.qwen_score,
                    "consensus_score": grade.consensus_score,
                    "passed": grade.passed,
                }
                graded.append(memory)
            else:
                logger.debug(f"[ENHANCER] Memory {memory_id} filtered: {grade.reason}")
        
        # Sort by consensus score
        graded.sort(key=lambda m: m.get("grade", {}).get("consensus_score", 0), reverse=True)
        
        return graded
    
    @classmethod
    async def apply_importance_decay(
        cls,
        user_id: int,
        memories: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], DecayResult]:
        """
        Memorylere importance decay uygular.
        
        Args:
            user_id: Kullanıcı ID
            memories: Memory listesi
            
        Returns:
            Tuple[List[dict], DecayResult]: (updated_memories, stats)
        """
        updated = []
        decayed_count = 0
        expired_count = 0
        now = datetime.utcnow()
        
        for memory in memories:
            original_importance = memory.get("importance", 0.5)
            created_at_str = memory.get("created_at", "")
            
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                created_at = now
            
            new_importance = ImportanceDecay.calculate_decayed_importance(
                original_importance,
                created_at,
                now
            )
            
            if new_importance < original_importance:
                decayed_count += 1
            
            if ImportanceDecay.should_archive(new_importance):
                expired_count += 1
                memory["should_archive"] = True
            else:
                memory["should_archive"] = False
            
            memory["decayed_importance"] = new_importance
            updated.append(memory)
        
        result = DecayResult(
            memories_processed=len(memories),
            memories_decayed=decayed_count,
            memories_expired=expired_count
        )
        
        return updated, result
    
    @classmethod
    async def get_enhanced_memories(
        cls,
        user_id: int,
        query: str,
        memories: list[dict[str, Any]],
        apply_decay: bool = True,
        apply_grading: bool = True
    ) -> list[dict[str, Any]]:
        """
        Full enhancement pipeline: Decay + Grading.
        
        Returns:
            List[dict]: Enhanced ve filtrelenmiş memoryler
        """
        result = memories
        
        # 1. Apply decay
        if apply_decay:
            result, decay_stats = await cls.apply_importance_decay(user_id, result)
            # Filter out archived
            result = [m for m in result if not m.get("should_archive", False)]
            logger.debug(f"[ENHANCER] Decay: {decay_stats}")
        
        # 2. Apply double grading
        if apply_grading:
            result = await cls.grade_memories(query, result)
        
        return result
