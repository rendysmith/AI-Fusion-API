"""Common Pydantic schemas used across the API."""

from pydantic import BaseModel, Field


class BaseModelParams(BaseModel):
    """Base parameters for model generation requests."""

    pass


class PromptMixin(BaseModel):
    """Mixin adding a prompt field."""

    prompt: str = Field(..., description="Основной промпт для генерации.")


class DeleteResponse(BaseModel):
    """Generic delete operation response."""

    success: bool


class IsAdminResponse(BaseModel):
    """Response indicating whether a user is an admin."""

    is_admin: bool
