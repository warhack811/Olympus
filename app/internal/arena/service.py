"""
Mami AI - Arena Service (Atlas Sovereign Edition)
-------------------------------------------------
Geliştirici test aracı - Modelleri ve promptları test etmek için.

Temel Özellikler:
1. Test Senaryoları: Önceden tanımlı test case'leri çalıştırma
2. Model Karşılaştırma: Farklı modellerin yanıtlarını karşılaştırma
3. Metrik Toplama: Latency, token kullanımı, kalite skoru
"""

import uuid
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Bir test senaryosu."""
    id: str
    name: str
    prompt: str
    expected_keywords: List[str] = field(default_factory=list)
    intent: str = "general"
    persona: str = "friendly"


@dataclass
class TestResult:
    """Test sonucu."""
    test_id: str
    model: str
    response: str
    latency_ms: int
    tokens_used: int
    passed: bool
    score: float
    errors: List[str] = field(default_factory=list)


# Varsayılan test senaryoları
DEFAULT_TEST_CASES = [
    TestCase(
        id="basic_greeting",
        name="Basit Selamlama",
        prompt="Merhaba, nasılsın?",
        expected_keywords=["merhaba", "iyiyim", "nasıl"],
        intent="chat"
    ),
    TestCase(
        id="turkish_test",
        name="Türkçe Dil Testi",
        prompt="Türkiye'nin başkenti neresidir?",
        expected_keywords=["ankara", "başkent"],
        intent="qa"
    ),
    TestCase(
        id="math_test",
        name="Matematik Testi",
        prompt="2+2 kaç eder?",
        expected_keywords=["4", "dört"],
        intent="math"
    ),
    TestCase(
        id="memory_test",
        name="Hafıza Simülasyonu",
        prompt="Benim adım Ali. Bunu hatırla.",
        expected_keywords=["ali", "hatırla", "tamam"],
        intent="personal"
    ),
]


class ArenaService:
    """Test aracı servisi."""
    
    def __init__(self):
        self.test_cases = DEFAULT_TEST_CASES.copy()
        self.results: Dict[str, List[TestResult]] = {}
    
    def add_test_case(self, test_case: TestCase):
        """Yeni test senaryosu ekle."""
        self.test_cases.append(test_case)
    
    def get_test_cases(self) -> List[TestCase]:
        """Tüm test senaryolarını getir."""
        return self.test_cases
    
    async def run_single_test(
        self,
        test_case: TestCase,
        model: str = "llama-3.3-70b-versatile",
        llm_provider = None
    ) -> TestResult:
        """Tek bir test senaryosunu çalıştır."""
        start_time = datetime.now()
        errors = []
        response = ""
        tokens_used = 0
        
        try:
            if llm_provider:
                response = await llm_provider.generate(
                    prompt=test_case.prompt,
                    model=model,
                    temperature=0.7
                )
            else:
                # Fallback: Direct Groq call
                from app.providers.llm.groq import GroqProvider
                provider = GroqProvider()
                response = await provider.generate(
                    prompt=test_case.prompt,
                    model=model,
                    temperature=0.7
                )
            
        except Exception as e:
            errors.append(str(e))
            response = f"[ERROR] {e}"
        
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Keyword kontrolü
        response_lower = response.lower()
        matched_keywords = [kw for kw in test_case.expected_keywords if kw in response_lower]
        score = len(matched_keywords) / len(test_case.expected_keywords) if test_case.expected_keywords else 1.0
        passed = score >= 0.5 and not errors
        
        result = TestResult(
            test_id=test_case.id,
            model=model,
            response=response[:500],
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            passed=passed,
            score=score,
            errors=errors
        )
        
        # Sonucu sakla
        if test_case.id not in self.results:
            self.results[test_case.id] = []
        self.results[test_case.id].append(result)
        
        return result
    
    async def run_all_tests(
        self,
        model: str = "llama-3.3-70b-versatile",
        llm_provider = None
    ) -> Dict[str, Any]:
        """Tüm test senaryolarını çalıştır."""
        run_id = str(uuid.uuid4())[:8]
        results = []
        
        for test_case in self.test_cases:
            result = await self.run_single_test(test_case, model, llm_provider)
            results.append(result)
            await asyncio.sleep(0.5)  # Rate limiting
        
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0
        
        return {
            "run_id": run_id,
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "avg_latency_ms": int(avg_latency),
            "results": [
                {
                    "test_id": r.test_id,
                    "passed": r.passed,
                    "score": r.score,
                    "latency_ms": r.latency_ms,
                    "errors": r.errors
                }
                for r in results
            ]
        }
    
    async def compare_models(
        self,
        models: List[str],
        test_case_id: str = None
    ) -> Dict[str, Any]:
        """Farklı modelleri karşılaştır."""
        comparisons = {}
        
        test_cases = [tc for tc in self.test_cases if tc.id == test_case_id] if test_case_id else self.test_cases[:3]
        
        for model in models:
            model_results = []
            for tc in test_cases:
                result = await self.run_single_test(tc, model)
                model_results.append(result)
            
            avg_score = sum(r.score for r in model_results) / len(model_results)
            avg_latency = sum(r.latency_ms for r in model_results) / len(model_results)
            
            comparisons[model] = {
                "avg_score": avg_score,
                "avg_latency_ms": int(avg_latency),
                "passed": sum(1 for r in model_results if r.passed),
                "total": len(model_results)
            }
        
        return {
            "comparison": comparisons,
            "test_cases": [tc.id for tc in test_cases]
        }


# Singleton
arena_service = ArenaService()
