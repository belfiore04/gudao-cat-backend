from fastapi import APIRouter

router = APIRouter()


@router.post("/identify")
def identify_cat():
    return {"message": "TODO: 拍照识猫"}
