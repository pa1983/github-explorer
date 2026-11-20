import logging
from time import monotonic
from typing import TypeVar, Generic

logger = logging.getLogger("github_explorer.cache")

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Generic time-to-live (TTL) cache with max size limit."""

    def __init__(self, ttl_seconds: int, max_size: int):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        """Get a value from cache if it exists and hasn't expired."""
        cached = self._cache.get(key)
        if cached is not None:
            expires_at, value = cached
            if monotonic() < expires_at:
                logger.debug(f"Cache hit for key: {key}")
                return value
            logger.debug(f"Cache miss for key: {key} (expired)")
            self._cache.pop(key)
        else:
            logger.debug(f"Cache miss for key: {key} (not found)")
        return None

    def set(self, key: str, value: T) -> None:
        """Set a value in cache with expiration time."""
        self._cache[key] = (monotonic() + self.ttl_seconds, value)
        logger.debug(f"Cached key: {key} (TTL: {self.ttl_seconds}s, size: {len(self._cache)}/{self.max_size})")
        if len(self._cache) > self.max_size:
            evicted = next(iter(self._cache))
            self._cache.pop(evicted)
            logger.debug(f"Cache evicted: {evicted}")
