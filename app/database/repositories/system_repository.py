import redis.asyncio as aioredis
from typing import Optional


class SystemRepository:
    MAINTENANCE_KEY = "global:maintenance_mode"
    MAINTENANCE_MESSAGE_KEY = "global:maintenance_message"

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def set_maintenance_mode(self, enabled: bool, message: Optional[str] = None):
        if enabled:
            await self.redis.set(self.MAINTENANCE_KEY, "true")
            if message:
                await self.redis.set(self.MAINTENANCE_MESSAGE_KEY, message)
        else:
            await self.redis.delete(self.MAINTENANCE_KEY)
            await self.redis.delete(self.MAINTENANCE_MESSAGE_KEY)

    async def is_maintenance_mode(self) -> tuple[bool, str]:
        is_enabled = await self.redis.exists(self.MAINTENANCE_KEY)
        if not is_enabled:
            return False, ""

        message = await self.redis.get(self.MAINTENANCE_MESSAGE_KEY)
        msg_str = message.decode("utf-8") if message else "Ведутся технические работы. Пожалуйста, попробуйте позже."
        return True, msg_str