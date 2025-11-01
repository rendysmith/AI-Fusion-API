import redis.asyncio as aioredis
from app.settings import settings


class CircuitBreakerRepository:

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    def _get_key(self, model_name: str) -> str:

        return f"circuit:kie_ai:{model_name}:open"

    async def trip(self, model_name: str):
        await self.redis.setex(
            self._get_key(model_name),
            settings.CIRCUIT_BREAKER_TTL,
            "true"
        )


    async def is_open(self, model_name: str) -> bool:
        return await self.redis.exists(self._get_key(model_name))

    async def reset(self, model_name: str):
        await self.redis.delete(self._get_key(model_name))