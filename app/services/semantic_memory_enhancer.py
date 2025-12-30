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
from datetime import datetime, timedelta
from typing import Any
from dataclasses import dataclass

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

class SimhashStore:
    """
    Simhash değerlerini tutar ve hızlı benzerlik araması yapar.
    
    Production'da Redis'e taşınabilir.
    """
    
    # {user_id: {memory_id: Simhash}}
    _store: dict[int, dict[str, Simhash]] = {}
    
    # Similarity threshold
    SIMILARITY_THRESHOLD = 0.95  # Blueprint: similarity > 0.95 → merge
    HAMMING_THRESHOLD = 3        # ~95% similarity için max 3 bit fark
    
    @classmethod
    def add(cls, user_id: int, memory_id: str, text: str) -> Simhash:
        """Simhash ekler."""
        if user_id not in cls._store:
            cls._store[user_id] = {}
        
        sh = Simhash(text)
        cls._store[user_id][memory_id] = sh
        return sh
    
    @classmethod
    def find_similar(cls, user_id: int, text: str) -> SimhashResult:
        """Benzer memory arar."""
        new_sh = Simhash(text)
        
        if user_id not in cls._store:
            return SimhashResult(is_duplicate=False)
        
        for memory_id, existing_sh in cls._store[user_id].items():
            dist = new_sh.distance(existing_sh)
            sim = new_sh.similarity(existing_sh)
            
            if dist <= cls.HAMMING_THRESHOLD:
                return SimhashResult(
                    is_duplicate=True,
                    existing_id=memory_id,
                    hamming_distance=dist,
                    similarity=sim
                )
        
        return SimhashResult(is_duplicate=False, similarity=0.0)
    
    @classmethod
    def remove(cls, user_id: int, memory_id: str) -> bool:
        """Simhash siler."""
        if user_id in cls._store and memory_id in cls._store[user_id]:
            del cls._store[user_id][memory_id]
            return True
        return False
    
    @classmethod
    def clear_user(cls, user_id: int) -> int:
        """Kullanıcının tüm simhash'lerini siler."""
        if user_id in cls._store:
            count = len(cls._store[user_id])
            del cls._store[user_id]
            return count
        return 0


# =============================================================================
# DOUBLE GRADER
# =============================================================================

class DoubleGrader:
    """
    Double Grader - Scout + Qwen Consensus.
    
    Blueprint v1: "Scout grader → Qwen grader → Consensus"
    Her ikisi de > 0.7 ise kabul.
    """
    
    # Thresholds
    GRADE_THRESHOLD = 0.7      # Her model için minimum skor
    SCOUT_TIMEOUT = 0.5        # 500ms
    QWEN_TIMEOUT = 1.0         # 1s
    
    @classmethod
    async def grade_memory(
        cls,
        query: str,
        memory_text: str,
        memory_id: str
    ) -> GradeResult:
        """
        Memory'yi query'ye göre puanlar.
        
        Args:
            query: Kullanıcı sorgusu
            memory_text: Memory içeriği
            memory_id: Memory ID
            
        Returns:
            GradeResult: Puanlama sonucu
        """
        try:
            # Scout grading (fast model - simulated with heuristics for now)
            scout_score = await cls._scout_grade(query, memory_text)
            
            # If Scout fails early, skip Qwen
            if scout_score < 0.5:
                return GradeResult(
                    memory_id=memory_id,
                    scout_score=scout_score,
                    qwen_score=0.0,
                    consensus_score=scout_score / 2,
                    passed=False,
                    reason="scout_failed_early"
                )
            
            # Qwen grading (quality model - simulated for now)
            qwen_score = await cls._qwen_grade(query, memory_text)
            
            # Consensus
            consensus = (scout_score + qwen_score) / 2
            passed = scout_score >= cls.GRADE_THRESHOLD and qwen_score >= cls.GRADE_THRESHOLD
            
            return GradeResult(
                memory_id=memory_id,
                scout_score=scout_score,
                qwen_score=qwen_score,
                consensus_score=consensus,
                passed=passed,
                reason="consensus_passed" if passed else "consensus_failed"
            )
            
        except Exception as e:
            logger.error(f"[GRADER] Error grading memory {memory_id}: {e}")
            return GradeResult(
                memory_id=memory_id,
                scout_score=0.5,  # Safe default
                qwen_score=0.5,
                consensus_score=0.5,
                passed=False,
                reason=f"error: {e}"
            )
    
    @classmethod
    async def _scout_grade(cls, query: str, memory_text: str) -> float:
        """
        Scout grading (fast heuristic-based for now).
        
        Future: Replace with actual LLM call to fast model.
        """
        # Heuristic scoring based on keyword overlap and length
        query_words = set(query.lower().split())
        memory_words = set(memory_text.lower().split())
        
        if not query_words or not memory_words:
            return 0.5
        
        # Keyword overlap
        overlap = len(query_words & memory_words)
        max_possible = min(len(query_words), len(memory_words))
        
        if max_possible == 0:
            return 0.5
        
        keyword_score = overlap / max_possible
        
        # Length penalty (too short = less info, too long = noise)
        length = len(memory_text)
        if length < 10:
            length_score = 0.3
        elif length > 500:
            length_score = 0.7
        else:
            length_score = 0.9
        
        return min(1.0, (keyword_score * 0.7) + (length_score * 0.3))
    
    @classmethod
    async def _qwen_grade(cls, query: str, memory_text: str) -> float:
        """
        Qwen grading (quality check).
        
        Future: Replace with actual LLM call to Qwen model.
        """
        # For now, use slightly different heuristics
        # This simulates the "second opinion" from Qwen
        
        query_lower = query.lower()
        memory_lower = memory_text.lower()
        
        # Check for semantic relevance indicators
        relevance_keywords = [
            "isim", "ad", "name", "meslek", "job", "yaş", "age",
            "şehir", "city", "proje", "project", "tercih", "preference"
        ]
        
        keyword_hits = sum(1 for kw in relevance_keywords if kw in query_lower or kw in memory_lower)
        keyword_score = min(1.0, keyword_hits / 3)  # Normalize
        
        # Content quality check
        if len(memory_text) < 5:
            quality_score = 0.2
        elif any(c.isupper() for c in memory_text):  # Has proper nouns
            quality_score = 0.9
        else:
            quality_score = 0.7
        
        return (keyword_score * 0.4) + (quality_score * 0.6)


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
        result = SimhashStore.find_similar(user_id, text)
        return result.is_duplicate, result
    
    @classmethod
    async def register_memory_simhash(
        cls,
        user_id: int,
        memory_id: str,
        text: str
    ) -> Simhash:
        """Memory için Simhash kaydeder."""
        return SimhashStore.add(user_id, memory_id, text)
    
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
