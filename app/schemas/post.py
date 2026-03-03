from datetime import datetime

from pydantic import BaseModel


class PostCreate(BaseModel):
    content: str
    images: list[str] | None = None
    video: str | None = None


class PostOut(BaseModel):
    id: int
    user_id: int
    content: str
    images: list | None = None
    video: str | None = None
    like_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
