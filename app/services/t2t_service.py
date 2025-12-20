import logging
from typing import Tuple, Optional, Dict

from openai import AsyncOpenAI

from app.database.engine import async_session_factory
from app.database.repositories.chat_repository import ChatRepository
from app.schemas import ChatMessageCreate, ChatSessionCreate
from app.settings import settings
from app.database.repositories.priority_model_repository import PriorityModelRepository

logger = logging.getLogger(__name__)


class UniversalLLM:
    _clients: Dict[str, AsyncOpenAI] = {}

    def _get_provider_config(self, provider_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Конфигурация провайдеров.
        Возвращает (API Key, Base URL).
        """
        if provider_name == "Google":
            return settings.GEMINI_API_KEY, "https://generativelanguage.googleapis.com/v1beta/openai/"

        elif provider_name == "Grsai":
            return settings.GRSAI_API_KEY, "https://api.grsai.com/v1"

        elif provider_name in ["ChatGPT", "OpenAI"]:
            return settings.OPENAI_API_KEY, None

        return None, None

    async def _get_or_create_client(self, provider_name: str) -> Optional[AsyncOpenAI]:
        """Singleton для клиентов (чтобы не пересоздавать подключение)"""
        if provider_name in self._clients:
            return self._clients[provider_name]

        api_key, base_url = self._get_provider_config(provider_name)

        if not api_key:
            return None

        logger.info(f"⚡️ Init OpenAI Client for: {provider_name}")
        new_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._clients[provider_name] = new_client

        return new_client

    async def get_response(self, user_id: int, prompt: str, model_slug: str, session_id: int = None) -> Tuple[
        str, Optional[int]]:
        """
        Главный метод: Сессия -> История -> Роутинг -> Ответ
        """

        chat_repo = ChatRepository(async_session_factory)
        priority_repo = PriorityModelRepository(async_session_factory)

        current_session_id = session_id

        if current_session_id:
            session_obj = await chat_repo.get_session_by_id(current_session_id)
            if not session_obj or session_obj.user_id != user_id:
                current_session_id = None

        if not current_session_id:
            session_payload = ChatSessionCreate(
                user_id=user_id,
                model_slug=model_slug,
                chat_name=prompt[:40]
            )
            new_session = await chat_repo.create_session(session_payload)
            current_session_id = new_session.id

        messages = [{"role": "system", "content": "You are a helpful assistant."}]

        if session_id:
            history = await chat_repo.get_messages_by_session_id(current_session_id)
            for msg in history:
                messages.append({"role": msg.role, "content": msg.message_text})

        messages.append({"role": "user", "content": prompt})

        await chat_repo.create_message(ChatMessageCreate(
            session_id=current_session_id,
            role='user',
            message_text=prompt,
            token_count=len(prompt) // 4
        ))

        providers = await priority_repo.get_by_proveder_all(model_slug)
        if not providers:
            return "Ошибка: Провайдеры для модели не настроены.", current_session_id

        ai_text = None

        for prov in providers:
            provider_name = prov.provider
            client = await self._get_or_create_client(provider_name)

            if not client:
                continue

            try:

                response = await client.chat.completions.create(
                    model=model_slug,
                    messages=messages,
                    temperature=0.7
                )
                ai_text = response.choices[0].message.content
                if ai_text:
                    break

            except Exception as e:
                logger.warning(f"⚠️ Provider {provider_name} failed: {e}. Switching...")
                continue

        if not ai_text:
            return "Извините, все сервисы временно недоступны.", current_session_id

        await chat_repo.create_message(ChatMessageCreate(
            session_id=current_session_id,
            role='assistant',
            message_text=ai_text,
            token_count=len(ai_text) // 4
        ))

        return ai_text, current_session_id
