import redis.asyncio as aioredis
from app.settings import settings


redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True
)

def get_redis_client() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)