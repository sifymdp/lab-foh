from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.permissions import normalize_role
from app.models import AIEvent
from app.schemas.ai import AIEventCreate, AIEventOut
from app.services.ollama_service import generate_text
from app.socket_manager import emit_sync

ROLE_FILTER: dict[str, list[str]] = {
    "WAITER": ["WAIT_ALERT", "DIRTY_ALERT"],
    "HOST": ["WAIT_ALERT", "SEATING_SUGGESTION"],
    "MANAGER": [
        "WAIT_ALERT",
        "DIRTY_ALERT",
        "DEPARTURE_ALERT",
        "SEATING_SUGGESTION",
        "SHIFT_REPORT",
    ],
    "OWNER": [
        "WAIT_ALERT",
        "DIRTY_ALERT",
        "DEPARTURE_ALERT",
        "SEATING_SUGGESTION",
        "SHIFT_REPORT",
    ],
}


def _alert_payload(event: AIEvent) -> dict:
    created = event.created_at
    if created.tzinfo is None:
        created_str = created.isoformat() + "Z"
    else:
        created_str = created.isoformat().replace("+00:00", "Z")
    return {
        "id": event.id,
        "eventType": event.event_type,
        "message": event.message,
        "targetRole": event.target_role,
        "tableId": event.table_id,
        "createdAt": created_str,
        "resolved": event.resolved,
    }


def _emit_ai_alert(db: Session, event: AIEvent) -> None:
    payload = _alert_payload(event)
    if event.table_id:
        from app.models import Table

        table = db.get(Table, event.table_id)
        if table:
            emit_sync("ai_alert", payload, room=str(table.floor_id))
            return
    from app.models import Floor

    floors = db.query(Floor).all()
    if floors:
        for floor in floors:
            emit_sync("ai_alert", payload, room=str(floor.id))
    else:
        emit_sync("ai_alert", payload, room="floor-1")


def _to_out(event: AIEvent) -> AIEventOut:
    created = event.created_at
    if created.tzinfo is None:
        created_str = created.isoformat() + "Z"
    else:
        created_str = created.isoformat().replace("+00:00", "Z")
    return AIEventOut(
        id=event.id,
        table_id=event.table_id,
        event_type=event.event_type,
        message=event.message,
        target_role=event.target_role,
        created_at=created_str,
        resolved=event.resolved,
    )


def create_alert(db: Session, payload: AIEventCreate) -> AIEventOut:
    event = AIEvent(
        id=new_id(),
        table_id=payload.table_id,
        event_type=payload.event_type,
        message=payload.message,
        target_role=payload.target_role,
        created_at=datetime.now(timezone.utc),
        resolved=False,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    _emit_ai_alert(db, event)
    return _to_out(event)


def list_alerts(db: Session, resolved: bool = False, user_role: str | None = None) -> list[AIEventOut]:
    q = db.query(AIEvent).filter(AIEvent.resolved == resolved)
    if user_role:
        normalized = normalize_role(user_role)
        if normalized in ROLE_FILTER:
            q = q.filter(AIEvent.event_type.in_(ROLE_FILTER[normalized]))
    rows = q.order_by(AIEvent.created_at.desc()).all()
    return [_to_out(r) for r in rows]


def resolve_alert(db: Session, event_id: str) -> dict[str, str | bool]:
    event = db.get(AIEvent, event_id)
    if not event:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    event.resolved = True
    db.commit()
    return {"id": event_id, "resolved": True}


def seating_suggest(db: Session, party_size: int) -> str:
    from app.models import Table

    tables = (
        db.query(Table)
        .filter(Table.status == "AVAILABLE", Table.capacity >= party_size)
        .order_by(Table.capacity.asc())
        .limit(6)
        .all()
    )
    if not tables:
        return (
            f"I couldn't find any open tables for a party of {party_size} right now. "
            "You may want to ask guests to wait a few minutes or combine smaller tables."
        )
    lines = [
        f"Table {t.number} seats {t.capacity} ({t.type.lower()} table)"
        for t in tables[:3]
    ]
    prompt = (
        f"A host needs seating for {party_size} guests. "
        f"Available options: {'; '.join(lines)}. "
        "Recommend the top 3 choices in plain conversational English with a short reason for each. "
        "Do not use JSON or bullet codes."
    )
    return generate_text(
        prompt,
        fallback=(
            f"For a party of {party_size}, I'd start with Table {tables[0].number} "
            f"which seats {tables[0].capacity} — it's the best fit without wasting space."
        ),
    )


def shift_report(db: Session, report_date: str | None = None) -> tuple[str, dict]:
    from app.models import DiningSession, Order

    today = report_date or datetime.now(timezone.utc).date().isoformat()
    sessions = db.query(DiningSession).all()
    orders = db.query(Order).all()
    stats = {
        "sessions": len(sessions),
        "orders": len(orders),
        "reportDate": today,
    }
    prompt = (
        f"Write a short plain-English shift summary paragraph for a restaurant manager. "
        f"Stats: {len(sessions)} dining sessions, {len(orders)} orders placed today. "
        "Sound natural, no JSON, no technical codes."
    )
    content = generate_text(
        prompt,
        fallback=(
            f"Tonight's shift saw {len(sessions)} seated parties and {len(orders)} orders "
            "through the floor. Service ran steadily with no major bottlenecks reported."
        ),
    )
    return content, stats
