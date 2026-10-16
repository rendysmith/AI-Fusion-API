"""Unifically provider for Sora-2 video generation (fallback)."""

import asyncio
import logging
import time
from typing import Final, Optional

import aiohttp

from app.exceptions import UserValidationError, FatalProviderError
from app.settings import settings
from app.services.s3_uploader import S3UploaderService

logging.basicConfig(level=logging.INFO)

SORA_GENERATE_URL: Final[str] = (
    "https://api.unifically.com/sora-2/generate"
)
SORA_FEED_URL: Final[str] = (
    "https://api.unifically.com/sora-2/status"
)

SORA_POST_MAX_RETRIES: Final[int] = 3
SORA_POST_RETRY_DELAY: Final[int] = 5
SORA_POLLING_INTERVAL: Final[int] = 20
SORA_POLLING_TIMEOUT: Final[int] = 900

API_UNIFICALLY_TOKEN = settings.API_UNIFICALLY_TOKEN


class SoraError(Exception):
    """Custom error for Sora generation."""

    pass


async def _start_sora_task(
    session: aiohttp.ClientSession,
    prompt: str,
    aspect_ratio: Optional[str] = None,
    duration: Optional[int] = None,
    image_url: Optional[str] = None,
    seed: Optional[int] = None,
) -> str:
    """Start a Sora generation task and return the task ID."""
    headers = {
        "Authorization": f"Bearer {API_UNIFICALLY_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {"prompt": prompt}
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if duration:
        payload["duration"] = duration
    if image_url:
        payload["image_url"] = image_url
    if seed:
        payload["seed"] = seed

    logging.info(f"SORA: Starting generation. Payload: {payload}")

    for attempt in range(SORA_POST_MAX_RETRIES):
        try:
            logging.info(
                f"Attempt {attempt + 1}/{SORA_POST_MAX_RETRIES} "
                f"POST {SORA_GENERATE_URL}",
            )
            async with session.post(
                SORA_GENERATE_URL, headers=headers, json=payload, ssl=False,
            ) as resp:
                if resp.status == 400:
                    try:
                        error_data = await resp.json()
                        error_message = (
                            error_data.get("data", {})
                            .get("error", {})
                            .get("message", str(error_data))
                        )
                    except Exception:
                        error_message = await resp.text()

                    raise UserValidationError(
                        f"Unifically 400: {error_message}",
                    )

                if resp.status >= 500:
                    raise FatalProviderError(
                        f"Unifically Server Error: {resp.status}",
                    )

                resp.raise_for_status()
                response_data = await resp.json()

                api_task_id = response_data.get("data", {}).get("task_id")
                if not api_task_id:
                    raise SoraError(
                        "API returned 'data' but 'task_id' is missing.",
                    )

                logging.info(
                    f"SORA: Got task_id: {api_task_id}",
                )
                return api_task_id

        except aiohttp.ClientResponseError as e:
            if (
                e.status in [500, 502, 503, 504, 524]
                and attempt < SORA_POST_MAX_RETRIES - 1
            ):
                logging.warning(
                    f"SORA: Server error ({e.status}) on attempt "
                    f"{attempt + 1}. Retrying in {SORA_POST_RETRY_DELAY}s...",
                )
                await asyncio.sleep(SORA_POST_RETRY_DELAY)
                continue

            raise FatalProviderError(f"Unifically Network Error: {e}")

        except UserValidationError:
            raise
        except Exception as e:
            raise FatalProviderError(f"Unifically Unexpected Error: {e}")

    raise FatalProviderError("Unifically failed to start task after retries")


async def _poll_sora_result(
    session: aiohttp.ClientSession, api_task_id: str,
) -> str:
    """Poll for Sora generation result until completion."""
    headers = {"Authorization": f"Bearer {API_UNIFICALLY_TOKEN}"}

    feed_url = f"{SORA_FEED_URL}/{api_task_id}"
    start_time = time.time()

    while time.time() - start_time < SORA_POLLING_TIMEOUT:
        try:
            logging.info(
                f"SORA: Polling result for task_id: {api_task_id}...",
            )
            async with session.get(
                feed_url, headers=headers, ssl=False,
            ) as resp:
                if resp.status == 400:
                    try:
                        error_data = await resp.json()
                        error_message = (
                            error_data.get("data", {})
                            .get("error", {})
                            .get(
                                "message",
                                "API returned 400 without error message",
                            )
                        )
                    except Exception:
                        error_message = await resp.text()

                    logging.error(
                        f"SORA: API 400 for task {api_task_id}: "
                        f"{error_message}",
                    )
                    raise UserValidationError(
                        f"Unifically Poll 400: {error_message}",
                    )

                if resp.status in [500, 502, 503, 504, 524]:
                    logging.warning(
                        f"SORA: Server error ({resp.status}) polling. "
                        f"Retrying...",
                    )
                    await asyncio.sleep(SORA_POLLING_INTERVAL)
                    continue

                if resp.status != 200:
                    resp.raise_for_status()

                response_data = await resp.json()
                data_block = response_data.get("data", {})

                logging.info(response_data)

                status = data_block.get("status")

                if status == "failed":
                    error_info = data_block.get("error", {})
                    error_message = (
                        error_info.get("message", "Unknown").lower()
                    )

                    if any(
                        x in error_message
                        for x in ["nsfw", "policy", "safety", "moderation"]
                    ):
                        raise UserValidationError(
                            f"Unifically Safety: {error_message}",
                        )

                    raise FatalProviderError(
                        f"Unifically Task Failed: {error_message}",
                    )

                if status == "completed":
                    output = data_block.get("output", {})
                    video_url = output.get("video_url")
                    if video_url:
                        logging.info(
                            f"SORA: Got result for task {api_task_id}.",
                        )
                        return video_url
                    else:
                        raise SoraError(
                            "SORA: Status 'completed' but no 'video_url'.",
                        )

                logging.info(
                    f"SORA: Task {api_task_id} in progress "
                    f"(status: {status}). Waiting...",
                )
                await asyncio.sleep(SORA_POLLING_INTERVAL)

        except (UserValidationError, FatalProviderError):
            raise
        except Exception as e:
            logging.error(
                f"SORA: Unexpected error polling task "
                f"{api_task_id}: {e}",
                exc_info=True,
            )
            await asyncio.sleep(SORA_POLLING_INTERVAL)

    raise FatalProviderError(
        f"Unifically Polling Timeout ({SORA_POLLING_TIMEOUT}s)",
    )


async def generate_sora_video(
    session: aiohttp.ClientSession,
    params: dict,
    task_id: str,
    s3_uploader: S3UploaderService,
    model_name: str = "sora-2",
    **kwargs,
) -> dict:
    """Generate a Sora video via Unificantly provider (fallback)."""
    logging.info(
        f"InternalTaskID: {task_id} | "
        f"generate_sora_video with params: {params}",
    )

    if "prompt" not in params:
        raise ValueError("Parameter 'prompt' is required for SORA.")

    try:
        prompt = params["prompt"]
        aspect_ratio = params.get("aspect_ratio", "16:9")
        duration = params.get("duration")
        image_url = params.get("image_url")
        seed = params.get("seed")

        api_task_id = await _start_sora_task(
            session=session,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration=duration,
            image_url=image_url,
            seed=seed,
        )

        logging.info(
            f"InternalTaskID: {task_id} | "
            f"SORA API TaskID: {api_task_id} | Polling result...",
        )

        temp_video_url = await _poll_sora_result(session, api_task_id)

        permanent_url = await s3_uploader.download_and_upload_video(
            session=session,
            source_url=temp_video_url,
            task_id=task_id,
        )

        return {"video_url": permanent_url}

    except (UserValidationError, FatalProviderError):
        raise
    except Exception as e:
        raise FatalProviderError(f"Unifically Critical: {e}")
