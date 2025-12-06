from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Set, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.production', env_file_encoding='utf-8', extra='ignore')

    APP_TITLE: str = "Main API v3"
    APP_VERSION: str = "3.0.0"

    WORKER_MAX_CONCURRENT_TASKS: int = 30

    WORKER_ID: str = Field('main-1')

    MODELS_WITH_DURATION_COST: Set[str] = Field(default_factory=lambda: {"video-model"})

    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ['*', '0.0.0.0'])

    GETCOURSE_API_KEY: str
    GETCOURSE_ACCOUNT_NAME: str
    GETCOURSE_WEBHOOK_SECRET: str = "my-super-secret-key-123"

    API_UNIFICALLY_TOKEN: str

    GETCOURSE_ADMIN_EMAIL: str

    FRONTEND_DOMAIN: str

    KIE_AI: str

    OPENAI_API_KEY: str
    CIRCUIT_BREAKER_TTL: int = 300

    DATABASE_URL: str

    BOT_SECRET_KEY: str

    ADMIN_TELEGRAM_ID: int

    BOT_TOKEN: str

    REDIS_URL: str


    YANDEX_ACCESS_KEY_ID: str
    YANDEX_SECRET_ACCESS_KEY: str
    YANDEX_BUCKET_NAME: str
    YANDEX_REGION: str
    YANDEX_STORAGE_ENDPOINT: str



    YANDEX_QUEUE_REGION: str
    YANDEX_QUEUE_ENDPOINT: str
    YANDEX_QUEUE_URL: str
    YANDEX_DLQ_URL: str

    YANDEX_SQS_ACCESS_KEY_ID: str
    YANDEX_SQS_SECRET_ACCESS_KEY: str

    FIREBASE_SERVICE_ACCOUNT_PATH: str

    FIREBASE_PHANTOM_EMAIL_DOMAIN: str

    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    GEMINI_API_KEY: str
    PERPLEXITY_API_KEY: str

settings = Settings()