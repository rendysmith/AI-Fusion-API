# Viralix Backend

AI-powered content generation platform with video, image, and text-to-text capabilities.
Built with FastAPI, PostgreSQL, Redis, and async task processing via SQS.

## Architecture Overview

```
┌─────────────┐     ┌──────────┐     ┌─────────────┐
│  FastAPI App │────▶│  SQS     │────▶│  Worker     │
│  (REST API)  │     │  Queue   │     │  (Consumer) │
└──────┬───────┘     └──────────┘     └──────┬───────┘
       │                                      │
       ▼                                      ▼
┌──────────────┐                    ┌─────────────────┐
│  PostgreSQL  │                    │  Yandex S3 /     │
│  + Redis     │                    │  AI Providers    │
└──────────────┘                    └─────────────────┘
```

## Tech Stack

- **Framework:** FastAPI (async Python)
- **Database:** PostgreSQL 15 + SQLAlchemy 2.0 (async)
- **Cache/Queue:** Redis, ElasticMQ (SQS-compatible)
- **Auth:** Firebase Admin SDK
- **File Storage:** Yandex Object Storage (S3-compatible)
- **AI Providers:** GrsAI, Unifically, OpenAI, LiteLLM
- **Scheduler:** APScheduler
- **Containerization:** Docker + docker-compose

## Project Structure

```
viralix-backend/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── worker.py                  # Background task processor
│   ├── settings.py                # Pydantic settings (env vars)
│   ├── dependencies.py            # FastAPI dependency injection
│   ├── exceptions.py              # Custom exception hierarchy
│   ├── documentation.py           # OpenAPI description
│   ├── main_api_utils.py          # Cost calculation utilities
│   ├── constants.py               # Application constants
│   ├── database/
│   │   ├── base.py                # SQLAlchemy declarative base
│   │   ├── engine.py              # Async engine & session factory
│   │   ├── redis_db.py            # Redis connection pool
│   │   ├── main_models.py         # User, TelegramAuthToken, Price
│   │   ├── ai.py                  # AiModel, PriorityModel
│   │   ├── chat.py                # ChatSession, ChatMessage
│   │   ├── billing_models.py      # Product, Payment, Invoice
│   │   ├── subscription_models.py # SubscriptionPlan, UserSubscription
│   │   ├── task_models.py         # GenerationTask
│   │   ├── analytics_models.py    # DailySystemStats, CompletedTaskLog
│   │   ├── metric_models.py       # Visitor tracking
│   │   ├── video_template_models.py
│   │   └── repositories/          # Data access layer
│   │       ├── user_repository.py
│   │       ├── task_repository.py
│   │       ├── billing_repository.py
│   │       ├── subscription_repository.py
│   │       ├── plan_repository.py
│   │       ├── ai_model_repository.py
│   │       ├── analytics_repository.py
│   │       ├── metric_repository.py
│   │       ├── chat_repository.py
│   │       ├── plan_access_repository.py
│   │       ├── product_repository.py
│   │       ├── template_repository.py
│   │       ├── telegram_token_repository.py
│   │       ├── qr_session_repository.py
│   │       ├── circuit_breaker_repository.py
│   │       ├── system_repository.py
│   │       └── priority_model_repository.py
│   ├── schemas/                   # Pydantic models (request/response)
│   │   ├── common.py              # BaseModelParams, PromptMixin
│   │   ├── generation.py          # Sora, Veo, NanoBanana params
│   │   ├── auth.py                # Telegram auth schemas
│   │   ├── user.py                # User profile schemas
│   │   ├── billing.py             # Payment & checkout schemas
│   │   ├── subscription.py        # Subscription schemas
│   │   ├── plan.py                # Plan CRUD schemas
│   │   ├── ai.py                  # AI model schemas
│   │   ├── chat.py                # Chat session/message schemas
│   │   ├── admin.py               # Admin panel schemas
│   │   ├── admin_payment.py       # Admin payment listing
│   │   ├── admin_user_info.py     # Admin user details
│   │   ├── admin_user_traffic.py  # Traffic source schemas
│   │   ├── admin_system_status.py # System health schemas
│   │   ├── product.py             # Product CRUD schemas
│   │   ├── template.py            # Video template schemas
│   │   ├── analytics.py           # Analytics schemas
│   │   ├── metric.py              # Visitor tracking schemas
│   │   ├── transcribe.py          # Transcription schemas
│   │   ├── plan_access.py         # Plan-model access schemas
│   │   ├── referral.py            # Referral system schemas
│   │   └── __init__.py            # Schema exports
│   ├── routers/                   # API endpoint definitions
│   │   ├── auth.py                # /auth/* endpoints
│   │   ├── user.py                # /user/* endpoints
│   │   ├── ai_models.py           # /ai-models/* endpoints
│   │   ├── billing.py             # /billing/* endpoints
│   │   ├── subscription_plans.py  # /plans/* endpoints
│   │   ├── plan_access.py         # Admin plan-model access
│   │   ├── products.py            # /products/* endpoints
│   │   ├── templates.py           # /templates/* endpoints
│   │   ├── transcribe.py          # /transcribe/* endpoints
│   │   ├── telegram.py            # Telegram auth endpoints
│   │   ├── webhooks.py            # GetCourse webhook
│   │   ├── referral.py            # Referral registration
│   │   ├── metric.py              # Visitor tracking endpoints
│   │   ├── system.py              # System health endpoints
│   │   ├── storage.py             # S3 storage endpoints
│   │   ├── upload.py              # File upload endpoints
│   │   ├── text2text_llm.py       # Chat completions with streaming
│   │   ├── text2image_llm.py      # Image generation
│   │   ├── admin_users.py         # Admin user management
│   │   ├── admin_tasks.py         # Admin task management
│   │   ├── admin_analytics.py     # Admin analytics dashboard
│   │   ├── admin_billing.py       # Admin billing management
│   │   ├── admin_models.py        # Admin model/routing management
│   │   └── __init__.py
│   ├── services/                  # Business logic layer
│   │   ├── generation_service.py  # Task preparation & costing
│   │   ├── billing_service.py     # Product reward fulfillment
│   │   ├── text_billing_service.py# Text generation billing
│   │   ├── auth_service.py        # Firebase auth & user creation
│   │   ├── firebase_service.py    # Firebase SDK initialization
│   │   ├── getcourse_service.py   # GetCourse payment integration
│   │   ├── s3_uploader.py         # S3 media upload service
│   │   ├── t2t_service.py         # Text-to-text (LLM) service
│   │   ├── t2i_service.py         # Text-to-image service
│   │   ├── v2p_service.py         # Video-to-prompt (Gemini)
│   │   ├── referral_service.py    # Referral code (Hashids)
│   │   ├── scheduler.py           # APScheduler cron jobs
│   │   ├── redis_publisher.py     # Redis pub/sub notifications
│   │   ├── telegram_notifier.py   # Admin Telegram alerts
│   │   └── metric_service.py      # Reserved
│   │   └── providers/             # AI provider implementations
│   │       ├── grsai_provider.py  # GrsAI (Sora, Veo, NanoBanana)
│   │       ├── unifically_provider.py  # Unificantly (Sora fallback)
│   │       ├── openai_provider.py      # OpenAI Sora fallback
│   │       └── kie_ai_provider.py      # Legacy Kie AI provider
│   └── utils/
│       ├── image_processor.py     # Base64 image upload to S3
│       └── error_mapper.py        # User-friendly error messages
├── alembic/                       # Database migrations
│   ├── env.py
│   ├── versions/                  # Migration history
│   └── script.py.mako
├── Dockerfile
├── docker-compose.yml
├── elasticmq.conf
├── requirements.txt
├── .env.example                   # Environment template
└── README.md
```

