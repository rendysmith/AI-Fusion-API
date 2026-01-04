import asyncio
import logging
import time
from typing import Final, Optional

import aiohttp

from app.exceptions import UserValidationError, FatalProviderError
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
    """Кастомная ошибка для генерации видео через Sora-2."""
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


                if resp.status == 400:
                    try:
                        error_data = await resp.json()
                        error_message = error_data.get('data', {}).get('error', {}).get('message', str(error_data))
                    except:
                        error_message = await resp.text()

                    raise UserValidationError(f"Unifically 400: {error_message}")

                if resp.status >= 500:
                    raise FatalProviderError(f"Unifically Server Error: {resp.status}")

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

            raise FatalProviderError(f"Unifically Network Error: {e}")


        except UserValidationError:

            raise

        except Exception as e:

            raise FatalProviderError(f"Unifically Unexpected Error: {e}")

    raise FatalProviderError(f"Unifically failed to start task after retries")


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
                    raise UserValidationError(f"Unifically Poll 400: {error_message}")

                if resp.status in [500, 502, 503, 504, 524]:
                    logging.warning(
                        f"SORA: Ошибка сервера ({resp.status}) при опросе. Повторим через {SORA_POLLING_INTERVAL} сек.")
                    await asyncio.sleep(SORA_POLLING_INTERVAL)
                    continue

                if resp.status != 200:
                    resp.raise_for_status()

                response_data = await resp.json()
                data_block = response_data.get('data', {})

                logging.info(response_data)

                status = data_block.get('status')

                if status == 'failed':
                    error_info = data_block.get('error', {})
                    error_message = error_info.get('message', 'Unknown').lower()

                    if any(x in error_message for x in ['nsfw', 'policy', 'safety', 'moderation']):
                        raise UserValidationError(f"Unifically Safety: {error_message}")

                    raise FatalProviderError(f"Unifically Task Failed: {error_message}")

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


        except (UserValidationError, FatalProviderError):
            raise

        except Exception as e:
            logging.error(f"SORA: Неожиданная ошибка при опросе task {api_task_id}: {e}", exc_info=True)
            await asyncio.sleep(SORA_POLLING_INTERVAL)

    raise FatalProviderError(f"Unifically Polling Timeout ({SORA_POLLING_TIMEOUT}s)")


async def generate_sora_video(session: aiohttp.ClientSession,
                              params: dict,
                              task_id: str,
                              s3_uploader: S3UploaderService,
                              model_name: str = "sora-2",
                              **kwargs) -> dict:
    logging.info(f"InternalTaskID: {task_id} | Вызов generate_sora_video с параметрами: {params}")

    if 'prompt' not in params:
        raise ValueError("Параметр 'prompt' обязателен для SORA.")

    try:
        prompt = params["prompt"]

        aspect_ratio = params.get('aspect_ratio', '16:9')

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

    except (UserValidationError, FatalProviderError):
        raise

    except Exception as e:
        raise FatalProviderError(f"Unifically Critical: {e}")


if __name__ == "__main__":
    from aiobotocore.session import get_session


    async def manual_sora_run():
        print("🚀 Запуск теста Unifically Sora Provider...")

        # 1. Создаем реальный S3 клиент (как в main.py)
        session_s3 = get_session()
        async with session_s3.create_client(
                's3',
                region_name=settings.YANDEX_REGION,
                endpoint_url=settings.YANDEX_STORAGE_ENDPOINT,
                aws_access_key_id=settings.YANDEX_ACCESS_KEY_ID,
                aws_secret_access_key=settings.YANDEX_SECRET_ACCESS_KEY
        ) as s3_client:

            # 2. Инициализируем сервисы
            uploader = S3UploaderService(s3_client)

            async with aiohttp.ClientSession() as http_session:

                # --- ТЕСТ SORA ---
                print("\n🎥 Тестируем Sora-2...")
                test_params = {
                                  "prompt": "Создай девушку со светлыми волосами лет 25, идущий вдоль берега Персидского залива с видом на Бурдж аль Араб и поющие песню я тебя рисовал группа Ненси ",
                                  "model_name": "sora-2",
                                  "orientation": "portrait",
                                  "duration": 10
                                }
                test_task_id = f"test_unifically_sora_{int(time.time())}"

                try:

                    result = await generate_sora_video(
                        session=http_session,
                        params=test_params,
                        task_id=test_task_id,
                        s3_uploader=uploader,
                        circuit_breaker=None
                    )
                    print(f"✅ SORA SUCCESS! Video URL: {result['video_url']}")

                except SoraError as e:
                    print(f"❌ SORA FAILED (API Error): {e}")
                except Exception as e:
                    print(f"❌ SORA FAILED (Unknown): {e}")



    try:
        asyncio.run(manual_sora_run())
    except KeyboardInterrupt:
        print("\n🛑 Тест остановлен вручную.")