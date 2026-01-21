"""
Mami AI - Arena API Router
--------------------------
Arena test aracı için API endpointleri.
Sadece DEBUG=True iken çalışır.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.config import get_settings
from app.internal.arena.service import arena_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/internal/arena", tags=["arena"])


class RunTestRequest(BaseModel):
    test_case_id: Optional[str] = None
    model: str = "llama-3.3-70b-versatile"


class CompareModelsRequest(BaseModel):
    models: List[str]
    test_case_id: Optional[str] = None


def check_debug_mode():
    """DEBUG modu kontrolü."""
    settings = get_settings()
    if not getattr(settings, 'DEBUG', False):
        raise HTTPException(status_code=403, detail="Arena only available in DEBUG mode")


@router.get("/test-cases")
async def list_test_cases(_: None = Depends(check_debug_mode)):
    """Tüm test senaryolarını listele."""
    cases = arena_service.get_test_cases()
    return {
        "test_cases": [
            {
                "id": tc.id,
                "name": tc.name,
                "prompt": tc.prompt[:100],
                "intent": tc.intent
            }
            for tc in cases
        ]
    }


@router.post("/run")
async def run_all_tests(
    request: RunTestRequest,
    _: None = Depends(check_debug_mode)
):
    """Tüm testleri çalıştır."""
    try:
        result = await arena_service.run_all_tests(model=request.model)
        return result
    except Exception as e:
        logger.error(f"[Arena] Run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/{test_case_id}")
async def run_single_test(
    test_case_id: str,
    request: RunTestRequest,
    _: None = Depends(check_debug_mode)
):
    """Tek bir testi çalıştır."""
    cases = [tc for tc in arena_service.test_cases if tc.id == test_case_id]
    if not cases:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    try:
        result = await arena_service.run_single_test(cases[0], model=request.model)
        return {
            "test_id": result.test_id,
            "model": result.model,
            "response": result.response,
            "latency_ms": result.latency_ms,
            "passed": result.passed,
            "score": result.score,
            "errors": result.errors
        }
    except Exception as e:
        logger.error(f"[Arena] Single test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_models(
    request: CompareModelsRequest,
    _: None = Depends(check_debug_mode)
):
    """Modelleri karşılaştır."""
    try:
        result = await arena_service.compare_models(
            models=request.models,
            test_case_id=request.test_case_id
        )
        return result
    except Exception as e:
        logger.error(f"[Arena] Compare failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
