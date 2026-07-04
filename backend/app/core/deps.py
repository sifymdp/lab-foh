from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.permissions import (
    can_edit_floor,
    can_manage_menu,
    can_manage_reservations,
    can_manage_users,
    normalize_role,
)
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def require_floor_editor(user: User = Depends(get_current_user)) -> User:
    if not can_edit_floor(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Floor edit not allowed")
    return user


def require_owner(user: User = Depends(get_current_user)) -> User:
    if not can_manage_users(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")
    return user


def require_manager_or_owner(user: User = Depends(get_current_user)) -> User:
    if normalize_role(user.role) not in ("OWNER", "MANAGER"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager access required")
    return user


def require_menu_manager(user: User = Depends(get_current_user)) -> User:
    if not can_manage_menu(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Menu management not allowed")
    return user


def require_reservations_access(user: User = Depends(get_current_user)) -> User:
    if not can_manage_reservations(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reservations access not allowed")
    return user
