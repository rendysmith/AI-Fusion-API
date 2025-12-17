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

    async def _generic_upload(
            self,
            session: aiohttp.ClientSession,
            source_url: str,
            task_id: str,
            folder: str,
            default_ext: str,
            default_content_type: str
    ) -> str:
        try:
            logger.info(f"TaskID: {task_id} | Скачиваю файл с {source_url}...")

            async with session.get(source_url, ssl=False) as response:
                if response.status != 200:
                    raise Exception(f"Provider returned {response.status}")

                file_data = await response.read()
                content_type = response.headers.get("Content-Type", default_content_type)

            extension = mimetypes.guess_extension(content_type) or default_ext

            bucket_name = settings.YANDEX_BUCKET_NAME

            # Формируем путь: folder/task_id.ext
            s3_key = f"{folder}/{task_id}{extension}"

            logger.info(f"TaskID: {task_id} | Загружаю в S3 ({len(file_data)} bytes) в {folder}...")

            await self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
            )

            permanent_url = f"{settings.YANDEX_STORAGE_ENDPOINT}/{bucket_name}/{s3_key}"

            logger.info(f"TaskID: {task_id} | Успешно сохранено: {permanent_url}")
            return permanent_url

        except Exception as e:
            logger.error(f"TaskID: {task_id} | Ошибка S3 Proxy: {e}")
            # Если не удалось загрузить в S3, возвращаем исходный URL, чтобы задача не упала
            return source_url


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


    async def download_and_upload_image(
            self,
            session: aiohttp.ClientSession,
            source_url: str,
            task_id: str
    ) -> str:
        return await self._generic_upload(
            session=session,
            source_url=source_url,
            task_id=task_id,
            folder="images",  # Сохраняем в отдельную папку
            default_ext=".png",
            default_content_type="image/png"
        )

    async def upload_file(self, file_data: bytes, key: str, content_type: str) -> str:
        """
        Загружает байты напрямую в S3 (для админки и генерации превью).
        """
        bucket_name = settings.YANDEX_BUCKET_NAME

        try:
            await self.s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type,
            )

            return f"{settings.YANDEX_STORAGE_ENDPOINT}/{bucket_name}/{key}"

        except Exception as e:
            logger.error(f"S3 Direct Upload Error: {e}")
            raise S3UploadServiceError(f"Failed to upload file to S3: {e}")