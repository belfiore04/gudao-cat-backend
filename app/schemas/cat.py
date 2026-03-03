from datetime import datetime

from pydantic import BaseModel


class CatCreate(BaseModel):
    name: str
    habits: str | None = None
    location: str | None = None


class CatOut(BaseModel):
    id: int
    name: str
    habits: str | None = None
    location: str | None = None
    photos: list | None = None
    creator_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
