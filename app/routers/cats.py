from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cat import Cat
from app.models.user import User
from app.schemas.cat import CatCreate, CatOut
from app.utils.deps import get_current_user

router = APIRouter()


@router.get("/", response_model=list[CatOut])
def list_cats(db: Session = Depends(get_db)):
    return db.query(Cat).order_by(Cat.created_at.desc()).all()


@router.post("/", response_model=CatOut, status_code=status.HTTP_201_CREATED)
def create_cat(
    data: CatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = Cat(
        name=data.name,
        habits=data.habits,
        location=data.location,
        photos=[],
        creator_id=current_user.id,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/{cat_id}", response_model=CatOut)
def get_cat(cat_id: int, db: Session = Depends(get_db)):
    cat = db.query(Cat).filter(Cat.id == cat_id).first()
    if cat is None:
        raise HTTPException(status_code=404, detail="猫咪不存在")
    return cat
