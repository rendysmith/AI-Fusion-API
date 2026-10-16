"""Kie AI provider for Sora and Veo video generation (legacy)."""

import asyncio
import json
import logging
import random
import time
from typing import Dict, List, Final

import aiohttp

from app.database.repositories.circuit_breaker_repository import (
    CircuitBreakerRepository,
)
from app.services.s3_uploader import S3UploaderService, S3UploadServiceError
from app.settings import settings

API_BASE_URL_KIE_AI = "https://api.kie.ai"
POLL_TOTAL_TIMEOUT_SECONDS = 600
POLL_INTERVAL_SECONDS = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

MODELS_MAP_VEO_KIE: Final[Dict[str, str]] = {
    "veo-3-quality": "veo3",
    "veo-3-fast": "veo3_fast",
}


class KieAiGenerationError(Exception):
    """Base error for Kie AI generation."""

    pass


class SoraGenerationError(KieAiGenerationError):
    """Sora-specific generation error."""

    pass


class VeoGenerationError(KieAiGenerationError):
    """Veo-specific generation error."""

    pass


async def _make_request_with_retry(request_func, *args, **kwargs):
    """Make an HTTP request with exponential backoff retry."""
    max_retries = 5
    base_delay = 1.0
    last_exception = None

    for attempt in range(max_retries):
        try:
            if "timeout" not in kwargs:
                kwargs["timeout"] = aiohttp.ClientTimeout(total=60)

            response = await request_func(*args, **kwargs)
            response.raise_for_status()
            return response
        except (
            aiohttp.ClientConnectorError,
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
        ) as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(
                    f"Connection error ({type(e).__name__}): {e}. "
                    f"Retry #{attempt + 2} in {delay:.2f}s...",
                )
                await asyncio.sleep(delay)
            else:
                logging.error(
                    f"Failed to connect after {max_retries} attempts.",
                )
                raise KieAiGenerationError(
                    "Failed to connect after multiple attempts.",
                ) from last_exception
        except aiohttp.ClientResponseError as e:
            if e.status in [500, 502, 503, 504] and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(
                    f"Server error {e.status}. Retrying...",
                )
                await asyncio.sleep(delay)
                continue
            else:
                raise e
    return None
