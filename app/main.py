import json
import logging

from aiobotocore.session import get_session
from fastapi import FastAPI, Depends, HTTPException, Request
from contextlib import asynccontextmanager


from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

from app.database.base import Base
from app.database.main_models import User
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.task_repository import TaskRepository
from app.database.engine import engine
from app import schemas
from app import dependencies
from app.database.repositories.user_repository import UserRepository
from app.dependencies import get_current_user
from app.documentation import API_DESCRIPTION
from app.schemas import TaskStatusResponse
from app.services.firebase_service import initialize_firebase
from app.services.generation_service import GenerationService
from app.settings import settings

from app.routers import auth as auth_router
from app.routers import user as user_router
from app.routers import ai_models as ai_models_router
from app.routers import templates as templates_router
from app.routers import subscription_plans as plans_router
from app.routers import plan_access as plan_access_router
from app.routers import admin_users as admin_users_router


import app.database.main_models
import app.database.analytics_models
import app.database.task_models
import app.database.billing_models


@asynccontextmanager
async def lifespan(app: FastAPI):

    initialize_firebase()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = get_session()

    async with session.create_client(
            's3',
            region_name=settings.YANDEX_REGION,
            endpoint_url=settings.YANDEX_STORAGE_ENDPOINT,
            aws_access_key_id=settings.YANDEX_ACCESS_KEY_ID,
            aws_secret_access_key=settings.YANDEX_SECRET_ACCESS_KEY
    ) as s3_client:

        app.state.s3_client = s3_client

        async with session.create_client(
                'sqs',
                region_name=settings.YANDEX_QUEUE_REGION,
                endpoint_url=settings.YANDEX_QUEUE_ENDPOINT,
                aws_access_key_id=settings.YANDEX_SQS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.YANDEX_SQS_SECRET_ACCESS_KEY
        ) as sqs_client:

            app.state.sqs_client = sqs_client
            logging.info("Successfully connected to Yandex Message Queue")

            yield


AUTH_DEPENDENCY = Depends(get_current_user)

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan
)


app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(ai_models_router.router)
app.include_router(ai_models_router.admin_router)

app.include_router(templates_router.router)
app.include_router(templates_router.admin_router)
app.include_router(plans_router.admin_router)
app.include_router(plan_access_router.admin_router)
app.include_router(admin_users_router.admin_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse, tags=["Tasks"])
async def get_task_status(
    task_id: str,
    task_repo: TaskRepository = Depends(dependencies.get_task_repository),
    user: User = AUTH_DEPENDENCY
):


    task = await task_repo.get_task(task_id)


    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this task"
        )

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        result=task.result,
        error=task.error
    )


@app.post("/generate", response_model=schemas.GenerateAcceptedResponse, status_code=status.HTTP_202_ACCEPTED,
          tags=["Core Logic"])
async def generate(
        request_data: schemas.GenerateRequest,
        request: Request,
        user: User = AUTH_DEPENDENCY,
        ai_model_repo: AiModelRepository = Depends(dependencies.get_ai_model_repository),
        user_repo: UserRepository = Depends(dependencies.get_user_repository),
        task_repo: TaskRepository = Depends(dependencies.get_task_repository)
):

    s3_client = request.app.state.s3_client

    service = GenerationService(
        user=user,
        ai_model_repo=ai_model_repo,
        user_repo=user_repo,
        s3_client=s3_client,
        task_repo=task_repo
    )

    task_id, task_message_body, new_balance = await service.prepare_generation_task(request_data.params)

    sqs_client = app.state.sqs_client

    await sqs_client.send_message(
        QueueUrl=settings.YANDEX_QUEUE_URL,
        MessageBody=json.dumps(task_message_body, default=str)
    )

    return schemas.GenerateAcceptedResponse(
        task_id=task_id,
        balance=float(new_balance)
    )



@app.get("/docs/elements", response_class=HTMLResponse, include_in_schema=False)
async def get_elements_docs():
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Main API V3</title>
        <script src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">
      </head>
      <body>
        <elements-api
          apiDescriptionUrl="/openapi.json" 
          router="hash"
          layout="sidebar"
        />
      </body>
    </html>
"""