## Quick Start

### Prerequisites

- Docker & docker-compose
- Python 3.11+ (for local development)

### Local Development

1. **Clone and configure:**

```bash
cp .env.example .env.local
# Edit .env.local with your API keys
```

2. **Start infrastructure:**

```bash
docker-compose up -d db redis minio elasticmq
```

3. **Run database migrations:**

```bash
alembic upgrade head
```

4. **Start the API server:**

```bash
uvicorn app.main:app --reload --port 8000
```

5. **Start the worker (in another terminal):**

```bash
python -m app.worker
```

### Full Docker Setup

```bash
docker-compose up --build
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL async connection string | ✅ |
| `REDIS_URL` | Redis connection string | ✅ |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Firebase credentials file path | ✅ |
| `YANDEX_ACCESS_KEY_ID` | S3 access key | ✅ |
| `YANDEX_SECRET_ACCESS_KEY` | S3 secret key | ✅ |
| `YANDEX_BUCKET_NAME` | S3 bucket name | ✅ |
| `YANDEX_STORAGE_ENDPOINT` | S3 endpoint URL | ✅ |
| `YANDEX_QUEUE_URL` | SQS queue URL | ✅ |
| `YANDEX_SQS_ACCESS_KEY_ID` | SQS access key | ✅ |
| `YANDEX_SQS_SECRET_ACCESS_KEY` | SQS secret key | ✅ |
| `OPENAI_API_KEY` | OpenAI API key (fallback) | ✅ |
| `GRSAI_API_KEY` | GrsAI API key | ✅ |
| `API_UNIFICALLY_TOKEN` | Unificantly API token | ✅ |
| `GEMINI_API_KEY` | Google Gemini API key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `PERPLEXITY_API_KEY` | Perplexity API key | Optional |
| `BOT_TOKEN` | Telegram bot token | Optional |
| `BOT_SECRET_KEY` | Bot internal auth key | ✅ |
| `ADMIN_TELEGRAM_ID` | Admin Telegram user ID | Optional |
| `GETCOURSE_API_KEY` | GetCourse API key | Optional |
| `GETCOURSE_ACCOUNT_NAME` | GetCourse account name | Optional |
| `CIRCUIT_BREAKER_TTL` | Circuit breaker TTL (seconds) | Optional |

## API Endpoints

### Core
- `POST /generate` — Submit a generation task
- `GET /tasks/{task_id}` — Get task status
- `GET /docs/elements` — API documentation (Stoplight Elements)

### Authentication
- `POST /auth/register` — Register new user
- `POST /auth/token` — Get auth token
- `POST /auth/telegram/init` — Initiate Telegram auth
- `POST /auth/telegram/webhook` — Telegram webhook handler

### Models & Generation
- `GET /ai-models` — List available models
- `GET /ai-models/category/{category}` — Filter by category
- `POST /ai-models/text-to-text` — Text-to-text chat completion
- `POST /ai-models/text-to-text/stream` — Streaming chat completion
- `POST /ai-models/image_generation` — Image generation
- `POST /ai-models/get_text_to_text` — Get T2T response

### User
- `GET /user/profile` — Get user profile
- `PUT /user/profile` — Update user profile
- `GET /user/balance` — Get user balance
- `GET /user/generations` — Generation history
- `GET /user/subscription` — User subscription details
- `GET /user/invoices` — User invoices

### Billing & Products
- `GET /products` — List products
- `POST /billing/checkout` — Create checkout
- `GET /billing/payment/{payment_id}` — Payment status
- `POST /billing/subscription/cancel` — Cancel subscription
- `POST /webhooks/getcourse` — GetCourse webhook

### Templates
- `GET /templates` — List video templates

### System
- `GET /system/health` — System health status
- `POST /metrics/track-visit` — Track visitor
- `POST /upload/image` — Upload image to S3
- `POST /transcribe` — Transcribe audio

### Admin
- `GET /admin/users` — List users
- `GET /admin/users/{uid}` — User details
- `POST /admin/users/{uid}/block` — Block/unblock user
- `GET /admin/tasks` — List all tasks
- `GET /admin/tasks/{task_id}` — Task details
- `GET /admin/analytics/metrics` — Dashboard metrics
- `GET /admin/analytics/report` — Analytics report
- `GET /admin/analytics/users-traffic` — User traffic sources
- `GET /admin/analytics/visitors` — Visitor log
- `GET /admin/billing/payments` — Payment listing
- `POST /admin/storefront` — Create/update AI models
- `POST /admin/routing` — Configure provider routing
- `POST /admin/plans` — Manage subscription plans
- `POST /admin/plan-access` — Plan-model access control
- `POST /admin/credits/bulk` — Bulk credit assignment

## Task Processing Flow

1. **Client** submits `POST /generate` with model parameters
2. **API** validates plan access, calculates cost, deducts balance
3. **Task** is created in PostgreSQL with `pending` status
4. **Message** is sent to SQS queue with task data
5. **Worker** polls SQS, processes the task:
   - Tries **primary provider** (GrsAI)
   - On failure, opens **circuit breaker** and tries **fallback** (Unifically)
   - On success, uploads result to S3
6. **Result** is saved to PostgreSQL, analytics are updated
7. **User** can poll `GET /tasks/{task_id}` for status

## Key Features

- **Circuit Breaker:** Automatic provider failover with configurable TTL
- **Concurrency Control:** Per-user and global task limits
- **Unlimited Plans:** Built-in delay factor for fair resource allocation
- **Multi-Provider:** GrsAI (primary), Unifically/OpenAI (fallback)
- **Provider Routing:** Priority-based backend selection via database
- **Real-time Updates:** Redis pub/sub for Telegram notifications
- **Admin Alerts:** Telegram notifications on critical errors
- **Analytics:** Per-user and system-wide usage tracking
- **Visitor Tracking:** UTM parameter analysis with conversion metrics
- **Referral System:** Hashids-based referral codes

## Contributing

1. Follow PEP 8 and PEP 257 standards
2. Add docstrings to all public methods
3. Use type hints throughout
4. Write tests for new functionality
5. Run `pytest` before submitting changes

## License

See [LICENSE](LICENSE)
