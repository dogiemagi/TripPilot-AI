import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("trippilot.fallback")


class ModelFallbackHandler:
    @staticmethod
    async def execute_with_fallback(
        primary_fn: Callable[[], Coroutine[Any, Any, Any]],
        fallback_fn: Callable[[], Coroutine[Any, Any, Any]],
        task_name: str = "inference_task",
    ) -> Any:
        try:
            return await primary_fn()
        except Exception as e:
            logger.warning("Primary provider failed for %s (%s). Executing fallback.", task_name, str(e))
            return await fallback_fn()
