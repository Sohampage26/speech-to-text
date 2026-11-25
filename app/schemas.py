from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TranscriptCreate(BaseModel):
    text: str = Field(min_length=1)
    duration_sec: float | None = None


class TranscriptUpdate(BaseModel):
    text: str = Field(min_length=1)


class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    duration_sec: float | None
    created_at: datetime
    updated_at: datetime


class TranscriptPage(BaseModel):
    items: list[TranscriptOut]
    total: int
