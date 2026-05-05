from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.config import UPLOAD_DIR
from app.database import Base, engine
from app.models import *  # noqa: ensure all models are registered
from app.routers import auth, users, cats, recognition, posts, admin, uploads

# 自动建表（开发用，生产环境用 alembic）
Base.metadata.create_all(bind=engine)


def ensure_dev_schema():
    inspector = inspect(engine)
    if "posts" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("posts")}
    if "cat_id" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE posts ADD COLUMN cat_id INTEGER"))


ensure_dev_schema()

app = FastAPI(title="鼓捣猫呢 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(cats.router, prefix="/api/cats", tags=["猫咪档案"])
app.include_router(recognition.router, prefix="/api/recognition", tags=["猫咪识别"])
app.include_router(posts.router, prefix="/api/posts", tags=["社区帖子"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["文件上传"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "鼓捣猫呢 API is running"}
