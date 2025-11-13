import logging
from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form
)
from openai import AsyncOpenAI, BadRequestError

from app import schemas
from app.database.main_models import User
from app.dependencies import get_current_user
from app.settings import settings

router = APIRouter(prefix="/transcribe", tags=["Utilities"])


if settings.OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
else:
    openai_client = None
    logging.warning("OPENAI_API_KEY не найден. Эндпоинт /transcribe не будет работать.")


SUPPORTED_AUDIO_FORMATS = [
    "audio/webm",
    "audio/wav",
    "audio/mp3",
    "audio/ogg",
    "audio/mpeg"
]


@router.post(
    "",
    response_model=schemas.TranscribeResponse,
    summary="Transcribe audio using Whisper"
)
async def transcribe_audio(
        audio_file: UploadFile = File(..., alias="audio"),
        language: str = Form("ru"),
        user: User = Depends(get_current_user)
):

    if not openai_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcription service is not configured (missing OPENAI_API_KEY)."
        )

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio file provided"
        )

    if audio_file.content_type not in SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported audio format. Received: {audio_file.content_type}"
        )

    try:

        file_bytes = await audio_file.read()

        file_tuple = (audio_file.filename, file_bytes, audio_file.content_type)


        response = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=file_tuple,
            language=language
        )


        return {"text": response.text}

    except BadRequestError as e:

        logging.warning(f"Whisper BadRequestError: {e.message}")
        if "File too large" in str(e):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large (> 25 MB)"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Whisper API error: {e.message}"
        )

    except Exception as e:

        logging.error(f"Whisper 500 Error: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed"
        )