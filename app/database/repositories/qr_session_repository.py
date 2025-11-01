import redis.asyncio as aioredis
import json


class QrSessionRepository:

    SESSION_TTL = 300

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    def _get_key(self, session_id: str) -> str:

        return f"qr_session:{session_id}"

    async def create_session(self, session_id: str):

        key = self._get_key(session_id)
        session_data = {"status": "pending", "token": None}

        await self.redis.setex(key, self.SESSION_TTL, json.dumps(session_data))

    async def get_session_status(self, session_id: str) -> dict | None:

        key = self._get_key(session_id)
        data = await self.redis.get(key)

        if not data:
            return None

        return json.loads(data)

    async def complete_session(self, session_id: str, token: str):

        key = self._get_key(session_id)
        session_data = {"status": "completed", "token": token}

        await self.redis.setex(key, self.SESSION_TTL, json.dumps(session_data))

    async def delete_session(self, session_id: str):

        key = self._get_key(session_id)
        await self.redis.delete(key)