from datetime import datetime

from pydantic import BaseModel


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    avatar: str | None = None
    bio: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
