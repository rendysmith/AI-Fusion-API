"""Text-to-image service for generating images via multiple providers."""

import logging
import asyncio
from typing import Dict

import aiohttp
from litellm import image_generation

from app.database.engine import async_session_factory
from app.schemas import ChatMessageCreate, ChatSessionCreate
from app.settings import settings
from app.database.repositories.priority_model_repository import PriorityModelRepository

logger = logging.getLogger(__name__)


class UniversalImageGenerator:
    """Unified service for image generation via LiteLLM and custom providers."""

    async def lite_llm(self, api_key: str, model: str, prompt: str, **kwargs):
        """Generate an image using LiteLLM (DALL-E 3, Imagen, etc.)."""
        aspect_ratio = kwargs.get("aspect_ratio", "square")
        size_map = {
            "square": "1024x1024",
            "1:1": "1024x1024",
            "auto": "1024x1024",
            "landscape": "1792x1024",
            "16:9": "1792x1024",
            "portrait": "1024x1792",
            "9:16": "1024x1792",
        }

        final_size = size_map.get(aspect_ratio, "1024x1024")

        try:
            logger.info(
                f"[LiteLLM] Request to {model}: {prompt[:30]}... Size: {final_size}",
            )

            response = await asyncio.to_thread(
                image_generation,
                prompt=prompt,
                model=model,
                api_key=api_key,
                size=final_size,
                n=1,
            )

            if response and response.data:
                image_url = response.data[0].url
                logger.info(f"[LiteLLM] Success: {image_url}")
                return image_url
            else:
                return "LiteLLM returned empty response."

        except Exception as e:
            err_msg = str(e)
            logger.error(f"[LiteLLM] Error: {err_msg}")

            if "safety" in err_msg.lower() or "content_policy_violation" in err_msg.lower():
                return "Request rejected by safety policy."

            return f"Provider error: {err_msg}"

    async def _make_post_request(
        self, session: aiohttp.ClientSession, url: str,
        headers: Dict, payload: Dict,
    ) -> Dict:
        """Execute a POST request with error handling."""
        try:
            async with session.post(
                url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()

                if resp.status != 200:
                    error_msg = (
                        data.get("msg")
                        or data.get("error", {}).get("message")
                        or await resp.text()
                    )
                    raise Exception(f"API Error ({resp.status}): {error_msg}")

                return data
        except asyncio.TimeoutError:
            raise Exception("Timeout: server did not respond in time.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {e}")

    async def grsai(
        self, api_key: str, model: str, prompt: str, **kwargs,
    ) -> str:
        """Generate an image via Grsai API with polling."""
        aspect_ratio = kwargs.get("aspect_ratio", "auto")
        image_size = kwargs.get("image_size", "1K")
        urls = kwargs.get("urls", None)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        submit_url = "https://api.grsai.com/v1/draw/nano-banana"
        submit_payload = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "webHook": "-1",
            "shutProgress": False,
        }

        if image_size:
            submit_payload["imageSize"] = image_size

        if urls and len(urls) > 0:
            submit_payload["urls"] = urls

        try:
            async with aiohttp.ClientSession() as session:
                logger.info(f"Submitting task: {prompt[:50]}...")
                submit_response = await self._make_post_request(
                    session, submit_url, headers, submit_payload,
                )

                task_id = None
                if "data" in submit_response and isinstance(
                    submit_response["data"], dict,
                ):
                    task_id = submit_response["data"].get("id")
                else:
                    task_id = submit_response.get("id")

                if not task_id:
                    return (
                        f"Error: Failed to get task ID. "
                        f"Response: {submit_response}"
                    )

                logger.info(f"Task ID: {task_id}. Waiting for generation...")

                result_url = "https://api.grsai.com/v1/draw/result"
                result_payload = {"id": task_id}

                attempts = 0
                max_attempts = 45

                while attempts < max_attempts:
                    await asyncio.sleep(2)

                    try:
                        res_data = await self._make_post_request(
                            session, result_url, headers, result_payload,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error checking status: {e}. Retrying...",
                        )
                        attempts += 1
                        continue

                    data_block = res_data.get("data", res_data)
                    status = data_block.get("status")

                    if status == "succeeded":
                        results = data_block.get("results", [])
                        if results and len(results) > 0:
                            image_url = results[0].get("url")
                            return image_url
                        else:
                            return "Status success but results array is empty."

                    elif status == "failed":
                        reason = (
                            data_block.get("failure_reason")
                            or data_block.get("error")
                        )
                        return f"Generation failed. Reason: {reason}"

                    elif status in ("running", None):
                        attempts += 1
                    else:
                        return f"Unknown status: {status}"

                return "Timeout waiting for image generation."

        except Exception as e:
            return f"Critical error: {str(e)}"

    async def get_response(self, user_id, prompt, model_slug, **kwargs):
        """Universal method to call any image generation model."""
        api_keys = {
            "ChatGPT": [settings.OPENAI_API_KEY, self.lite_llm],
            "Google": [settings.GEMINI_API_KEY, self.lite_llm],
            "Grsai": [settings.GRSAI_API_KEY, self.grsai],
        }

        pmr = PriorityModelRepository(async_session_factory)
        providers = await pmr.get_by_proveder_all(model_slug)

        if len(providers) == 0:
            return f"No providers found for {model_slug}"

        for prov in providers:
            provider_name = prov.provider

            if provider_name not in api_keys:
                logger.error(
                    f"Provider {provider_name} in DB but not configured in code.",
                )
                continue

            api_key = api_keys[provider_name][0]
            connector_func = api_keys[provider_name][1]

            try:
                result_url = await connector_func(
                    api_key, model_slug, prompt, **kwargs,
                )

                if str(result_url).startswith(""):
                    logger.warning(
                        f"Generation returned error: {result_url}",
                    )
                    return result_url

                try:
                    chat_repo = PriorityModelRepository(async_session_factory)

                    session_payload = ChatSessionCreate(
                        user_id=user_id,
                        model_slug=model_slug,
                        chat_name=f"Image: {prompt[:20]}...",
                    )
                    new_session = await chat_repo.create_session(session_payload)

                    user_message = ChatMessageCreate(
                        session_id=new_session.id,
                        role="user",
                        message_text=prompt,
                        token_count=len(prompt) // 4,
                    )
                    await chat_repo.create_message(user_message)

                    ai_message = ChatMessageCreate(
                        session_id=new_session.id,
                        role="assistant",
                        message_text=result_url,
                        token_count=0,
                    )
                    await chat_repo.create_message(ai_message)

                except Exception as db_ex:
                    logger.error(f"Error saving to DB: {db_ex}")

                return result_url

            except Exception as ex:
                logger.error(
                    f"Error calling provider {provider_name}: {ex}",
                )
                continue

        return (
            f"Failed to generate image with any provider for {model_slug}"
        )
