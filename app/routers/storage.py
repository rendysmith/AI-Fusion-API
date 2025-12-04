from urllib.parse import urlparse
import logging
from fastapi import APIRouter, Query, Request
from app.settings import settings

router = APIRouter(prefix="/storage", tags=["Storage"])
logger = logging.getLogger(__name__)


@router.get("/download-link")
async def get_download_link(
        request: Request,
        url: str = Query(..., description="Исходная публичная ссылка на видео")
):
    """
    Генерирует временную ссылку (Presigned URL), которая заставляет браузер
    скачать файл, а не открывать его.
    """
    try:

        if settings.YANDEX_STORAGE_ENDPOINT not in url and settings.YANDEX_BUCKET_NAME not in url:

            return {"download_url": url}


        parsed = urlparse(url)
        path = parsed.path.lstrip('/')


        if path.startswith(settings.YANDEX_BUCKET_NAME + "/"):
            key = path.replace(settings.YANDEX_BUCKET_NAME + "/", "", 1)
        else:
            key = path


        filename = key.split('/')[-1]
        if not filename:
            filename = "video.mp4"


        s3_client = request.app.state.s3_client

        presigned_url = await s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.YANDEX_BUCKET_NAME,
                'Key': key,
                'ResponseContentDisposition': f'attachment; filename="{filename}"'
            },
            ExpiresIn=3600
        )

        return {"download_url": presigned_url}

    except Exception as e:
        logger.error(f"Error generating download link: {e}")
        return {"download_url": url}