from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CatFeature(Base):
    __tablename__ = "cat_features"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cat_id: Mapped[int] = mapped_column(ForeignKey("cats.id"))
    embedding: Mapped[list] = mapped_column(JSON)
    photo_url: Mapped[str | None] = mapped_column(String(500))

    cat: Mapped["Cat"] = relationship(back_populates="features")
