import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from app.database.main_models import User
from app.dependencies import AUTH_DEPENDENCY, get_s3_uploader
from app.services.s3_uploader import S3UploaderService

router = APIRouter(prefix="/upload", tags=["Upload"])


MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic"]


@router.post("/image", response_model=dict)
async def upload_image(
        file: UploadFile = File(...),
        user: User = AUTH_DEPENDENCY,
        s3_service: S3UploaderService = Depends(get_s3_uploader)
):
    """
    Принимает картинку (multipart/form-data), грузит в S3 и возвращает URL.
    """

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {ALLOWED_TYPES}"
        )


    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10MB)"
        )


    file_ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    s3_key = f"chat_uploads/{user.id}/{uuid.uuid4()}.{file_ext}"


    try:
        url = await s3_service.upload_file(
            file_data=file_bytes,
            key=s3_key,
            content_type=file.content_type
        )
        return {"url": url}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )