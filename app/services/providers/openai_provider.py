"""OpenAI provider for Sora video generation (fallback)."""

import asyncio
import logging
from typing import Final

import aiohttp
from openai import AsyncOpenAI
from app.settings import settings
from app.services.s3_uploader import S3UploaderService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

POLLING_INTERVAL: Final[int] = 5
POLLING_TIMEOUT: Final[int] = 600


async def _download_image_for_reference(
    session: aiohttp.ClientSession, url: str,
) -> bytes:
    """Download an image for reference usage."""
    async with session.get(url) as resp:
        if resp.status != 200:
            raise ValueError(
                f"Failed to download image_url for reference: {resp.status}",
            )
        return await resp.read()


def _map_duration(duration: int) -> str:
    """Map duration in seconds to Sora API duration string."""
    if not duration:
        return "4"
    if duration <= 6:
        return "4"
    elif duration <= 10:
        return "8"
    else:
        return "12"


def _map_size(orientation: str) -> str:
    """Map orientation to resolution."""
    if orientation == "portrait":
        return "720x1280"
    elif orientation == "landscape":
        return "1280x720"
    else:
        return "1280x720"


async def generate_sora_openai_video(
    session: aiohttp.ClientSession,
    params: dict,
    task_id: str,
    s3_uploader: S3UploaderService,
    **kwargs,
) -> dict:
    """Generate a Sora video via OpenAI provider (fallback)."""
    logger.info(
        f"InternalTaskID: {task_id} | "
        f"generate_sora_openai_video (FALLBACK)",
    )

    try:
        prompt = params.get("prompt")
        if not prompt:
            raise ValueError("Prompt is required for OpenAI Sora generation")

        size = _map_size(params.get("orientation", "landscape"))
        seconds_str = _map_duration(params.get("duration", 4))

        create_kwargs = {
            "model": "sora-2",
            "prompt": prompt,
            "seconds": seconds_str,
            "size": size,
        }

        image_url = params.get("image_url")
        if image_url:
            logger.info(
                f"TaskID: {task_id} | Downloading reference image...",
            )
            image_bytes = await _download_image_for_reference(session, image_url)
            create_kwargs["input_reference"] = image_bytes

        logger.info(f"TaskID: {task_id} | Sending request to OpenAI...")

        video_job = await client.videos.create(**create_kwargs)
        video_id = video_job.id

        logger.info(
            f"TaskID: {task_id} | OpenAI Video ID: {video_id}. "
            f"Status: {video_job.status}",
        )

        start_time = asyncio.get_running_loop().time()

        while True:
            if asyncio.get_running_loop().time() - start_time > POLLING_TIMEOUT:
                raise TimeoutError("OpenAI generation timed out")

            job_status = await client.videos.retrieve(video_id)

            if job_status.status == "completed":
                logger.info(
                    f"TaskID: {task_id} | Generation completed. "
                    f"Downloading content...",
                )
                break
            elif job_status.status == "failed":
                error_msg = getattr(job_status, "error", "Unknown error")
                raise Exception(f"OpenAI generation failed: {error_msg}")
            else:
                await asyncio.sleep(POLLING_INTERVAL)

        logger.info(
            f"TaskID: {task_id} | "
            f"Downloading video bytes via download_content...",
        )

        response = await client.videos.download_content(video_id=video_id)
        video_bytes = response.read()

        bucket_name = settings.YANDEX_BUCKET_NAME
        s3_key = f"videos/{task_id}.mp4"

        logger.info(
            f"TaskID: {task_id} | "
            f"Uploading result ({len(video_bytes)} bytes) to S3...",
        )

        await s3_uploader.s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=video_bytes,
            ContentType="video/mp4",
        )

        permanent_url = (
            f"{settings.YANDEX_STORAGE_ENDPOINT}/{bucket_name}/{s3_key}"
        )
        logger.info(f"TaskID: {task_id} | Saved: {permanent_url}")

        return {"video_url": permanent_url}

    except Exception as e:
        logger.error(
            f"TaskID: {task_id} | OpenAI Fallback Error: {e}",
            exc_info=True,
        )
        raise e
