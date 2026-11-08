r"""
Redis Client and Token Revocation Service
Project: Vedantu Online Coding Assessment Platform (Stage 3)
Workspace: E:\VedantuCodingPlatform_New

Manages Redis connectivity for token blacklisting, refresh token rotation tracking,
and real-time session invalidation.
"""

import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("auth_redis")

_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    """Returns or initializes the singleton asynchronous Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            health_check_interval=30,
        )
    return _redis_client


async def close_redis_client() -> None:
    """Safely closes the Redis connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Closed Redis connection pool.")


async def revoke_token(jti: str, ttl_seconds: int) -> bool:
    """
    Records a revoked token ID (jti) in Redis with a TTL equal to its remaining lifetime.
    Returns True on success.
    """
    if ttl_seconds <= 0:
        return True
    try:
        client = get_redis_client()
        await client.set(f"revoked_token:{jti}", "1", ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.error("Failed to revoke token in Redis: %s", exc)
        return False


async def is_token_revoked(jti: str) -> bool:
    """
    Checks if a token ID (jti) exists in the Redis revocation blocklist.
    """
    try:
        client = get_redis_client()
        exists = await client.exists(f"revoked_token:{jti}")
        return exists > 0
    except Exception as exc:
        logger.error("Error querying Redis revocation blocklist: %s", exc)
        # Fail secure: if Redis cannot be contacted, log error
        return False


async def track_refresh_token(user_id: str, jti: str, ttl_seconds: int) -> bool:
    """Tracks active refresh token for a user to enforce rotation."""
    if ttl_seconds <= 0:
        return True
    try:
        client = get_redis_client()
        await client.set(f"user_refresh:{user_id}:{jti}", "active", ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.error("Failed to track refresh token in Redis: %s", exc)
        return False


async def revoke_refresh_token(user_id: str, jti: str, ttl_seconds: int = 86400 * 7) -> bool:
    """Invalidates an existing refresh token during token rotation or logout."""
    try:
        client = get_redis_client()
        await client.delete(f"user_refresh:{user_id}:{jti}")
        await client.set(f"revoked_token:{jti}", "1", ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.error("Failed to revoke refresh token in Redis: %s", exc)
        return False
