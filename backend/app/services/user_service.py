import time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User
from app.schemas.user import CreateUserIn, UserOut


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


def list_users(db: Session) -> list[UserOut]:
    users = db.query(User).order_by(User.name).all()
    return [user_to_out(u) for u in users]


def create_user(db: Session, payload: CreateUserIn) -> UserOut:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    user = User(
        id=f"u-{int(time.time() * 1000)}",
        name=payload.name,
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_out(user)


def set_user_active(db: Session, user_id: str, is_active: bool) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user_to_out(user)
