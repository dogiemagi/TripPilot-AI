import json
import logging
import time
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("trippilot.observability")


class ObservabilityService:
    _metrics = {
        "total_requests": 0,
        "total_errors": 0,
        "total_fallbacks": 0,
        "latencies_ms": [],
        "intent_distribution": {},
    }

    @classmethod
    def log_event(
        cls,
        event_name: str,
        request_id: str,
        user_id: str,
        intent: str | None = None,
        confidence: float | None = None,
        model_used: str | None = None,
        latency_ms: float | None = None,
        status: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        cls._metrics["total_requests"] += 1
        if status != "success":
            cls._metrics["total_errors"] += 1
        if latency_ms:
            cls._metrics["latencies_ms"].append(latency_ms)
            if len(cls._metrics["latencies_ms"]) > 500:
                cls._metrics["latencies_ms"].pop(0)

        if intent:
            cls._metrics["intent_distribution"][intent] = (
                cls._metrics["intent_distribution"].get(intent, 0) + 1
            )

        log_payload = {
            "event": event_name,
            "request_id": request_id,
            "user_id": user_id,
            "intent": intent,
            "confidence": confidence,
            "model_used": model_used,
            "latency_ms": latency_ms,
            "status": status,
            "metadata": metadata or {},
        }
        logger.info(json.dumps(log_payload))

    @classmethod
    def get_metrics_summary(cls) -> dict[str, Any]:
        latencies = cls._metrics["latencies_ms"]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        return {
            "total_requests": cls._metrics["total_requests"],
            "total_errors": cls._metrics["total_errors"],
            "total_fallbacks": cls._metrics["total_fallbacks"],
            "average_latency_ms": round(avg_lat, 2),
            "intent_distribution": cls._metrics["intent_distribution"],
        }
