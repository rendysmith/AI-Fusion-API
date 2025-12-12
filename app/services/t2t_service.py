import asyncio
import logging
import mimetypes

import aiohttp
from litellm import completion

from app.database.engine import async_session_factory
from app.settings import settings
from app.database.repositories.priority_model_repository import PriorityModelRepository

logger = logging.getLogger(__name__)

class UniversalLLM:
    async def grsai(self, api_key: str, model: str, question: str) -> str:
        """
        Задаёт вопрос модели gpt-4o-all через API Grsai.

        Args:
            api_key (str): Ваш токен доступа к API Grsai.
            question (str): Вопрос, который вы хотите задать модели.

        Returns:
            str: Ответ от модели или сообщение об ошибке.
        """
        url = "https://api.grsai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful, accurate, and concise assistant."},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "stream": False
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    data = await resp.json()  # Сначала получаем JSON

                    print(data)

                    if resp.status != 200:
                        # Обработка стандартных ошибок по статусу (401, 403, 429, 500 и т.д.)
                        msg = data.get("error", {}).get("message", await resp.text())
                        return f"❌ API error ({resp.status}): {msg}"

                    # --- НАДЕЖНОЕ ИЗВЛЕЧЕНИЕ КОНТЕНТА ---
                    try:
                        # 1. Получаем список 'choices'. Если нет, то пустой список.
                        choices = data.get("choices", [])
                        if not choices:
                            return f"❌ Некорректный ответ от API: отсутствует 'choices' или он пуст. Ответ: {data}"

                        # 2. Получаем объект 'message' (для non-stream) ИЛИ 'delta' (для stream).
                        # Если ни того, ни другого нет, то пустой словарь.
                        message_container = choices[0].get("message") or choices[0].get("delta", {})

                        # 3. Получаем 'content' из контейнера. Если нет, то None.
                        content = message_container.get("content")

                        if content is None:
                            # Если контент пуст, но ответ успешный, возвращаем сообщение об этом
                            return "✅ Успешный ответ, но модель не сгенерировала текстовый контент."

                        return str(content).strip()

                    except IndexError:
                        # На случай, если choices[0] недоступен
                        return f"❌ Некорректный ответ от API: 'choices' не содержит элементов. Ответ: {data}"
                    # --------------------------------------

            # Перехватываем ошибки подключения и таймауты
        except asyncio.TimeoutError:
            return "❌ Таймаут: сервер не ответил вовремя."
        except aiohttp.ClientError as e:
            return f"❌ Ошибка подключения: {e}"
        except Exception as e:
            # Общий перехват, который поймает любой другой сбой парсинга
            return f"❌ Непредвиденная ошибка при обработке ответа: {e}"

    async def lite_llm(self, api_key: str, model: str, question: str, **kwargs):
        messages = [
            {"role": "user", "content": question}
        ]

        # LiteLLM сам понимает, какое API дергать, исходя из названия модели
        response = completion(
            model=model,
            messages=messages,
            api_key=api_key,
            **kwargs
        )
        return response.choices[0].message.content

    async def get_response(self, prompt, model_name, **kwargs):
        """
        Универсальный метод вызова любой модели.

        :param prompt: Текст запроса
        :param model_name: Название модели (ChatGPT, Claude, Gemini, Perplexity)
        :param kwargs: Доп. параметры (temperature, max_tokens и т.д.)
        """
        API_KEYS = {
            "ChatGPT": [settings.OPENAI_API_KEY, self.lite_llm],
            "Anthropic": [settings.ANTHROPIC_API_KEY, self.lite_llm],
            "Google": [settings.GEMINI_API_KEY, self.lite_llm],
            "Perplexity": [settings.PERPLEXITY_API_KEY, self.lite_llm],
            "Grsai": [settings.GRSAI_API_KEY, self.grsai]
        }


        pmr = PriorityModelRepository(async_session_factory)
        providers = await pmr.get_by_proveder_all(model_name)

        if len(providers) == 0:
            return f"Провайдеров для {model} не найдено!"

        for prov in providers:
            provider = prov.provider
            api_key = API_KEYS[provider][0]
            connecter = API_KEYS[provider][1]

            try:
                result = await connecter(api_key, model, prompt)
                return result

            except Exception as Ex:
                logging.info(f'Error: {Ex}')
                continue

        else:
            return f"Ошибка при вызове модели {model}"

if "__main__" in __name__:
    ullm = UniversalLLM()
    api_key = 'sk-3b00533d9f574087a4ee67c61dde992c'
    model = 'gemini-2.5-flash'
    prompt = 'Кто такой Илон Маск?'

    a = asyncio.run(ullm.grsai(api_key, model, prompt))
    print(a)