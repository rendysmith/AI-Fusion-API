class AIProviderError(Exception):
    """Базовый класс для всех ошибок провайдеров"""
    pass


class FatalProviderError(AIProviderError):
    """
    Критическая ошибка сервиса (500, Timeout, Rate Limit, Network Error).
    Воркер должен разорвать цепь и попробовать Fallback.
    """
    pass


class UserValidationError(AIProviderError):
    """
    Ошибка валидации со стороны пользователя (NSFW, Content Policy, ошибка 400).
    Воркер должен просто пометить задачу как failed, не трогая цепь.
    """
    pass