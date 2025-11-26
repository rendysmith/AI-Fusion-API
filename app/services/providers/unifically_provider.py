import asyncio
import logging
import time
from typing import Final, Optional

import aiohttp

from app.settings import settings
from app.services.s3_uploader import S3UploaderService, S3UploadServiceError
from app.database.repositories.circuit_breaker_repository import CircuitBreakerRepository

logging.basicConfig(level=logging.INFO)

SORA_GENERATE_URL: Final[str] = 'https://api.unifically.com/sora-2/generate'
SORA_FEED_URL: Final[str] = 'https://api.unifically.com/sora-2/status'

SORA_POST_MAX_RETRIES: Final[int] = 3
SORA_POST_RETRY_DELAY: Final[int] = 5
SORA_POLLING_INTERVAL: Final[int] = 20
SORA_POLLING_TIMEOUT: Final[int] = 900

orientation_dict = {
    'landscape': '16:9',
    'portrait': '9:16'
}

API_UNIFICALLY_TOKEN = settings.API_UNIFICALLY_TOKEN


class SoraError(Exception):
    pass


async def _start_sora_task(session: aiohttp.ClientSession,
                           prompt: str,
                           aspect_ratio: Optional[str] = None,
                           duration: Optional[int] = None,
                           image_url: Optional[str] = None,
                           seed: Optional[int] = None) -> str:
    headers = {
        'Authorization': f'Bearer {API_UNIFICALLY_TOKEN}',
        'Content-Type': 'application/json'
    }

    payload = {
        "prompt": prompt,
    }
    if aspect_ratio:
        payload['aspect_ratio'] = aspect_ratio
    if duration:
        payload['duration'] = duration
    if image_url:
        payload['image_url'] = image_url
    if seed:
        payload['seed'] = seed

    logging.info(f"SORA: Запуск генерации. Payload: {payload}")

    for attempt in range(SORA_POST_MAX_RETRIES):
        try:
            logging.info(f"Попытка {attempt + 1}/{SORA_POST_MAX_RETRIES} запроса генерации SORA: {SORA_GENERATE_URL}")
            async with session.post(SORA_GENERATE_URL, headers=headers, json=payload, ssl=False) as resp:
                resp.raise_for_status()
                response_data = await resp.json()

                api_task_id = response_data.get('data', {}).get('task_id')
                if not api_task_id:
                    raise SoraError("API вернул 'data', но 'task_id' в ответе отсутствует или пуст.")

                logging.info(f"SORA: Успешно получили task_id: {api_task_id}")
                return api_task_id

        except aiohttp.ClientResponseError as e:

            if e.status in [500, 502, 503, 504, 524] and attempt < SORA_POST_MAX_RETRIES - 1:
                logging.warning(
                    f"SORA: Ошибка сервера ({e.status}) при запросе task_id. Попытка {attempt + 1}/{SORA_POST_MAX_RETRIES}. "
                    f"Повтор через {SORA_POST_RETRY_DELAY} сек."
                )
                await asyncio.sleep(SORA_POST_RETRY_DELAY)
                continue

            raise
        except Exception as e:
            logging.error(f"SORA: Неожиданная ошибка при запросе task_id: {e}", exc_info=True)
            raise SoraError(f"SORA: Произошла неожиданная ошибка: {e}") from e

    raise SoraError(f"SORA: Не удалось получить task_id от API после {SORA_POST_MAX_RETRIES} попыток.")


