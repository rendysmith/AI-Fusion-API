"""Transcription Pydantic schemas."""

from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    """Transcription result."""

    text: str
