"""Vision-RCP Rate Limiter — Token bucket per-connection rate limiting."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("rcp.rate_limiter")


@dataclass
class TokenBucket:
    """Token bucket rate limiter for a single connection."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        self.tokens = float(self.capacity)

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed, False if rate limited."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def remaining(self) -> int:
        self._refill()
        return int(self.tokens)


class RateLimiter:
    """Manages per-connection rate limiting."""

    def __init__(self, commands_per_minute: int = 120, burst: int = 20,
                 auth_attempts_per_minute: int = 5):
        self._commands_per_minute = commands_per_minute
        self._burst = burst
        self._auth_per_minute = auth_attempts_per_minute
        self._buckets: dict[str, TokenBucket] = {}
        self._auth_buckets: dict[str, TokenBucket] = {}
        self._relay_bucket: Optional[TokenBucket] = None

    def _get_bucket(self, connection_id: str) -> TokenBucket:
        if connection_id.startswith("relay:"):
            if not self._relay_bucket:
                # Relay gets 10x the standard burst and 5x the refill rate
                # to handle multiple clients aggregated into one stream.
                self._relay_bucket = TokenBucket(
                    capacity=self._burst * 10,
                    refill_rate=(self._commands_per_minute * 5) / 60.0,
                )
            return self._relay_bucket

        if connection_id not in self._buckets:
            self._buckets[connection_id] = TokenBucket(
                capacity=self._burst,
                refill_rate=self._commands_per_minute / 60.0,
            )
        return self._buckets[connection_id]

    def _get_auth_bucket(self, source_ip: str) -> TokenBucket:
        if source_ip not in self._auth_buckets:
            self._auth_buckets[source_ip] = TokenBucket(
                capacity=self._auth_per_minute,
                refill_rate=self._auth_per_minute / 60.0,
            )
        return self._auth_buckets[source_ip]

    def check_command(self, connection_id: str) -> bool:
        """Check if a command is allowed for this connection."""
        bucket = self._get_bucket(connection_id)
        allowed = bucket.consume()
        if not allowed:
            logger.warning("Rate limit exceeded for connection %s", connection_id)
        return allowed

    def check_auth(self, source_ip: str) -> bool:
        """Check if an auth attempt is allowed from this IP."""
        # Whitelist localhost for development convenience
        if source_ip in ("127.0.0.1", "::1", "localhost"):
            return True
            
        bucket = self._get_auth_bucket(source_ip)
        allowed = bucket.consume()
        if not allowed:
            logger.warning("Auth rate limit exceeded for IP %s", source_ip)
        return allowed

    def remove_connection(self, connection_id: str) -> None:
        """Clean up buckets when a connection closes."""
        self._buckets.pop(connection_id, None)

    def get_remaining(self, connection_id: str) -> int:
        """Get remaining tokens for a connection."""
        if connection_id in self._buckets:
            return self._buckets[connection_id].remaining
        return self._burst
