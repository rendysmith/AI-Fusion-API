import json
import logging

from aiobotocore.session import get_session
from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from typing import Tuple


from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

from app.database.main_models import Base, ApiKey, User
from app.database.repositories.task_repository import TaskRepository
from app.database.repositories.user_price_repository import UserPriceRepository
from app.database.repositories.user_repository import ApiKeyRepository
from app.database.engine import engine
from app.database.repositories.price_repository import PriceRepository
from app import schemas
from app import dependencies
from app.documentation import API_DESCRIPTION
from app.schemas import TaskStatusResponse
from app.services.generation_service import GenerationService
from app.settings import settings


AUTH_DEPENDENCY = Depends(dependencies.get_current_user_and_key)



@asynccontextmanager
async def lifespan(app: FastAPI):
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
                aws_access_key_id=settings.YANDEX_ACCESS_KEY_ID,
                aws_secret_access_key=settings.YANDEX_SECRET_ACCESS_KEY
        ) as sqs_client:

            app.state.sqs_client = sqs_client
            logging.info("Successfully connected to Yandex Message Queue")

            yield

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan
)

MODELS_WITH_DURATION_COST = settings.MODELS_WITH_DURATION_COST



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
    auth_data: Tuple[User, ApiKey] = AUTH_DEPENDENCY
):

    user, _ = auth_data

    task = await task_repo.get_task(task_id)


    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


    if task.user_telegram_id != user.telegram_id:
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
        auth_data: Tuple[User, ApiKey] = AUTH_DEPENDENCY,
        key_repo: ApiKeyRepository = Depends(dependencies.get_key_repository),
        price_repo: PriceRepository = Depends(dependencies.get_price_repository),
        user_price_repo: UserPriceRepository = Depends(dependencies.get_user_price_repository)
):

    user, api_key = auth_data

    service = GenerationService(
        user=user,
        api_key=api_key,
        key_repo=key_repo,
        price_repo=price_repo,
        user_price_repo=user_price_repo,
    )

    task_id, task_message_body = await service.prepare_generation_task(request_data.params)

    sqs_client = app.state.sqs_client

    await sqs_client.send_message(
        QueueUrl=settings.YANDEX_QUEUE_URL,
        MessageBody=json.dumps(task_message_body, default=str)
    )

    return schemas.GenerateAcceptedResponse(task_id=task_id)



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

