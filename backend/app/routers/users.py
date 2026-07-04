from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_owner
from app.database import get_db
from app.models.user import User
from app.schemas.user import CreateUserIn, SetActiveIn, UserOut
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def get_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_owner),
) -> list[UserOut]:
    return user_service.list_users(db)


@router.post("", response_model=UserOut)
def create_user(
    body: CreateUserIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_owner),
) -> UserOut:
    return user_service.create_user(db, body)


@router.patch("/{user_id}/active", response_model=UserOut)
def set_active(
    user_id: str,
    body: SetActiveIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_owner),
) -> UserOut:
    return user_service.set_user_active(db, user_id, body.is_active)
