import logging

logger = logging.getLogger(__name__)


MSG_SAFETY = "Запрос отклонен системой безопасности (Safety/NSFW). Пожалуйста, избегайте тем 18+, насилия и т.д."
MSG_TIMEOUT = "Генерация заняла слишком много времени. Попробуйте повторить запрос позже."
MSG_OVERLOAD = "Серверы ИИ перегружены. Пожалуйста, попробуйте через пару минут."
MSG_UNKNOWN = "Произошла техническая ошибка. Мы уже разбираемся. Попробуйте изменить параметры."


def get_user_friendly_error(error: Exception) -> str:
    """
    Превращает страшную техническую ошибку в понятный текст для юзера.
    """
    error_str = str(error).lower()


    if any(x in error_str for x in ["safety", "policy", "nsfw", "content_policy_violation", "censorship"]):
        return MSG_SAFETY


    if "400" in error_str:

        if any(x in error_str for x in ["sexual", "violence", "hate", "harassment"]):
            return MSG_SAFETY
        return "Некорректные параметры запроса. Попробуйте изменить промпт."


    if "timeout" in error_str or "timed out" in error_str:
        return MSG_TIMEOUT


    if any(x in error_str for x in ["500", "502", "503", "504", "429", "limit"]):
        return MSG_OVERLOAD


    if "connection" in error_str or "connector" in error_str:
        return MSG_OVERLOAD

    return MSG_UNKNOWN