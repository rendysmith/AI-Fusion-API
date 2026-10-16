"""Image processing utilities for base64-to-S3 upload."""

import base64
import uuid
import aiobotocore.client
from fastapi import HTTPException, status
from app import schemas


async def _process_single_image_string(
    item_string: str,
    s3_client: aiobotocore.client.BaseClient,
    bucket_name: str,
    endpoint_url: str,
) -> str:
    """Process a single image string: upload base64 to S3 or return URL as-is."""
    b64_data = None
    content_type = "image/jpeg"

    if item_string.strip().startswith("data:image"):
        try:
            header, b64_data = item_string.split(",", 1)
            content_type = header.split(":")[1].split(";")[0]
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 data URI format.",
            )

    elif not item_string.strip().startswith(("http://", "https://")):
        try:
            base64.b64decode(item_string, validate=True)
            b64_data = item_string
        except (base64.binascii.Error, ValueError):
            pass

    if b64_data:
        try:
            image_bytes = base64.b64decode(b64_data)

            ext_map = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
            }
            file_extension = ext_map.get(content_type, "jpg")

            file_name = f"uploads/{uuid.uuid4().hex}.{file_extension}"

            await s3_client.put_object(
                Bucket=bucket_name,
                Key=file_name,
                Body=image_bytes,
                ContentType=content_type,
            )

            s3_url = f"{endpoint_url}/{bucket_name}/{file_name}"
            return s3_url

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"S3 upload failed: {e}",
            )

    return item_string


async def process_and_upload_images(
    model_params: schemas.AnyModelParams,
    s3_client: aiobotocore.client.BaseClient,
    bucket_name: str,
    endpoint_url: str,
) -> schemas.AnyModelParams:
    """Process all image fields in model params, uploading base64 to S3."""
    image_field_keys = ["image_url", "image_urls"]

    for key in image_field_keys:
        if not hasattr(model_params, key):
            continue

        value = getattr(model_params, key)
        if not value:
            continue

        if isinstance(value, list):
            processed_urls = []
            for item in value:
                s3_url = await _process_single_image_string(
                    item, s3_client, bucket_name, endpoint_url,
                )
                processed_urls.append(s3_url)
            setattr(model_params, key, processed_urls)

        elif isinstance(value, str):
            s3_url = await _process_single_image_string(
                value, s3_client, bucket_name, endpoint_url,
            )
            setattr(model_params, key, s3_url)

    return model_params
