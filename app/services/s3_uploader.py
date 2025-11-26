import logging
import mimetypes

import aiohttp
import aiobotocore.client
from app.settings import settings


logger = logging.getLogger(__name__)


class S3UploadServiceError(Exception):
    """Кастомная ошибка для этого сервиса"""
    pass


class S3UploaderService:

    def __init__(self, s3_client: aiobotocore.client.BaseClient):
        self.s3_client = s3_client

    async def download_and_upload_video(
            self,
            session: aiohttp.ClientSession,
            source_url: str,
            task_id: str
    ) -> str:

        try:
            logger.info(f"TaskID: {task_id} | Скачиваю видео с {source_url}...")

            async with session.get(source_url, ssl=False) as response:
                if response.status != 200:
                    raise Exception(f"Provider returned {response.status}")

                video_data = await response.read()
                content_type = response.headers.get("Content-Type", "video/mp4")


            extension = mimetypes.guess_extension(content_type) or ".mp4"

            bucket_name = settings.YANDEX_BUCKET_NAME

            s3_key = f"videos/{task_id}{extension}"

            logger.info(f"TaskID: {task_id} | Загружаю в S3 ({len(video_data)} bytes)...")

            await self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=video_data,
                ContentType=content_type,
            )


            permanent_url = f"{settings.YANDEX_STORAGE_ENDPOINT}/{bucket_name}/{s3_key}"

            logger.info(f"TaskID: {task_id} | Успешно сохранено: {permanent_url}")
            return permanent_url

        except Exception as e:
            logger.error(f"TaskID: {task_id} | Ошибка S3 Proxy: {e}")

            return source_url