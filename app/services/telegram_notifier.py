"""Telegram notification service for admin error alerts."""

import logging
import aiohttp
import json
from typing import Optional
from app.settings import settings

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096


def _truncate_text(text: str, limit: int) -> str:
    """Truncate text from the beginning if it exceeds the limit."""
    if len(text) <= limit:
        return text
    return "...(cut)...\n" + text[-(limit - 100):]


async def send_error_alert(
    task_data: dict,
    error: Exception,
    traceback_str: str,
    duration: float,
    primary_error: Optional[Exception] = None,
    custom_title: Optional[str] = None,
):
    """Send an error alert to the admin Telegram chat."""
    if not settings.BOT_TOKEN or not settings.ADMIN_TELEGRAM_ID:
        return

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    task_id = task_data.get("_id", "unknown")
    model = task_data.get("model", "unknown")
    user_id = task_data.get("user_id", "unknown")
    cost = task_data.get("cost", 0.0)

    params = task_data.get("params", {})
    params_str = json.dumps(params, indent=2, ensure_ascii=False)

    if len(params_str) > 500:
        params_str = params_str[:500] + "\n... (truncated)"

    primary_error_text = ""
    if primary_error:
        primary_error_text = (
            f"Primary Failed: {str(primary_error)[:200]}\n"
        )

    title = custom_title if custom_title else "WORKER CRITICAL ERROR"

    header = (
        f"{title}\n\n"
        f"Task: {task_id}\n"
        f"User: {user_id}\n"
        f"Model: {model}\n"
        f"Cost: {cost}\n"
        f"Duration: {duration:.2f}s\n"
        f"{primary_error_text}"
        f"Error: {str(error)[:300]}\n"
    )

    reserved_len = len(header) + len(params_str) + 100
    available_for_tb = MAX_MESSAGE_LENGTH - reserved_len

    if available_for_tb < 500:
        params_str = "(Params too long)"
        available_for_tb = MAX_MESSAGE_LENGTH - len(header) - 100

    tb_formatted = _truncate_text(traceback_str, available_for_tb)

    message = (
        f"{header}\n"
        f"Params:\n<pre>{params_str}</pre>\n\n"
        f"Traceback:\n<pre><code class='language-python'>{tb_formatted}</code></pre>"
    )

    payload = {
        "chat_id": settings.ADMIN_TELEGRAM_ID,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"Telegram Alert failed: {await resp.text()}")
    except Exception as e:
        logger.error(f"Telegram Alert connection error: {e}")
