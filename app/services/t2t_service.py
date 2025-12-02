import logging
import mimetypes

from litellm import completion

import aiohttp
import aiobotocore.client


from app.settings import settings
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.db import async_session_factory


logger = logging.getLogger(__name__)

API_KEYS = {
    "ChatGPT": settings.OPENAI_API_KEY,
    "Claude": settings.ANTHROPIC_API_KEY,
    "Gemini": settings.GEMINI_API_KEY,
    "Perplexity": settings.PERPLEXITY_API_KEY
}


class UniversalLLM:
    async def get_response(self, prompt, provider, **kwargs):
        """
        Универсальный метод вызова любой модели.

        :param prompt: Текст запроса
        :param model_name: Название модели (ChatGPT, Claude, Gemini, Perplexity)
        :param kwargs: Доп. параметры (temperature, max_tokens и т.д.)
        """
        messages = [
            {"role": "user", "content": prompt}
        ]

        api_key = API_KEYS[provider]

        amr = AiModelRepository(async_session_factory)
        model = await amr.get_by_name(provider)
        model_slug = model.slug if model else "default_model_slug"

        try:
            # LiteLLM сам понимает, какое API дергать, исходя из названия модели
            response = completion(
                model=model_slug,
                messages=messages,
                api_key=api_key,
                **kwargs
            )
            return response.choices[0].message.content

        except Exception as e:
            return f"Ошибка при вызове модели {provider}: {str(e)}"
