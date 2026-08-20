import time
from typing import Any


class CacheService:
    _cache: dict[str, tuple[float, Any]] = {}

    @classmethod
    def get(cls, key: str) -> Any | None:
        if key in cls._cache:
            expiry, value = cls._cache[key]
            if time.time() < expiry:
                return value
            del cls._cache[key]
        return None

    @classmethod
    def set(cls, key: str, value: Any, ttl_seconds: int = 300) -> None:
        cls._cache[key] = (time.time() + ttl_seconds, value)

    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()
