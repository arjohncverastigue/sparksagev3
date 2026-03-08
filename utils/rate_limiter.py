"""Token-bucket rate limiter for per-user and per-guild quota management."""

import time
from collections import defaultdict
from typing import Dict, Tuple


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, capacity: float, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens in the bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def try_consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens. Returns True if successful, False if rate limited."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_remaining(self) -> float:
        """Get remaining tokens (after refill)."""
        self._refill()
        return self.tokens

    def _refill(self):
        """Refill bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity, self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now


class RateLimiter:
    """Rate limiter that tracks per-user and per-guild quotas."""

    def __init__(self, user_rate: float, guild_rate: float):
        """
        Args:
            user_rate: requests per minute per user
            guild_rate: requests per minute per guild
        """
        # Convert requests/minute to tokens/second
        self.user_capacity = user_rate
        self.user_refill = user_rate / 60.0
        self.guild_capacity = guild_rate
        self.guild_refill = guild_rate / 60.0

        self.user_buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.user_capacity, self.user_refill)
        )
        self.guild_buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.guild_capacity, self.guild_refill)
        )

    def update_capacities(self, user_rate: float, guild_rate: float):
        """
        Updates the user and guild rate limit capacities and refill rates.
        Existing TokenBuckets retain their state until naturally refilled,
        but any new TokenBuckets will use the updated capacities.
        """
        self.user_capacity = user_rate
        self.user_refill = user_rate / 60.0
        self.guild_capacity = guild_rate
        self.guild_refill = guild_rate / 60.0

        # Update the factory functions for defaultdicts to use new capacities
        self.user_buckets.default_factory = lambda: TokenBucket(self.user_capacity, self.user_refill)
        self.guild_buckets.default_factory = lambda: TokenBucket(self.guild_capacity, self.guild_refill)

        # Update existing buckets as well
        for bucket in self.user_buckets.values():
            bucket.capacity = self.user_capacity
            bucket.refill_rate = self.user_refill
            bucket.tokens = min(bucket.tokens, bucket.capacity) # Cap tokens to new capacity

        for bucket in self.guild_buckets.values():
            bucket.capacity = self.guild_capacity
            bucket.refill_rate = self.guild_refill
            bucket.tokens = min(bucket.tokens, bucket.capacity) # Cap tokens to new capacity

    def is_allowed(self, user_id: str, guild_id: str | None = None) -> Tuple[bool, str]:
        """
        Check if a request is allowed.

        Returns:
            (allowed: bool, reason: str)
        """
        # Check user limit
        user_bucket = self.user_buckets[user_id]
        if not user_bucket.try_consume():
            remaining = user_bucket.get_remaining()
            return (
                False,
                f"User rate limit exceeded. Reset in ~{int(self.user_capacity / self.user_refill - remaining / self.user_refill)}s",
            )

        # Check guild limit (if guild_id provided)
        if guild_id:
            guild_bucket = self.guild_buckets[guild_id]
            if not guild_bucket.try_consume():
                remaining = guild_bucket.get_remaining()
                return (
                    False,
                    f"Server rate limit exceeded. Reset in ~{int(self.guild_capacity / self.guild_refill - remaining / self.guild_refill)}s",
                )

        return True, "OK"

    def get_user_quota(self, user_id: str) -> Dict[str, float]:
        """Get remaining quota for a user."""
        bucket = self.user_buckets[user_id]
        remaining = bucket.get_remaining()
        return {
            "user_id": user_id,
            "remaining": remaining,
            "capacity": self.user_capacity,
            "reset_in_seconds": max(
                0, (self.user_capacity - remaining) / self.user_refill
            ),
        }

    def get_guild_quota(self, guild_id: str) -> Dict[str, float]:
        """Get remaining quota for a guild."""
        bucket = self.guild_buckets[guild_id]
        remaining = bucket.get_remaining()
        return {
            "guild_id": guild_id,
            "remaining": remaining,
            "capacity": self.guild_capacity,
            "reset_in_seconds": max(
                0, (self.guild_capacity - remaining) / self.guild_refill
            ),
        }

    def get_all_quotas(self) -> Dict[str, Dict]:
        """Get all tracked quotas."""
        return {
            "users": {
                user_id: self.get_user_quota(user_id)
                for user_id in self.user_buckets.keys()
            },
            "guilds": {
                guild_id: self.get_guild_quota(guild_id)
                for guild_id in self.guild_buckets.keys()
            },
        }
