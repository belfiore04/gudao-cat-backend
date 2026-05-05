from datetime import datetime

from pydantic import BaseModel


class PostCreate(BaseModel):
    content: str
    cat_id: int | None = None
    images: list[str] | None = None
    video: str | None = None


class PostOut(BaseModel):
    id: int
    user_id: int
    cat_id: int | None = None
    content: str
    images: list | None = None
    video: str | None = None
    like_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    content: str


class CommentOut(BaseModel):
    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
