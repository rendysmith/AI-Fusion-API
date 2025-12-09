import redis.asyncio as aioredis
from typing import Optional
from app.settings import settings


class CircuitBreakerRepository:

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    def _get_key(self, model_name: str) -> str:
        return f"circuit:kie_ai:{model_name}:open"

    def _get_error_key(self, model_name: str) -> str:
        return f"circuit:kie_ai:{model_name}:last_error"

    async def trip(self, model_name: str, error_msg: Optional[str] = None):
        """Разрывает цепь и сохраняет причину."""
        ttl = settings.CIRCUIT_BREAKER_TTL

        await self.redis.setex(
            self._get_key(model_name),
            ttl,
            "true"
        )


        if error_msg:
            clean_msg = str(error_msg)[:500]
            await self.redis.setex(
                self._get_error_key(model_name),
                ttl,
                clean_msg
            )

    async def is_open(self, model_name: str) -> bool:
        return await self.redis.exists(self._get_key(model_name))

    async def get_last_error(self, model_name: str) -> str:
        """Возвращает текст ошибки, из-за которой цепь разорвалась."""
        val = await self.redis.get(self._get_error_key(model_name))
        if val:
            return val.decode("utf-8") if isinstance(val, bytes) else val
        return "Неизвестная причина (нет данных)"

    async def reset(self, model_name: str):
        await self.redis.delete(self._get_key(model_name))
        await self.redis.delete(self._get_error_key(model_name))