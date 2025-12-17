import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

from app import schemas
from app.database.repositories.template_repository import TemplateRepository
from app.services.s3_uploader import S3UploaderService
from app.dependencies import (
    get_current_user,
    get_current_admin_user,
    get_template_repository,
    get_s3_uploader  # <--- Не забудь импортировать это!
)

router = APIRouter(
    prefix="/templates",
    tags=["Templates"]
)


@router.get(
    "",
    response_model=List[schemas.VideoTemplateResponse],
    summary="Get all video templates"
)
async def get_all_templates(repo: TemplateRepository = Depends(get_template_repository)):
    return await repo.get_all()


admin_router = APIRouter(
    prefix="/templates",
    tags=["Admin: Templates"],
    dependencies=[Depends(get_current_admin_user)]
)


@admin_router.post(
    "",
    response_model=schemas.VideoTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template (Upload video + thumbnail)"
)
async def create_template(
        # --- ФАЙЛЫ (Обязательные) ---
        video_file: UploadFile = File(...),
        thumbnail_file: UploadFile = File(...),

        # --- ПОЛЯ (Принимаем как Form, так как это Multipart запрос) ---
        title: str = Form(...),
        prompt: str = Form(...),

        # Опциональные поля
        views_count: Optional[str] = Form(None),
        platform_icon: Optional[str] = Form(None),
        row_number: int = Form(1),
        position: int = Form(1),

        # --- ЗАВИСИМОСТИ ---
        repo: TemplateRepository = Depends(get_template_repository),
        s3_uploader: S3UploaderService = Depends(get_s3_uploader)
):


    try:
        video_content = await video_file.read()
        video_ext = video_file.filename.split('.')[-1] if '.' in video_file.filename else "mp4"
        video_key = f"templates/videos/{uuid.uuid4()}.{video_ext}"

        video_url = await s3_uploader.upload_file(
            file_data=video_content,
            key=video_key,
            content_type=video_file.content_type or "video/mp4"
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to upload video: {e}")

    try:
        thumb_content = await thumbnail_file.read()
        thumb_ext = thumbnail_file.filename.split('.')[-1] if '.' in thumbnail_file.filename else "jpg"
        thumb_key = f"templates/thumbnails/{uuid.uuid4()}.{thumb_ext}"

        thumbnail_url = await s3_uploader.upload_file(
            file_data=thumb_content,
            key=thumb_key,
            content_type=thumbnail_file.content_type or "image/jpeg"
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to upload thumbnail: {e}")

    payload = schemas.VideoTemplateCreate(
        title=title,
        prompt=prompt,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        views_count=views_count,
        platform_icon=platform_icon,
        row_number=row_number,
        position=position
    )

    return await repo.create(payload)


@admin_router.put(
    "/{template_id}",
    response_model=schemas.VideoTemplateResponse
)
async def update_template(
        template_id: int,
        payload: schemas.VideoTemplateUpdate,
        repo: TemplateRepository = Depends(get_template_repository)
):

    template = await repo.update(template_id, payload)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return template


@admin_router.delete(
    "/{template_id}",
    response_model=schemas.DeleteResponse
)
async def delete_template(
        template_id: int,
        repo: TemplateRepository = Depends(get_template_repository)
):
    success = await repo.delete(template_id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return {"success": True}