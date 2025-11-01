import logging
from typing import Dict
import aiohttp
from app.services.s3_uploader import S3UploaderService, S3UploadServiceError
from app.settings import settings



logger = logging.getLogger(__name__)


class OpenAIGenerationError(Exception):
    pass


async def generate_sora_openai_video(
        session: aiohttp.ClientSession,
        params: Dict,
        s3_uploader: S3UploaderService,
        task_id: str,
        **kwargs
) -> Dict:
    logger.warning(f"TaskID: {task_id} | FALLBACK: Используется OpenAI.")

    pass

    try:

        placeholder_url = "https://cdn.pixabay.com/video/2024/05/20/212628_large.mp4"

        permanent_s3_url = await s3_uploader.download_and_upload_video(
            session=session,
            source_url=placeholder_url,
            task_id=task_id
        )
        return {"video_url": permanent_s3_url}

    except Exception as e:
        logger.error(f"TaskID: {task_id} | FALLBACK: Ошибка OpenAI или S3: {e}")
        raise OpenAIGenerationError(f"Ошибка в Fallback-провайдере: {e}")