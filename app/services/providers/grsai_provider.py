import asyncio
import logging
import json
from typing import Final, Optional

import aiohttp

from app.exceptions import FatalProviderError, UserValidationError
from app.settings import settings
from app.services.s3_uploader import S3UploaderService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


GRSAI_BASE_URL: Final[str] = "https://api.grsai.com"
GRSAI_SORA_PATH: Final[str] = "/v1/video/sora-video"
GRSAI_VEO_PATH: Final[str] = "/v1/video/veo"
GRSAI_NANO_BANANA_PATH: Final[str] = "/v1/draw/nano-banana"
GRSAI_RESULT_PATH: Final[str] = "/v1/draw/result"

POLLING_INTERVAL: Final[int] = 20
POLLING_TIMEOUT: Final[int] = 900


ASPECT_RATIO_MAP = {
    'landscape': '16:9',
    'portrait': '9:16',
    'square': '1:1'
}

MODELS_API_MAP = {
    'veo-3-fast': 'veo3.1-fast',
    'veo-3-quality': 'veo3.1-pro'
}


class GrsaiError(Exception):
    """Кастомная ошибка для провайдера Grsai."""
    pass


async def _make_request(
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        payload: dict = None
) -> dict:
    headers = {
        'Authorization': f'Bearer {settings.GRSAI_API_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        if method == "POST":
            async with session.post(url, json=payload, headers=headers, ssl=False) as resp:
                resp_text = await resp.text()

                if resp.status == 400:
                    raise UserValidationError(f"GrsAI 400 Bad Request: {resp_text}")

                if resp.status in [401, 403]:
                    raise FatalProviderError(f"GrsAI Auth Error ({resp.status}): {resp_text}")

                if resp.status >= 500:
                    raise FatalProviderError(f"GrsAI Server Error ({resp.status}): {resp_text}")

                if resp.status != 200:
                    raise FatalProviderError(f"GrsAI Unknown Error ({resp.status}): {resp_text}")

                return json.loads(resp_text)

        elif method == "GET":

            async with session.get(url, params=payload, headers=headers, ssl=False) as resp:
                resp_text = await resp.text()

                if resp.status == 400:
                    raise UserValidationError(f"GrsAI 400 Bad Request: {resp_text}")
                if resp.status >= 500:
                    raise FatalProviderError(f"GrsAI Server Error ({resp.status}): {resp_text}")

                if resp.status != 200:
                    raise FatalProviderError(f"GrsAI Error ({resp.status}): {resp_text}")
                return json.loads(resp_text)

    except aiohttp.ClientError as e:
        raise FatalProviderError(f"GrsAI Network Error: {e}") from e



async def _poll_result(session: aiohttp.ClientSession, task_id: str, model_type: str) -> str:
    """
    Опрашивает статус задачи, пока не получит результат или ошибку.
    model_type: 'sora' или 'veo' (нужно для парсинга ответа, так как они чуть отличаются)
    """
    url = f"{GRSAI_BASE_URL}{GRSAI_RESULT_PATH}"
    payload = {"id": task_id}

    start_time = asyncio.get_running_loop().time()

    while True:
        if asyncio.get_running_loop().time() - start_time > POLLING_TIMEOUT:
            raise asyncio.TimeoutError(f"Timeout polling task {task_id}")

        data = await _make_request(session, "POST", url, payload)



        if data.get("code") != 0:

            logger.warning(f"Grsai Poll Warning: {data.get('msg')} (Code {data.get('code')})")
            await asyncio.sleep(POLLING_INTERVAL)
            continue

        result_data = data.get("data", {})
        status = result_data.get("status")

        if status == "succeeded":

            if model_type == 'sora':

                results = result_data.get("results", [])
                if results and len(results) > 0:
                    return results[0].get("url")


            elif model_type == 'nano_banana':
                results = result_data.get("results", [])
                if results and len(results) > 0:
                    return results[0].get("url")

            elif model_type == 'veo':

                return result_data.get("url")

            raise GrsaiError(f"Статус succeeded, но URL видео не найден в ответе: {result_data}")

        elif status == "failed":
            reason = result_data.get("failure_reason")
            error_msg = result_data.get("error", "Unknown error")

            error_lower = error_msg.lower()

            user_fault_keywords = [
                "violation", "violate",
                "moderation",
                "sensitive",
                "safety",
                "policy", "policies",
                "nsfw",
                "filter",
                'processing_error'
            ]
            if any(word in error_lower for word in user_fault_keywords):
                raise UserValidationError(f"GrsAI Safety Policy: {error_msg}")


            raise FatalProviderError(f"GrsAI Generation Failed: {reason} - {error_msg}")


        await asyncio.sleep(POLLING_INTERVAL)



async def generate_sora_grsai(
        session: aiohttp.ClientSession,
        params: dict,
        task_id: str,
        s3_uploader: S3UploaderService,
        model_name: str = "sora-2",
        **kwargs
) -> dict:
    logger.info(f"TaskID: {task_id} | Grsai Sora Start")


    logger.info(f"TaskID: {task_id} | Grsai Sora Params: {params}")


    prompt = params.get("prompt")
    if not prompt:
        raise ValueError("Prompt is required")

    ratio = params.get("aspect_ratio", "16:9")
    duration = params.get("duration", 10)





    payload = {
        "model": "sora-2",
        "prompt": prompt,
        "aspectRatio": ratio,
        "duration": int(duration),
        "webHook": "-1"
    }

    if params.get("image_url"):
        payload["url"] = params.get("image_url")

    try:

        url = f"{GRSAI_BASE_URL}{GRSAI_SORA_PATH}"
        resp_json = await _make_request(session, "POST", url, payload)


        provider_task_id = resp_json.get("data", {}).get("id")
        if not provider_task_id:
            raise GrsaiError(f"No task ID in response: {resp_json}")

        logger.info(f"TaskID: {task_id} | Grsai Task ID: {provider_task_id}")


        video_url = await _poll_result(session, provider_task_id, model_type='sora')


        final_url = await s3_uploader.download_and_upload_video(
            session=session,
            source_url=video_url,
            task_id=task_id
        )

        return {"video_url": final_url}

    except (UserValidationError, FatalProviderError):
        raise

    except Exception as e:
        raise FatalProviderError(f"GrsAI Unexpected Error: {e}") from e



async def generate_veo_grsai(
        session: aiohttp.ClientSession,
        params: dict,
        task_id: str,
        s3_uploader: S3UploaderService,
        model_name: str = "veo-3-fast",
        **kwargs
) -> dict:
    logger.info(f"TaskID: {task_id} | Grsai Veo Start ({model_name})")

    prompt = params.get("prompt")
    if not prompt:
        raise ValueError("Prompt is required")

    aspect_ratio = ASPECT_RATIO_MAP.get(params.get("orientation", "landscape"), "16:9")


    api_model = model_name.replace("veo-3-fast", "veo3.1-fast")

    payload = {
        "model": api_model,
        "prompt": prompt,
        "aspectRatio": aspect_ratio,
        "webHook": "-1"
    }


    if params.get("image_url"):
        payload["firstFrameUrl"] = params.get("image_url")

    try:
        url = f"{GRSAI_BASE_URL}{GRSAI_VEO_PATH}"
        resp_json = await _make_request(session, "POST", url, payload)

        logging.info(resp_json)

        provider_task_id = resp_json.get("data", {}).get("id")
        if not provider_task_id:
            raise GrsaiError(f"No task ID in response: {resp_json}")

        logger.info(f"TaskID: {task_id} | Grsai Veo Task ID: {provider_task_id}")

        video_url = await _poll_result(session, provider_task_id, model_type='veo')

        final_url = await s3_uploader.download_and_upload_video(
            session=session,
            source_url=video_url,
            task_id=task_id
        )

        return {"video_url": final_url}


    except (UserValidationError, FatalProviderError):
        raise

    except Exception as e:
        raise FatalProviderError(f"GrsAI Unexpected Error: {e}") from e


async def _generate_nano_base(
        session: aiohttp.ClientSession,
        params: dict,
        task_id: str,
        s3_uploader: S3UploaderService,
        api_model_name: str,
        extra_payload: dict = None
) -> dict:
    logger.info(f"TaskID: {task_id} | Grsai {api_model_name} Start")

    prompt = params.get("prompt")
    if not prompt:
        raise UserValidationError("Prompt is required")

    aspect_ratio = params.get("aspect_ratio", 'auto')

    payload = {
        "model": api_model_name,
        "prompt": prompt,
        "aspectRatio": aspect_ratio,
        "webHook": "-1"
    }

    if params.get("image_urls"):
        payload["urls"] = params.get("image_urls")


    if extra_payload:
        payload.update(extra_payload)

    try:
        url = f"{GRSAI_BASE_URL}{GRSAI_NANO_BANANA_PATH}"
        resp_json = await _make_request(session, "POST", url, payload)

        provider_task_id = resp_json.get("data", {}).get("id")
        if not provider_task_id:
            raise FatalProviderError(f"No task ID in response: {resp_json}")

        logger.info(f"TaskID: {task_id} | Grsai Task ID: {provider_task_id}")

        image_url = await _poll_result(session, provider_task_id, model_type='nano_banana')

        final_url = await s3_uploader.download_and_upload_image(
            session=session,
            source_url=image_url,
            task_id=task_id
        )


        return {"image_url": final_url}

    except (UserValidationError, FatalProviderError):
        raise
    except Exception as e:
        raise FatalProviderError(f"GrsAI {api_model_name} Unexpected Error: {e}") from e


async def generate_nano_banana_grsai(
        session: aiohttp.ClientSession,
        params: dict,
        task_id: str,
        s3_uploader: S3UploaderService,
        **kwargs
) -> dict:
    """
    Функция для обычной Nano Banana
    """
    return await _generate_nano_base(
        session=session,
        params=params,
        task_id=task_id,
        s3_uploader=s3_uploader,
        api_model_name="nano-banana-fast"
    )


async def generate_nano_banana_pro_grsai(
        session: aiohttp.ClientSession,
        params: dict,
        task_id: str,
        s3_uploader: S3UploaderService,
        **kwargs
) -> dict:
    """
    Функция для Nano Banana PRO (поддерживает imageSize)
    """
    image_size = params.get("image_size", "1K")

    return await _generate_nano_base(
        session=session,
        params=params,
        task_id=task_id,
        s3_uploader=s3_uploader,
        api_model_name="nano-banana-pro",
        extra_payload={"imageSize": image_size}
    )


if __name__ == "__main__":
    from aiobotocore.session import get_session


    async def manual_run():
        print("🚀 Запуск теста GRSAI Provider...")

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

                # --- ТЕСТ 1: SORA 2 ---
                print("\n🎥 [1/2] Тестируем Sora-2...")
                sora_params = {
                    "prompt": "A cinematic drone shot of a futuristic cyberpunk city with neon lights, 8k",
                    "orientation": "landscape",
                    "duration": 10
                }
                sora_task_id = "test_grsai_sora_001"

                try:
                    result = await generate_sora_grsai(
                        session=http_session,
                        params=sora_params,
                        task_id=sora_task_id,
                        s3_uploader=uploader
                    )
                    print(f"✅ SORA SUCCESS! URL: {result['video_url']}")
                except Exception as e:
                    print(f"❌ SORA FAILED: {e}")

                # --- ТЕСТ 2: VEO 3 ---
                # print("\n🎥 [2/2] Тестируем Veo-3...")
                # veo_params = {
                #     "prompt": "A cute cat playing with a ball on green grass, realistic",
                #     "orientation": "landscape",
                #     # "image_url": "https://..." # Можно раскомментировать для теста image-to-video
                # }
                # veo_task_id = "test_grsai_veo_001"
                #
                # try:
                #
                #     result = await generate_veo_grsai(
                #         session=http_session,
                #         params=veo_params,
                #         task_id=veo_task_id,
                #         s3_uploader=uploader,
                #         model_name="veo-3-fast"
                #     )
                #     print(f"✅ VEO SUCCESS! URL: {result['video_url']}")
                # except Exception as e:
                #     print(f"❌ VEO FAILED: {e}")


    # Запускаем
    try:
        asyncio.run(manual_run())
    except KeyboardInterrupt:
        pass