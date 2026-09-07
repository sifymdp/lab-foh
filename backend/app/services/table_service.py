import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.status_machine import ACTIVE_SESSION_STATUSES, is_valid_transition
from app.models import DiningSession, StatusHistory, Table
from app.schemas.floor import CreateTableIn, TableOut, TablePatchIn
from app.services.floor_service import get_current_floor, _table_to_out
from app.socket_manager import sio


def _emit_table_updated(table: Table) -> None:
    sio.emit_sync(
        "table_updated",
        {
            "id": table.id,
            "status": table.status,
            "floor_id": table.floor_id,
            "number": table.number,
        },
        room=str(table.floor_id),
    )


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _on_status_change(table: Table, old_status: str, new_status: str) -> None:
    """Reset camera scan counters and edge-triggered alert flags; stamp cleaning start time."""
    if old_status != new_status:
        table.consecutive_person_scans = 0
        table.consecutive_empty_scans = 0
        # Re-arm one-shot alerts: each occurrence of BILLING/CLEANING gets its
        # own alert cycle, so leaving the status resets the flags.
        table.dirty_alert_sent = False
        table.dirty_escalated = False
        table.departure_alert_sent = False
    if new_status == "CLEANING":
        table.cleaning_started_at = _iso_now()
    elif old_status == "CLEANING" and new_status != "CLEANING":
        table.cleaning_started_at = None


def get_table(db: Session, table_id: str) -> Table:
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return table


def active_session_for_table(db: Session, table_id: str) -> DiningSession | None:
    return (
        db.query(DiningSession)
        .filter(
            DiningSession.table_id == table_id,
            DiningSession.status.in_(ACTIVE_SESSION_STATUSES),
        )
        .first()
    )


def record_history(
    db: Session,
    table_id: str,
    from_status: str | None,
    to_status: str,
    user_id: str | None,
    session_id: str | None = None,
) -> None:
    db.add(
        StatusHistory(
            id=new_id(),  # uuid4 — no millisecond collision risk
            table_id=table_id,
            session_id=session_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=user_id,
            changed_at=datetime.now(timezone.utc),
        )
    )


def find_available_tables(db: Session, party_size: int) -> list[TableOut]:
    """Available tables that seat at least ``party_size``, best-fit first.

    Best-fit = the smallest-capacity table that still fits, so a party of 2
    isn't handed an 8-top while smaller tables sit empty. Ties break by table
    number for a stable, predictable order.
    """
    size = max(party_size, 1)
    tables = (
        db.query(Table)
        .filter(Table.status == "AVAILABLE", Table.capacity >= size)
        .all()
    )

    def sort_key(t: Table):
        try:
            num = int(t.number)
        except (TypeError, ValueError):
            num = 10**9
        return (t.capacity, num, str(t.number))

    tables.sort(key=sort_key)
    return [_table_to_out(t) for t in tables]


def update_table(db: Session, table_id: str, patch: TablePatchIn) -> TableOut:
    table = get_table(db, table_id)
    data = patch.model_dump(exclude_unset=True, by_alias=False)
    old_status = table.status
    # Enforce the status machine on this general-purpose update path too, so a
    # direct table PUT can't bypass it and jump a table into an invalid state.
    if "status" in data and data["status"] != old_status:
        if not is_valid_transition(old_status, data["status"]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid transition from {old_status} to {data['status']}",
            )
    if "roi_coords" in data:
        # roi_coords arrives as a dict (or None) from the RectBounds schema field,
        # but the DB column stores it as a JSON string — convert before saving.
        roi = data["roi_coords"]
        if hasattr(roi, "model_dump"):
            roi = roi.model_dump()
        data["roi_coords"] = json.dumps(roi) if roi is not None else None
    for key, val in data.items():
        setattr(table, key, val)
    if "status" in data and data["status"] != old_status:
        _on_status_change(table, old_status, data["status"])
    db.commit()
    db.refresh(table)
    if "status" in data and data["status"] != old_status:
        _emit_table_updated(table)
    return _table_to_out(table)


def patch_table_status(
    db: Session, table_id: str, new_status: str, user_id: str | None
) -> TableOut:
    table = get_table(db, table_id)
    if not is_valid_transition(table.status, new_status):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid transition from {table.status} to {new_status}",
        )
    session = active_session_for_table(db, table_id)
    if new_status == "SEATED" and session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Table already has an active session",
        )
    old = table.status
    table.status = new_status
    _on_status_change(table, old, new_status)
    if session:
        session.status = new_status
    record_history(db, table_id, old, new_status, user_id, session.id if session else None)
    db.commit()
    db.refresh(table)
    _emit_table_updated(table)
    return _table_to_out(table)


def add_table(db: Session, payload: CreateTableIn) -> TableOut:
    floor = get_current_floor(db)
    w = payload.width if payload.width is not None else (64 if payload.shape == "CIRCLE" else 88)
    h = payload.height if payload.height is not None else (64 if payload.shape == "CIRCLE" else 72)
    table = Table(
        id=new_id(),  # uuid4
        floor_id=floor.id,
        section_id=payload.section_id,
        number=payload.number,
        capacity=payload.capacity,
        type=payload.type,
        shape=payload.shape,
        status="AVAILABLE",
        x=payload.x if payload.x is not None else 200,
        y=payload.y if payload.y is not None else 200,
        width=w,
        height=h,
        rotation=0,
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return _table_to_out(table)


def delete_table(db: Session, table_id: str) -> None:
    if active_session_for_table(db, table_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove table with an active session. Release the table first.",
        )
    table = get_table(db, table_id)
    db.query(DiningSession).filter(DiningSession.table_id == table_id).delete()
    db.delete(table)
    db.commit()
