from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.models.user import User
from app.schemas.recognition import RecognitionJobOut
from app.services.recognition import RecognitionQueueFull, recognition_service
from app.utils.deps import get_current_user

router = APIRouter()


@router.get("/health")
def recognition_health(current_user: User = Depends(get_current_user)):
    return recognition_service.snapshot()


@router.post("/jobs", response_model=RecognitionJobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_recognition_job(
    image: UploadFile = File(...),
    threshold: float | None = Form(None),
    current_user: User = Depends(get_current_user),
):
    try:
        image_path = recognition_service.save_upload(image.file, image.filename)
        return recognition_service.submit_recognition(
            image_path=image_path,
            filename=image.filename,
            user_id=current_user.id,
            threshold=threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except RecognitionQueueFull as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=RecognitionJobOut)
def get_recognition_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    job = recognition_service.get_job(job_id, current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="识别任务不存在")
    return job


@router.post("/gallery/rebuild", response_model=RecognitionJobOut, status_code=status.HTTP_202_ACCEPTED)
def rebuild_gallery(
    rebuild: bool = Query(True),
    current_user: User = Depends(get_current_user),
):
    try:
        return recognition_service.submit_gallery_build(
            user_id=current_user.id,
            rebuild=rebuild,
        )
    except RecognitionQueueFull as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
