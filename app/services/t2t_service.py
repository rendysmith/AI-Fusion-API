import asyncio
import logging
import mimetypes

import aiohttp
from litellm import completion

from app.database.engine import async_session_factory
from app.settings import settings
from app.database.repositories.ai_model_repository import AiModelRepository

logger = logging.getLogger(__name__)

API_KEYS = {
    "ChatGPT": [settings.OPENAI_API_KEY, True],
    "Claude": [settings.ANTHROPIC_API_KEY, True],
    "Gemini": [settings.GEMINI_API_KEY, True],
    "Perplexity": [settings.PERPLEXITY_API_KEY, True],
    "Grsai": [settings.GRSAI_API_KEY, False]

}

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
                    if resp.status != 200:
                        try:
                            error_data = await resp.json()
                            msg = error_data.get("error", {}).get("message", await resp.text())
                        except Exception:
                            msg = await resp.text()
                        return f"❌ API error ({resp.status}): {msg}"

                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()

        except asyncio.TimeoutError:
            return "❌ Таймаут: сервер не ответил вовремя."
        except aiohttp.ClientError as e:
            return f"❌ Ошибка подключения: {e}"
        except (KeyError, IndexError, ValueError) as e:
            return f"❌ Некорректный ответ от API: {e}"

    async def lite_llm(self, api_key: str, model: str, question: str, **kwargs):
        # LiteLLM сам понимает, какое API дергать, исходя из названия модели
        response = completion(
            model=model,
            messages=question,
            api_key=api_key,
            **kwargs
        )
        return response.choices[0].message.content

    async def get_response(self, prompt, model, **kwargs):
        """
        Универсальный метод вызова любой модели.

        :param prompt: Текст запроса
        :param model_name: Название модели (ChatGPT, Claude, Gemini, Perplexity)
        :param kwargs: Доп. параметры (temperature, max_tokens и т.д.)
        """

        model = model.title()

        messages = [
            {"role": "user", "content": prompt}
        ]

        amr = AiModelRepository(async_session_factory)
        providers = await amr.get_by_proveder_all(model)

        if len(providers) == 0:
            return f"Провайдеров для {model} не найдено!"

        for prov in providers:
            provider = prov.provider
            api_key = API_KEYS[provider][0]
            connect_llm = API_KEYS[provider][1]

            if connect_llm:
                try:
                    result = await self.lite_llm(api_key, model, prompt)
                    return result

                except Exception as Ex:
                    logging.info(f'Error: {Ex}')
                    continue

            else:
                try:
                    result = await self.grsai(api_key, model, prompt)
                    return result

                except Exception as Ex:
                    logging.info(f'Error: {Ex}')
                    continue







        else:
            return f"Ошибка при вызове модели {model}"
