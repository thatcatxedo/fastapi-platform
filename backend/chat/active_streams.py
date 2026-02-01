"""
Track active streaming sessions to prevent concurrent abuse.
Uses in-memory tracking (resets on pod restart, which is fine for this use case).
"""
import asyncio
from typing import Dict

from config import CHAT_MAX_CONCURRENT_STREAMS


class ActiveStreamTracker:
    """Track active streaming sessions per user."""

    def __init__(self, max_per_user: int = 1):
        self.max_per_user = max_per_user
        self._active: Dict[str, int] = {}  # user_id -> count
        self._lock = asyncio.Lock()

    async def acquire(self, user_id: str) -> bool:
        """
        Try to acquire a stream slot for a user.

        Returns:
            True if the slot was acquired, False if limit reached
        """
        async with self._lock:
            current = self._active.get(user_id, 0)
            if current >= self.max_per_user:
                return False
            self._active[user_id] = current + 1
            return True

    async def release(self, user_id: str):
        """Release a stream slot for a user."""
        async with self._lock:
            current = self._active.get(user_id, 0)
            if current > 0:
                self._active[user_id] = current - 1
                # Clean up if no active streams
                if self._active[user_id] == 0:
                    del self._active[user_id]

    async def get_active_count(self, user_id: str) -> int:
        """Get the number of active streams for a user."""
        async with self._lock:
            return self._active.get(user_id, 0)

    async def is_available(self, user_id: str) -> bool:
        """Check if a user can start a new stream."""
        async with self._lock:
            return self._active.get(user_id, 0) < self.max_per_user


# Singleton instance
active_streams = ActiveStreamTracker(max_per_user=CHAT_MAX_CONCURRENT_STREAMS)
