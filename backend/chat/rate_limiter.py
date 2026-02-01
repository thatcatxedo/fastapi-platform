"""
Rate limiting for chat feature.
Uses sliding window algorithm with MongoDB for persistence.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple

from database import rate_limits_collection
from config import CHAT_RATE_LIMIT_PER_MINUTE, CHAT_RATE_LIMIT_PER_HOUR


class ChatRateLimiter:
    """Rate limiter for chat messages using sliding window algorithm."""

    def __init__(self, per_minute: int, per_hour: int):
        self.per_minute = per_minute
        self.per_hour = per_hour

    async def check_rate_limit(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user is within rate limits.

        Returns:
            Tuple of (allowed, error_message)
            - allowed: True if request should proceed
            - error_message: None if allowed, otherwise the rate limit error
        """
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        doc = await rate_limits_collection.find_one({"user_id": user_id})
        if not doc:
            return True, None

        timestamps = doc.get("message_timestamps", [])

        # Count messages in windows
        minute_count = sum(1 for ts in timestamps if ts > minute_ago)
        hour_count = sum(1 for ts in timestamps if ts > hour_ago)

        if minute_count >= self.per_minute:
            wait_seconds = 60 - (now - min(ts for ts in timestamps if ts > minute_ago)).seconds
            return False, f"Rate limit exceeded. Please wait {wait_seconds}s ({self.per_minute} messages/minute)"

        if hour_count >= self.per_hour:
            return False, f"Hourly rate limit exceeded ({self.per_hour} messages/hour)"

        return True, None

    async def record_message(self, user_id: str):
        """Record a message timestamp for rate limiting."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)

        # Upsert: add timestamp, prune old ones, update timestamp for TTL
        await rate_limits_collection.update_one(
            {"user_id": user_id},
            {
                "$push": {"message_timestamps": now},
                "$set": {"updated_at": now}
            },
            upsert=True
        )

        # Clean up old timestamps (older than 1 hour)
        await rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$pull": {"message_timestamps": {"$lt": hour_ago}}}
        )

    async def get_usage(self, user_id: str) -> dict:
        """Get current usage stats for a user."""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        doc = await rate_limits_collection.find_one({"user_id": user_id})
        if not doc:
            return {
                "minute_used": 0,
                "minute_limit": self.per_minute,
                "hour_used": 0,
                "hour_limit": self.per_hour
            }

        timestamps = doc.get("message_timestamps", [])
        minute_count = sum(1 for ts in timestamps if ts > minute_ago)
        hour_count = sum(1 for ts in timestamps if ts > hour_ago)

        return {
            "minute_used": minute_count,
            "minute_limit": self.per_minute,
            "hour_used": hour_count,
            "hour_limit": self.per_hour
        }


# Singleton instance
chat_rate_limiter = ChatRateLimiter(
    per_minute=CHAT_RATE_LIMIT_PER_MINUTE,
    per_hour=CHAT_RATE_LIMIT_PER_HOUR
)
