from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    cat_id: Mapped[int | None] = mapped_column(ForeignKey("cats.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    images: Mapped[list | None] = mapped_column(JSON, default=list)
    video: Mapped[str | None] = mapped_column(String(500))
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    author: Mapped["User"] = relationship(back_populates="posts")
    cat: Mapped["Cat | None"] = relationship()
    comments: Mapped[list["Comment"]] = relationship(back_populates="post")
