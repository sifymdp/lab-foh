from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.models import Reservation, Table
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services.floor_service import _table_to_out
from app.services.table_service import record_history
from app.socket_manager import emit_sync


def _to_out(r: Reservation) -> ReservationOut:
    def fmt(dt: datetime) -> str:
        if dt.tzinfo is None:
            return dt.isoformat() + "Z"
        return dt.isoformat().replace("+00:00", "Z")

    return ReservationOut(
        id=r.id,
        table_id=r.table_id,
        guest_name=r.guest_name,
        party_size=r.party_size,
        reserved_for=fmt(r.reserved_for),
        reserved_until=fmt(r.reserved_until),
        status=r.status,
        notes=r.notes,
    )


def _emit_table_updated(table: Table) -> None:
    emit_sync("table_updated", _table_to_out(table).model_dump(by_alias=True), room=table.floor_id)


def list_reservations(db: Session) -> list[ReservationOut]:
    rows = db.query(Reservation).order_by(Reservation.reserved_for.desc()).all()
    return [_to_out(r) for r in rows]


def create_reservation(db: Session, payload: ReservationCreate, user_id: str | None) -> ReservationOut:
    table = db.get(Table, payload.table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if table.status not in ("AVAILABLE", "RESERVED"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Table not available")
    if payload.party_size > table.capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Party size exceeds capacity")

    reserved_for = datetime.fromisoformat(payload.reserved_for.replace("Z", "+00:00"))
    reserved_until = datetime.fromisoformat(payload.reserved_until.replace("Z", "+00:00"))

    reservation = Reservation(
        id=new_id(),
        table_id=payload.table_id,
        created_by=user_id,
        guest_name=payload.guest_name,
        party_size=payload.party_size,
        reserved_for=reserved_for,
        reserved_until=reserved_until,
        status="PENDING",
        notes=payload.notes,
    )
    old_status = table.status
    table.status = "RESERVED"
    table.reserved_until = payload.reserved_until
    db.add(reservation)
    record_history(db, table.id, old_status, "RESERVED", user_id)
    db.commit()
    db.refresh(reservation)
    db.refresh(table)
    _emit_table_updated(table)
    return _to_out(reservation)


def release_reservation(db: Session, reservation_id: str, user_id: str | None) -> ReservationOut:
    reservation = db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    table = db.get(Table, reservation.table_id)
    if table and table.status == "RESERVED":
        old = table.status
        table.status = "AVAILABLE"
        table.reserved_until = None
        record_history(db, table.id, old, "AVAILABLE", user_id)
    reservation.status = "RELEASED"
    db.commit()
    db.refresh(reservation)
    if table:
        db.refresh(table)
        _emit_table_updated(table)
    return _to_out(reservation)


def delete_reservation(db: Session, reservation_id: str, user_id: str | None) -> None:
    reservation = db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    table = db.get(Table, reservation.table_id)
    if table and table.status == "RESERVED":
        old = table.status
        table.status = "AVAILABLE"
        table.reserved_until = None
        record_history(db, table.id, old, "AVAILABLE", user_id)
    db.delete(reservation)
    db.commit()
    if table:
        db.refresh(table)
        _emit_table_updated(table)
