"""Tiny in-process TTL cache for transcript list queries.

Safe here because the app runs as a single instance; entries are dropped on
every write and expire after TTL as a safety net for out-of-band DB edits.
For multiple instances, replace with Redis (same get/set/invalidate interface).
"""
import threading
import time
from collections.abc import Hashable
from typing import Any


class TTLCache:
    def __init__(self, ttl: float = 60.0, max_entries: int = 200):
        self._ttl = ttl
        self._max = max_entries
        self._data: dict[Hashable, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            hit = self._data.get(key)
            if not hit:
                return None
            expires, value = hit
            if expires < time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self._max:
                self._data.clear()
            self._data[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self) -> None:
        with self._lock:
            self._data.clear()


list_cache = TTLCache()
