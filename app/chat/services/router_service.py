from typing import Any

from app.chat.decider import build_search_queries_async
from app.chat.smart_router import route_message
from app.core.logger import get_logger
from app.services.semantic_classifier import analyze_message_semantics

logger = get_logger(__name__)


class RouterService:
    """Mesaj yönlendirme ve semantic analiz servisi."""

    @staticmethod
    async def analyze_semantics(message: str, is_vision: bool = False) -> dict[str, Any] | None:
        """Mesajın anlamsal analizini yapar."""
        if is_vision:
            # Vision isteği: Semantic analiz yapma, direkt 'vision' profili oluştur
            return {"intent": "vision", "domain": "general", "risk_level": "low"}

        semantic = await analyze_message_semantics(message)
        return semantic.dict() if semantic else None

    @staticmethod
    def route(
        message: str,
        user: Any,
        semantic: dict[str, Any],
        requested_model: str | None = None,
        force_local: bool = False,
        stream: bool = False,
    ):
        """Mesajı uygun hedefe yönlendirir."""
        active_persona = getattr(user, "active_persona", "standard") if user else "standard"

        decision = route_message(
            message=message,
            user=user,
            persona_name=active_persona,
            requested_model=requested_model,
            force_local=force_local,
            semantic=semantic,
        )

        # Loglama
        logger.info(
            f"[ROUTER] User: {getattr(user, 'username', 'anon')} | Persona: {active_persona} | "
            f"Target: {decision.target.value} | "
            f"Tool: {decision.tool_intent.value} | "
            f"Reasons: {decision.reason_codes} | "
            f"Censorship: {decision.censorship_level} | Stream: {stream}"
        )

        return decision

    @staticmethod
    async def prepare_internet_search(message: str, semantic: dict[str, Any]) -> dict[str, Any]:
        """İnternet araması için sorguları hazırlar."""
        queries = await build_search_queries_async(message, semantic)
        return {"internet": {"queries": queries}}


# Global instance
router_service = RouterService()
