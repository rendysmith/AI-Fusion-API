# Файл: app/schemas/__init__.py (ЗАМЕНИТЬ ВСЁ)

# --- common.py ---
from .common import (
    BaseModelParams,
    PromptMixin,
    DeleteResponse,
    IsAdminResponse
)

# --- generation.py ---
from .generation import (
    Sora2Params,
    Veo3QualityParams,
    Veo3FastParams,
    AnyModelParams,
    GenerateRequest,
    GenerateAcceptedResponse,
    TaskStatus,
    TaskStatusResponse,
    GenerationResultModel,
    GenerationHistoryItem,
    GenerationHistoryResponse
)

# --- analytics.py ---
from .analytics import (
    Balance,
    UserStatItem,
    DailyActivity,
    UserAnalyticsResponse
)

# --- auth.py ---
from .auth import (
    TelegramInitRequest,
    TelegramInitResponse,
    TelegramStatusResponse,
    TelegramWebhookPayload
)

# --- ai_model.py ---
from .ai_model import (
    AiModelBase,
    AiModelCreate,
    AiModelUpdate,
    AiModelResponse
)

# --- template.py ---
from .template import (
    VideoTemplateBase,
    VideoTemplateCreate,
    VideoTemplateUpdate,
    VideoTemplateResponse
)

# --- plan.py ---
from .plan import (
    PlanSchema,
    SubscriptionSchema,
    SubscriptionPlanBase,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionPlanResponse,
    AdminSubscriptionPlanResponse
)

# --- subscription.py ---
from .subscription import (
    SubscriptionDetailResponse,
    UserSubscriptionDetailResponse,
    AvailableModel,
    SubscriptionUsage
)


# --- user.py ---
from .user import (
    UserBalanceResponse,
    UserProfileResponse,
    UserProfileUpdateRequest
)

# --- admin.py ---
from .admin import (
    AdminUserResponse,
    AdminUserListResponse,
    BlockUserRequest,
    BlockUserResponse,
    UpdateSubscriptionRequest,
    UpdateSubscriptionResponse
)

# --- transcribe.py ---
from .transcribe import (
    TranscribeResponse
)

# --- product.py ---
from .product import (
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductResponse
)

# --- billing.py ---
from .billing import (
    CheckoutRequest,
    CheckoutResponse,
    GetCourseWebhook,
    PaymentStatusResponse,
    CanceledSubscriptionResponse,
    InvoiceResponse
)