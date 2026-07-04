from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager_or_owner, require_menu_manager
from app.database import get_db
from app.models.user import User
from app.schemas.ai import AIEventCreate, AIEventOut, SeatingResponse, SeatingSuggestIn, ShiftReport
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/events", response_model=list[AIEventOut])
def list_events(
    resolved: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AIEventOut]:
    return ai_service.list_alerts(db, resolved=resolved, user_role=current_user.role)


@router.post("/events", response_model=AIEventOut)
def create_event(
    body: AIEventCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager_or_owner),
) -> AIEventOut:
    return ai_service.create_alert(db, body)


@router.patch("/events/{event_id}/resolve")
def resolve_event(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return ai_service.resolve_alert(db, event_id)


@router.post("/seating-suggest", response_model=SeatingResponse)
def seating_suggest(
    body: SeatingSuggestIn,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SeatingResponse:
    suggestion = ai_service.seating_suggest(db, body.party_size)
    return SeatingResponse(suggestion=suggestion, party_size=body.party_size)


@router.get("/reports/shift", response_model=ShiftReport)
def shift_report(
    date: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager_or_owner),
) -> ShiftReport:
    content, stats = ai_service.shift_report(db, date)
    return ShiftReport(report_date=stats.get("reportDate", date or ""), content=content, stats=stats)
