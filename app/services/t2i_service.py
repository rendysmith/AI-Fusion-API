
import logging

import asyncio
from typing import Optional, Dict, Any

import aiohttp
from litellm import completion, image_generation

from app.database.engine import async_session_factory
from app.schemas import ChatMessageCreate, ChatSessionCreate
from app.settings import settings
from app.database.repositories.priority_model_repository import PriorityModelRepository

logger = logging.getLogger(__name__)

class UniversalImageGenerator:
    async def lite_llm(self, api_key: str, model: str, prompt: str, **kwargs):
        """
             Генерация через LiteLLM (DALL-E 3, Imagen и др.)
             """
        # 1. Извлекаем параметры
        aspect_ratio = kwargs.get("aspect_ratio", "square")  # square, landscape, portrait
        # DALL-E 3 требует конкретных разрешений, мапим их:
        size_map = {
            "square": "1024x1024",
            "1:1": "1024x1024",
            "auto": "1024x1024",
            "landscape": "1792x1024",  # Широкий формат для DALL-E 3
            "16:9": "1792x1024",
            "portrait": "1024x1792",  # Вертикальный формат для DALL-E 3
            "9:16": "1024x1792"
        }

        # Выбираем размер, если не нашли - дефолт 1024x1024
        final_size = size_map.get(aspect_ratio, "1024x1024")

        try:
            logger.info(f"🚀 [LiteLLM] Запрос к {model}: {prompt[:30]}... Size: {final_size}")

            # 2. Выполняем генерацию
            # image_generation - синхронная функция, поэтому запускаем её в отдельном потоке,
            # чтобы не блокировать основной цикл (asyncio loop)
            response = await asyncio.to_thread(
                image_generation,
                prompt=prompt,
                model=model,  # например: "dall-e-3"
                api_key=api_key,  # Передаем ключ явно
                size=final_size,
                n=1  # Количество изображений
            )

            # 3. Извлекаем результат
            # Структура ответа LiteLLM: response.data[0].url
            if response and response.data:
                image_url = response.data[0].url
                logger.info(f"✅ [LiteLLM] Успех: {image_url}")
                return image_url
            else:
                return "❌ LiteLLM вернул пустой ответ (без data)."

        except Exception as e:
            err_msg = str(e)
            logger.error(f"❌ [LiteLLM] Error: {err_msg}")

            # Обработка частых ошибок OpenAI (например, Content Policy)
            if "safety" in err_msg.lower() or "content_policy_violation" in err_msg.lower():
                return "❌ Ошибка: Запрос отклонен системой безопасности (Safety Policy)."

            return f"❌ Ошибка провайдера: {err_msg}"

    async def _make_post_request(self, session: aiohttp.ClientSession, url: str, headers: Dict, payload: Dict) -> Dict:
        """Вспомогательный метод для выполнения запросов с обработкой ошибок."""
        try:
            async with session.post(url, headers=headers, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=30)) as resp:
                data = await resp.json()

                if resp.status != 200:
                    error_msg = data.get("msg") or data.get("error", {}).get("message") or await resp.text()
                    raise Exception(f"API Error ({resp.status}): {error_msg}")

                return data
        except asyncio.TimeoutError:
            raise Exception("Таймаут: сервер не ответил вовремя.")
        except aiohttp.ClientError as e:
            raise Exception(f"Ошибка подключения: {e}")

    async def grsai(self,
                    api_key: str,
                    model: str,
                    prompt: str,
                    **kwargs
                    ) -> str:
        """
        Запускает генерацию, ждет завершения и возвращает URL картинки.

        Args:
            api_key (str): Токен API.
            model (str): Модель (напр. 'nano-banana').
            prompt (str): Описание картинки.
            aspect_ratio (str): Пропорции (auto, 1:1, 16:9, etc).

        Returns:
            str: URL сгенерированного изображения или сообщение об ошибке.
        """

        aspect_ratio = kwargs.get("aspect_ratio", "auto")
        image_size = kwargs.get("image_size", "1K")
        urls = kwargs.get("urls", None)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        # 1. ЗАПУСК ЗАДАЧИ
        submit_url = f"https://api.grsai.com/v1/draw/nano-banana"
        submit_payload = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "webHook": "-1",  # Важно: -1 возвращает ID сразу для поллинга
            "shutProgress": False
        }

        if image_size:
            submit_payload["imageSize"] = image_size

        if urls and len(urls) > 0:
            submit_payload["urls"] = urls

        try:
            async with aiohttp.ClientSession() as session:
                # Отправляем задачу
                logger.info(f"🚀 Отправка задачи: {prompt[:50]}...")
                submit_response = await self._make_post_request(session, submit_url, headers, submit_payload)

                # Извлекаем ID задачи. API может вернуть структуру {data: {id: ...}} или {id: ...}
                task_id = None
                if "data" in submit_response and isinstance(submit_response["data"], dict):
                    task_id = submit_response["data"].get("id")
                else:
                    task_id = submit_response.get("id")

                if not task_id:
                    return f"❌ Ошибка: Не удалось получить ID задачи. Ответ: {submit_response}"

                prilogger.infont(f"⏳ Задача получена ID: {task_id}. Ожидание генерации...")

                # 2. ОЖИДАНИЕ РЕЗУЛЬТАТА (Polling)
                result_url = f"https://api.grsai.com/v1/draw/result"
                result_payload = {"id": task_id}

                attempts = 0
                max_attempts = 45  # Ждем максимум 60 секунд (30 * 2 сек)

                while attempts < max_attempts:
                    await asyncio.sleep(2)  # Пауза между проверками

                    try:
                        res_data = await self._make_post_request(session, result_url, headers, result_payload)
                    except Exception as e:
                        print(f"⚠️ Ошибка при проверке статуса: {e}. Пробуем еще раз...")
                        attempts += 1
                        continue

                    # Проверяем структуру ответа результата (обычно внутри data)
                    data_block = res_data.get("data", res_data)  # На случай если data нет на верхнем уровне

                    status = data_block.get("status")

                    if status == "succeeded":
                        results = data_block.get("results", [])
                        if results and len(results) > 0:
                            image_url = results[0].get("url")
                            return image_url
                        else:
                            return "❌ Статус успех, но массив results пуст."

                    elif status == "failed":
                        reason = data_block.get("failure_reason") or data_block.get("error")
                        return f"❌ Генерация не удалась. Причина: {reason}"

                    elif status == "running" or status is None:
                        # Продолжаем ждать
                        progress = data_block.get("progress", 0)
                        # print(f"Generate progress: {progress}%") # Можно раскомментировать для отладки
                        attempts += 1
                    else:
                        return f"❌ Неизвестный статус: {status}"

                return "❌ Таймаут ожидания генерации (картинка создавалась слишком долго)."

        except Exception as e:
            return f"❌ Критическая ошибка: {str(e)}"

    async def get_response(self, user_id, prompt, model_slug, **kwargs):
        """
        Универсальный метод вызова любой модели.

        :param prompt: Текст запроса
        :param model_slug: Название модели (ChatGPT, Claude, Gemini, Perplexity)
        :param kwargs: Доп. параметры (temperature, max_tokens и т.д.)
        """
        API_KEYS = {
            "ChatGPT": [settings.OPENAI_API_KEY, self.lite_llm],
            "Google": [settings.GEMINI_API_KEY, self.lite_llm],
            "Grsai": [settings.GRSAI_API_KEY, self.grsai]
        }

        pmr = PriorityModelRepository(async_session_factory)
        providers = await pmr.get_by_proveder_all(model_slug)

        if len(providers) == 0:
            return f"Провайдеров для {model} не найдено!"

        for prov in providers:
            provider_name = prov.provider  # Например, "Grsai"

            if provider_name not in API_KEYS:
                logger.error(f"Провайдер {provider_name} есть в БД, но не настроен в коде (API_KEYS).")
                continue

            api_key = API_KEYS[provider_name][0]
            connector_func = API_KEYS[provider_name][1]

            try:
                # ВАЖНО: передаем model_slug и **kwargs (где лежат настройки картинки)
                # connector_func это self.grsai
                result_url = await connector_func(api_key, model_slug, prompt, **kwargs)

                # --- ЛОГИКА СОХРАНЕНИЯ В ИСТОРИЮ (ОПЦИОНАЛЬНО) ---
                # Если result_url начинается с ошибки "❌", возможно, не стоит сохранять это как успешный чат
                if str(result_url).startswith("❌"):
                    logger.warning(f"Генерация вернула ошибку: {result_url}")
                    # Можно вернуть ошибку сразу или попробовать следующего провайдера
                    return result_url

                try:
                    chat_repo = PriorityModelRepository(async_session_factory)

                    # Создаем сессию
                    session_payload = ChatSessionCreate(
                        user_id=user_id,
                        model_slug=model_slug,
                        chat_name=f"Image: {prompt[:20]}..."
                    )
                    new_session = await chat_repo.create_session(session_payload)

                    # Сохраняем сообщение (промпт пользователя)
                    user_message = ChatMessageCreate(
                        session_id=new_session.id,
                        role='user',
                        message_text=prompt,
                        token_count=len(prompt) // 4
                    )
                    await chat_repo.create_message(user_message)

                    # Сохраняем ответ (URL картинки) как сообщение ассистента
                    ai_message = ChatMessageCreate(
                        session_id=new_session.id,
                        role='assistant',
                        message_text=result_url,  # Сохраняем ссылку как текст
                        token_count=0
                    )
                    await chat_repo.create_message(ai_message)

                except Exception as db_ex:
                    logger.error(f"Ошибка при сохранении в БД: {db_ex}")
                    # Не прерываем выполнение, если БД упала, главное - вернуть картинку пользователю

                return result_url

            except Exception as Ex:
                logger.error(f'Ошибка при вызове провайдера {provider_name}: {Ex}')
                continue  # Пробуем следующего провайдера

        return f"Не удалось сгенерировать изображение ни одним провайдером для {model_slug}"

if "__main__" in __name__:

    api_key = 'sk-3b00533d9f574087a4ee67c61dde992c'
    model = 'nano-banana-fast'
    prompt = 'A beautiful girl with long hair and blue eyes?'

    ullm = UniversalImageGenerator()
    a = asyncio.run(ullm.grsai(api_key, model, prompt))
    print(a)