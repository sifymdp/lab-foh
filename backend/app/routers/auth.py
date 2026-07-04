from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import AuthUserOut, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.email == body.email, User.is_active.is_(True)).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token, expires_at = create_access_token(user.id)
    return LoginResponse(
        access_token=token,
        expires_at=expires_at,
        user=AuthUserOut(id=user.id, name=user.name, email=user.email, role=user.role),
    )


@router.get("/me", response_model=AuthUserOut)
def me(user: User = Depends(get_current_user)) -> AuthUserOut:
    return AuthUserOut(id=user.id, name=user.name, email=user.email, role=user.role)
