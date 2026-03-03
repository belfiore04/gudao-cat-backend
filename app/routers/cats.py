from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_cats():
    return {"message": "TODO: 猫咪列表"}
