from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.cat import CatOut


JobStatus = Literal["queued", "running", "completed", "failed"]


class RecognitionMatch(BaseModel):
    cat_id: int
    cat_name: str
    distance: float
    photo_url: str | None = None
    cat: CatOut | None = None


class RecognitionResult(BaseModel):
    detected: bool
    accepted: bool = False
    decision: str
    top1: RecognitionMatch | None = None
    matches: list[RecognitionMatch] = []
    threshold: float
    timing: dict = {}


class RecognitionJobOut(BaseModel):
    id: str
    kind: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    filename: str | None = None
    user_id: int | None = None
    progress: dict = {}
    result: RecognitionResult | dict | None = None
    error: str | None = None
    finished_at: datetime | None = None

