from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_posts():
    return {"message": "TODO: 帖子列表"}
