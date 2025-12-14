
import logging

import asyncio
from typing import Optional, Dict, Any

import aiohttp
from litellm import completion

from app.database.engine import async_session_factory
from app.schemas.ai_model import ChatMessageCreate, ChatSessionCreate
from app.settings import settings
from app.database.repositories.priority_model_repository import PriorityModelRepository

logger = logging.getLogger(__name__)

class UniversalImageGenerator:
    async def lite_llm(self):
        pass

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
                    aspect_ratio: str = "auto",
                    image_size: str = "1K",  # <--- Добавлено: Размер (1K, 2K, 4K)
                    urls: Optional[List[str]] = None  # <--- Добавлено: Список ссылок-референсов
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
                print(f"🚀 Отправка задачи: {prompt[:50]}...")
                submit_response = await self._make_post_request(session, submit_url, headers, submit_payload)

                # Извлекаем ID задачи. API может вернуть структуру {data: {id: ...}} или {id: ...}
                task_id = None
                if "data" in submit_response and isinstance(submit_response["data"], dict):
                    task_id = submit_response["data"].get("id")
                else:
                    task_id = submit_response.get("id")

                if not task_id:
                    return f"❌ Ошибка: Не удалось получить ID задачи. Ответ: {submit_response}"

                print(f"⏳ Задача получена ID: {task_id}. Ожидание генерации...")

                # 2. ОЖИДАНИЕ РЕЗУЛЬТАТА (Polling)
                result_url = f"https://api.grsai.com/v1/draw/result"
                result_payload = {"id": task_id}

                attempts = 0
                max_attempts = 30  # Ждем максимум 60 секунд (30 * 2 сек)

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
            provider = prov.provider
            api_key = API_KEYS[provider][0]
            connecter = API_KEYS[provider][1]

            try:
                result = await connecter(api_key, model, prompt)

                # Создаем объект схемы
                session_payload = ChatSessionCreate(
                    user_id=user_id,
                    model_slug=model_slug,
                    chat_name="Первый диалог"
                )

                # Вызываем функцию репозитория
                chat_repo = PriorityModelRepository(async_session_factory)
                new_session = await chat_repo.create_session(session_payload)

                # СОХРАНЯЕМ ID СЕССИИ ДЛЯ ДАЛЬНЕЙШЕЙ РАБОТЫ!
                session_id = new_session.id

               # Токены для prompt можно посчитать отдельной функцией, здесь для примера:
                prompt_tokens = 5

                user_message_payload = ChatMessageCreate(
                    session_id=session_id,  # Используем ID, полученный на Шаге 1
                    role='user',
                    message_text=prompt,
                    token_count=prompt_tokens
                )

                await chat_repo.create_message(user_message_payload)

                return result

            except Exception as Ex:
                logging.info(f'Error: {Ex}')
                continue

        else:
            return f"Ошибка при вызове модели {model}"

if "__main__" in __name__:

    api_key = 'sk-3b00533d9f574087a4ee67c61dde992c'
    model = 'nano-banana-fast'
    prompt = 'A beautiful girl with long hair and blue eyes?'

    ullm = UniversalImageGenerator()
    a = asyncio.run(ullm.grsai(api_key, model, prompt))
    print(a)