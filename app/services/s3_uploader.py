import logging
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

            async with session.get(source_url, ssl=False, timeout=300) as response:
                response.raise_for_status()
                video_data = await response.read()

            if not video_data:
                raise S3UploadServiceError("Скачанный файл видео пустой.")


            bucket_name = settings.YANDEX_BUCKET_NAME
            s3_key = f"videos/{task_id}.mp4"


            await self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=video_data,
                ContentType='video/mp4',
                ACL='public-read'
            )

            permanent_url = f"{settings.YANDEX_STORAGE_ENDPOINT}/{bucket_name}/{s3_key}"

            return permanent_url

        except aiohttp.ClientError as e:
            logger.error(f"TaskID: {task_id} | S3Uploader: Ошибка скачивания: {e}", exc_info=True)
            raise S3UploadServiceError(f"Ошибка скачивания видео: {e}")
        except Exception as e:
            logger.error(f"TaskID: {task_id} | S3Uploader: Ошибка загрузки в S3: {e}", exc_info=True)
            raise S3UploadServiceError(f"Ошибка S3: {e}")