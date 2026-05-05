from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.config import UPLOAD_DIR

router = APIRouter()

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_image(request: Request, image: UploadFile = File(...)):
    suffix = Path(image.filename or "").suffix.lower() or ".jpg"
    if suffix not in IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail="只支持图片文件")

    upload_dir = Path(UPLOAD_DIR) / "posts"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    path = upload_dir / filename

    content = await image.read()
    if not content:
        raise HTTPException(status_code=400, detail="图片内容为空")
    path.write_bytes(content)

    base_url = str(request.base_url).rstrip("/")
    return {"url": f"{base_url}/uploads/posts/{filename}"}
