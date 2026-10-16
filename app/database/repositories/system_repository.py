"""System-level repository for maintenance mode and global state."""

import redis.asyncio as aioredis
from typing import Optional


class SystemRepository:
    """Repository for system-wide state management in Redis."""

    MAINTENANCE_KEY = "global:maintenance_mode"
    MAINTENANCE_MESSAGE_KEY = "global:maintenance_message"

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def set_maintenance_mode(
        self, enabled: bool, message: Optional[str] = None,
    ):
        """Enable or disable maintenance mode."""
        if enabled:
            await self.redis.set(self.MAINTENANCE_KEY, "true")
            if message:
                await self.redis.set(self.MAINTENANCE_MESSAGE_KEY, message)
        else:
            await self.redis.delete(self.MAINTENANCE_KEY)
            await self.redis.delete(self.MAINTENANCE_MESSAGE_KEY)

    async def is_maintenance_mode(self) -> tuple[bool, str]:
        """Check if maintenance mode is active."""
        is_enabled = await self.redis.exists(self.MAINTENANCE_KEY)
        if not is_enabled:
            return False, ""

        message = await self.redis.get(self.MAINTENANCE_MESSAGE_KEY)

        if message:
            msg_str = message.decode("utf-8") if isinstance(message, bytes) else message
        else:
            msg_str = "Ведутся технические работы. Пожалуйста, попробуйте позже."

        return True, msg_str
