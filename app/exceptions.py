"""Custom exception hierarchy for AI provider errors."""


class AIProviderError(Exception):
    """Base exception for all AI provider errors."""

    pass


class FatalProviderError(AIProviderError):
    """Critical service error (500, Timeout, Rate Limit, Network Error).

    The worker should break the circuit and attempt a fallback.
    """

    pass


class UserValidationError(AIProviderError):
    """User-side validation error (NSFW, Content Policy, 400 error).

    The worker should mark the task as failed without affecting the circuit.
    """

    pass
