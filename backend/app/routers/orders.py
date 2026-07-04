from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.deps import bearer_scheme, get_current_user
from app.core.security import decode_token
from app.database import get_db
from app.models import TableQRCode
from app.models.user import User
from app.schemas.order import OrderCreate, OrderOut
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
def list_orders(
    table_id: str | None = Query(None),
    session_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[OrderOut]:
    return order_service.list_orders(db, table_id=table_id, session_id=session_id)


@router.post("", response_model=OrderOut)
def place_order(
    body: OrderCreate,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    table_token: str | None = Query(None, alias="token"),
) -> OrderOut:
    if credentials and credentials.credentials:
        user_id = decode_token(credentials.credentials)
        if not user_id or not db.get(User, user_id):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    elif table_token:
        qr = (
            db.query(TableQRCode)
            .filter(TableQRCode.token == table_token, TableQRCode.is_active.is_(True))
            .first()
        )
        if not qr:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid table token")
        if body.table_id and body.table_id != qr.table_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Table mismatch")
        body = body.model_copy(update={"table_id": qr.table_id})
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return order_service.create_order(db, body)
