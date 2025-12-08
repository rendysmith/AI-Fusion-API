import logging

logger = logging.getLogger(__name__)



ERROR_RULES = [

    (
        ["photorealistic people", "real person", "human face"],
        "⚠️ Данная модель запрещает загрузку изображений реальных людей (фотореализм). Пожалуйста, используйте сгенерированные или стилизованные лица."
    ),


    (
        ["nudity", "sexuality", "erotic", "nsfw", "sexual"],
        "🔞 Запрос отклонен фильтром безопасности (темы 18+, нагота). Пожалуйста, измените промпт или изображение."
    ),


    (
        ["cameo", "celebrity", "public figure", "famous"],
        "🚫 Запрещено упоминание конкретных личностей или знаменитостей, у которых нет разрешения (Cameo)."
    ),


    (
        ["third-party", "copyright", "intellectual property"],
        "©️ Запрос отклонен из-за сходства с защищенным авторским контентом."
    ),


    (
        ["upload image violation", "image_moderation"],
        "🖼️ Загруженное изображение не прошло проверку безопасности нейросети. Попробуйте другое фото."
    ),


    (
        ["content policies", "guardrails", "moderation", "safety", "censorship", "policy violation"],
        "🛡️ Запрос отклонен системой безопасности (Safety Guardrails). Попробуйте переформулировать запрос, сделав его более нейтральным."
    ),


    (
        ["timeout", "timed out"],
        "⏳ Время генерации истекло. Сервис перегружен, попробуйте позже."
    ),


    (
        ["500", "502", "503", "504", "429", "connection error", "connector"],
        "🔌 Серверы нейросети перегружены или недоступны. Пожалуйста, попробуйте через пару минут."
    )
]

MSG_UNKNOWN = "Произошла техническая ошибка. Мы уже разбираемся. Попробуйте изменить параметры."


def get_user_friendly_error(error: Exception) -> str:
    """
    Превращает техническую ошибку провайдера в понятный текст на русском.
    """

    error_str = str(error).lower()


    for keywords, user_message in ERROR_RULES:

        if any(key in error_str for key in keywords):
            return user_message

    if "400" in error_str:
        return "Некорректные параметры запроса. Возможно, ошибка в промпте или настройках."


    return MSG_UNKNOWN