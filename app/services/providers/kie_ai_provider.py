import asyncio
import json
import logging
import random
import time
from typing import Dict, List

import aiohttp

from app.settings import settings

API_BASE_URL_KIE_AI = 'https://api.kie.ai'
POLL_TOTAL_TIMEOUT_SECONDS = 600
POLL_INTERVAL_SECONDS = 30


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



class KieAiGenerationError(Exception):
    pass


class SoraGenerationError(KieAiGenerationError):
    pass


class GptImageGenerationError(KieAiGenerationError):
    pass



async def _make_request_with_retry(request_func, *args, **kwargs):

    max_retries = 5
    base_delay = 1.0
    last_exception = None

    for attempt in range(max_retries):
        try:

            if 'timeout' not in kwargs:
                kwargs['timeout'] = aiohttp.ClientTimeout(total=60)

            response = await request_func(*args, **kwargs)
            response.raise_for_status()
            return response
        except (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(
                    f"Ошибка соединения ({type(e).__name__}): {e}. Попытка #{attempt + 2}. Повтор через {delay:.2f} сек.")
                await asyncio.sleep(delay)
            else:
                logging.error(f"Не удалось подключиться к API после {max_retries} попыток.")
                raise KieAiGenerationError(
                    "Не удалось подключиться к API после нескольких попыток.") from last_exception
        except aiohttp.ClientResponseError as e:
            if e.status in [500, 502, 503, 504] and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"Сервер вернул временную ошибку {e.status}. Повторяем запрос...")
                await asyncio.sleep(delay)
                continue
            else:

                raise e
    return None



async def _start_sora_video_generation_kie_ai(session: aiohttp.ClientSession,
                                              prompt: str,
                                              aspect_ratio: str,
                                              image_url: str = None,
                                              duration: int = 10) -> str:


    url = f"{API_BASE_URL_KIE_AI}/api/v1/jobs/createTask"
    payload = {'input': {'prompt': prompt, "aspect_ratio": aspect_ratio, 'n_frames': str(duration)}}

    if image_url:
        payload['input']['image_urls'] = [image_url]
        payload['model'] = 'sora-2-image-to-video'
    else:
        payload['model'] = 'sora-2-text-to-video'


    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {settings.KIE_AI}'}

    logging.info(f"SORA: Запуск генерации видео. Payload: {payload}")

    try:
        response = await _make_request_with_retry(session.post, url, json=payload, headers=headers, ssl=False)
        async with response:
            result = await response.json()
            if result.get('code') != 200:
                msg = result.get('msg', 'Нет подробностей')
                logging.error(result)
                raise SoraGenerationError(f"API вернуло ошибку при запуске задачи: {msg}")
            task_id = result.get('data', {}).get('taskId')
            if not task_id:
                raise SoraGenerationError("Не удалось получить ID задачи от API.")
            return task_id
    except aiohttp.ClientResponseError as e:
        error_details = e.message
        raise SoraGenerationError(f"Ошибка при запуске генерации (Статус {e.status}): {error_details}")
    except (json.JSONDecodeError, aiohttp.ContentTypeError):
        raise SoraGenerationError("API вернул некорректный ответ (не JSON).")


async def _poll_for_sora_video_url_kie_ai(session: aiohttp.ClientSession, task_id: str) -> str:

    url = f"{API_BASE_URL_KIE_AI}/api/v1/jobs/recordInfo"
    headers = {'Authorization': f'Bearer {settings.KIE_AI}'}
    params = {"taskId": task_id}
    start_time = time.time()

    while time.time() - start_time < POLL_TOTAL_TIMEOUT_SECONDS:
        logging.info(f"SORA: Проверка статуса задачи {task_id}...")
        try:
            response = await _make_request_with_retry(session.get, url, params=params, headers=headers, ssl=False)
            async with response:
                result = await response.json()
                status = result.get('data', {}).get('state')
                if status == 'success':
                    nested_data = json.loads(result['data']['resultJson'])
                    video_url = nested_data.get('resultUrls', [None])[0]
                    if video_url:
                        return video_url
                    raise SoraGenerationError("Задача завершена, но URL видео не найден.")
                elif status == 'fail':
                    raise SoraGenerationError(f"Ошибка генерации: {result.get('data', {}).get('failMsg')}")
                else:
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logging.warning(f"SORA: Ошибка при опросе статуса: {e}. Повтор...")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    raise SoraGenerationError(f"Время ожидания результата для задачи {task_id} истекло.")


async def generate_sora_kie_ai_video(session: aiohttp.ClientSession, params: Dict, **kwargs) -> Dict:

    provider_task_id = await _start_sora_video_generation_kie_ai(
        session=session,
        prompt=params['prompt'],
        image_url=params.get('image_url'),
        aspect_ratio=params.get('orientation', 'landscape'),
        duration=params.get('duration', 10)
    )
    logging.info(f"SORA: Задача на генерацию запущена, ID: {provider_task_id}")
    video_url = await _poll_for_sora_video_url_kie_ai(session, provider_task_id)
    return {"video_url": video_url}
