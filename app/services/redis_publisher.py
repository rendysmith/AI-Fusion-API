"""Redis publisher for real-time task update notifications."""

import json
import logging
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisPublisher:
    """Publishes task completion updates to Redis pub/sub."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.channel = "task_updates"

    async def publish_completion(
        self, task_id: str, telegram_id: int, file_url: str, prompt: str,
    ):
        """Publish a video completion notification."""
        message = {
            "type": "video_completed",
            "task_id": task_id,
            "telegram_id": telegram_id,
            "file_url": file_url,
            "prompt": prompt,
        }
        await self._publish(message)

    async def publish_error(self, task_id: str, telegram_id: int, error_msg: str):
        """Publish a task failure notification."""
        message = {
            "type": "video_failed",
            "task_id": task_id,
            "telegram_id": telegram_id,
            "error": error_msg,
        }
        await self._publish(message)

    async def _publish(self, data: dict):
        """Publish a message to the Redis channel."""
        try:
            payload = json.dumps(data)
            await self.redis.publish(self.channel, payload)
            logger.info(f"Redis Pub: Sent update for task {data.get('task_id')}")
        except Exception as e:
            logger.error(f"Redis Pub Error: {e}")
