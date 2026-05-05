from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cat import Cat
from app.models.post import Post
from app.models.user import User
from app.schemas.cat import CatOut
from app.schemas.post import PostOut
from app.schemas.user import UserOut
from app.utils.deps import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.get("/{user_id}/cats", response_model=list[CatOut])
def list_user_cats(user_id: int, db: Session = Depends(get_db)):
    return db.query(Cat).filter(Cat.creator_id == user_id).order_by(Cat.created_at.desc()).all()


@router.get("/{user_id}/posts", response_model=list[PostOut])
def list_user_posts(user_id: int, db: Session = Depends(get_db)):
    return db.query(Post).filter(Post.user_id == user_id).order_by(Post.created_at.desc()).all()
