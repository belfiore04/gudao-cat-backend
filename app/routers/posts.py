from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cat import Cat
from app.models.comment import Comment
from app.models.like import Like
from app.models.post import Post
from app.models.user import User
from app.schemas.post import CommentCreate, CommentOut, PostCreate, PostOut
from app.utils.deps import get_current_user

router = APIRouter()


@router.get("/", response_model=list[PostOut])
def list_posts(db: Session = Depends(get_db)):
    return db.query(Post).order_by(Post.created_at.desc()).all()


@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    data: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.cat_id is not None:
        cat = db.query(Cat).filter(Cat.id == data.cat_id).first()
        if cat is None:
            raise HTTPException(status_code=404, detail="关联猫咪不存在")
    post = Post(
        user_id=current_user.id,
        cat_id=data.cat_id,
        content=data.content,
        images=data.images or [],
        video=data.video,
        like_count=0,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/like", response_model=PostOut)
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="帖子不存在")

    existing = (
        db.query(Like)
        .filter(Like.post_id == post_id, Like.user_id == current_user.id)
        .first()
    )
    if existing is None:
        db.add(Like(post_id=post_id, user_id=current_user.id))
        post.like_count = (post.like_count or 0) + 1
    else:
        db.delete(existing)
        post.like_count = max((post.like_count or 0) - 1, 0)

    db.commit()
    db.refresh(post)
    return post


@router.get("/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return post


@router.get("/{post_id}/comments", response_model=list[CommentOut])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


@router.post("/{post_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    comment = Comment(post_id=post_id, user_id=current_user.id, content=data.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