async def _poll_sora_result(session: aiohttp.ClientSession, api_task_id: str) -> str:
    headers = {
        'Authorization': f'Bearer {API_UNIFICALLY_TOKEN}'
    }

    feed_url = f"{SORA_FEED_URL}/{api_task_id}"
    start_time = time.time()

    while time.time() - start_time < SORA_POLLING_TIMEOUT:
        try:
            logging.info(f"SORA: Опрос результата для task_id: {api_task_id}...")
            async with session.get(feed_url, headers=headers, ssl=False) as resp:

                if resp.status == 400:
                    try:
                        error_data = await resp.json()
                        error_message = error_data.get('data', {}).get('error', {}).get(
                            'message', 'API вернул 400 без сообщения об ошибке'
                        )
                    except Exception:
                        error_message = await resp.text()
                    logging.error(f"SORA: API вернул ошибку 400 для task {api_task_id}: {error_message}")
                    raise SoraError(f"Ошибка API (400): {error_message}")

                if resp.status in [500, 502, 503, 504, 524]:
                    logging.warning(
                        f"SORA: Ошибка сервера ({resp.status}) при опросе. Повторим через {SORA_POLLING_INTERVAL} сек.")
                    await asyncio.sleep(SORA_POLLING_INTERVAL)
                    continue

                if resp.status != 200:
                    resp.raise_for_status()

                response_data = await resp.json()
                data_block = response_data.get('data', {})
                status = data_block.get('status')

                if status == 'failed':
                    error_info = data_block.get('error', {})
                    error_message = error_info.get('message', 'Задача провалилась без сообщения')
                    raise SoraError(f"SORA: Задача {api_task_id} 'failed'. Причина: {error_message}")

                if status == 'completed':
                    output = data_block.get('output', {})
                    video_url = output.get('video_url')
                    if video_url:
                        logging.info(f"SORA: Успешно получен результат для task {api_task_id}.")
                        return video_url
                    else:
                        raise SoraError(f"SORA: Статус 'completed', но 'video_url' отсутствует в ответе.")

                logging.info(f"SORA: Task {api_task_id} еще в процессе (статус: {status}). Ожидаем...")
                await asyncio.sleep(SORA_POLLING_INTERVAL)

        except aiohttp.ClientResponseError:

            raise
        except SoraError:
            raise
        except Exception as e:
            logging.error(f"SORA: Неожиданная ошибка при опросе task {api_task_id}: {e}", exc_info=True)
            await asyncio.sleep(SORA_POLLING_INTERVAL)

    raise SoraError(f"SORA: Таймаут опроса ({SORA_POLLING_TIMEOUT} сек) для task_id: {api_task_id}")


async def generate_sora_video(session: aiohttp.ClientSession,
                              params: dict,
                              task_id: str,
                              s3_uploader: S3UploaderService,
                              circuit_breaker: Optional[CircuitBreakerRepository] = None,
                              model_name: str = "sora-2",
                              **kwargs) -> dict:
    logging.info(f"InternalTaskID: {task_id} | Вызов generate_sora_video с параметрами: {params}")

    if 'prompt' not in params:
        raise ValueError("Параметр 'prompt' обязателен для SORA.")

    try:
        prompt = params["prompt"]

        aspect_ratio = None
        if 'orientation' in params:
            aspect_ratio = orientation_dict.get(params['orientation'], '16:9')

        duration = params.get('duration')
        image_url = params.get('image_url')
        seed = params.get('seed')


        api_task_id = await _start_sora_task(
            session=session,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration=duration,
            image_url=image_url,
            seed=seed
        )

        logging.info(f"InternalTaskID: {task_id} | SORA API TaskID: {api_task_id} | Начинаем опрос результата.")


        temp_video_url = await _poll_sora_result(session, api_task_id)


        permanent_url = await s3_uploader.download_and_upload_video(
            session=session,
            source_url=temp_video_url,
            task_id=task_id
        )

        return {'video_url': permanent_url}

    except Exception as e:

        if isinstance(e, S3UploadServiceError):
            logging.error(f"TaskID: {task_id} | Ошибка S3, но Unifically жив. Fallback не нужен.")
            raise

        should_trip = False
        status_code = None


        if isinstance(e, aiohttp.ClientResponseError):
            status_code = e.status
        elif isinstance(e.__cause__, aiohttp.ClientResponseError):
            status_code = e.__cause__.status


        if status_code and status_code in [500, 502, 503, 504, 429]:
            should_trip = True

        if isinstance(e, asyncio.TimeoutError) or isinstance(e.__cause__, asyncio.TimeoutError):
            should_trip = True

        if should_trip and circuit_breaker:
            logging.error(
                f"TaskID: {task_id} | Unifically считается 'упавшим' (Status: {status_code}). "
                f"Разрываем цепь '{model_name}' и включаем Fallback на 5 минут."
            )

            await circuit_breaker.trip(model_name)
        else:
            logging.error(f"TaskID: {task_id} | Ошибка Unifically: {e}. Fallback только для текущей задачи.")


        raise