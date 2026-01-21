import json
import redis
import logging
from app.config import get_settings
from app.schemas.rdr import TelemetryEvent, EventType
from app.core.telemetry import context

logger = logging.getLogger("atlas.telemetry")

class TelemetryService:
    """
    Central Telemetry Service for Atlas & Mami AI.
    Handles event emission to logs and Redis Pub/Sub for real-time monitoring (RDR).
    """
    _instance = None
    _redis = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                settings = get_settings()
                # Use RDR dedicated Redis DB (3)
                cls._redis = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB_RDR,
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Telemetry Redis connection failed: {e}")
        return cls._instance

    def emit(self, event_type: EventType, data: dict, component: str = "system", trace_id: str = None):
        """
        Emits a telemetry event.
        
        Args:
            event_type: The category of the event (routing, llm, error, etc.)
            data: Arbitrary dictionary containing event details.
            component: The module/service originating the event.
            trace_id: Optional trace ID. If omitted, it will be pulled from context.
        """
        if not trace_id:
            trace_id = context.get_trace_id()

        try:
            event = TelemetryEvent(
                trace_id=trace_id,
                type=event_type,
                component=component,
                data=data
            )

            # 1. Structured Logging (Console/File)
            logger.info(f"[RDR] {event.model_dump_json()}")

            # 2. Redis Pub/Sub (Real-time dashboard / UI)
            if self._redis:
                try:
                    self._redis.publish("atlas_live_events", event.model_dump_json())
                except Exception as e:
                    logger.error(f"Redis publish error: {e}")
        
        except Exception as e:
            # Prevent telemetry failures from crashing the main application
            logger.error(f"Critical error in telemetry emission: {e}")

# Global Singleton Instance
telemetry = TelemetryService()
