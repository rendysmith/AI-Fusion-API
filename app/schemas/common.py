from pydantic import BaseModel, Field, ConfigDict


class BaseModelParams(BaseModel):
    pass

class PromptMixin(BaseModel):
    prompt: str = Field(..., description="Основной промпт для генерации.")


class DeleteResponse(BaseModel):
    success: bool

class IsAdminResponse(BaseModel):
    is_admin: bool