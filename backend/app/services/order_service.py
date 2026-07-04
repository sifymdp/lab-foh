from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.status_machine import is_valid_transition
from app.models import Bill, DiningSession, MenuItem, Order, OrderItem, Table
from app.schemas.order import BillOut, OrderCreate, OrderItemOut, OrderOut
from app.services.floor_service import _table_to_out
from app.services.table_service import active_session_for_table, record_history
from app.socket_manager import emit_sync


def _fmt_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat().replace("+00:00", "Z")


def _order_to_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        session_id=order.session_id,
        table_id=order.table_id,
        placed_at=_fmt_dt(order.placed_at),
        status=order.status,
        items=[
            OrderItemOut(
                id=i.id,
                item_name=i.item_name,
                unit_price=float(i.unit_price),
                quantity=i.quantity,
            )
            for i in order.items
        ],
    )


def _emit_table_updated(table: Table) -> None:
    emit_sync("table_updated", _table_to_out(table).model_dump(by_alias=True), room=table.floor_id)


def list_orders(
    db: Session, table_id: str | None = None, session_id: str | None = None
) -> list[OrderOut]:
    q = db.query(Order)
    if table_id:
        q = q.filter(Order.table_id == table_id)
    if session_id:
        q = q.filter(Order.session_id == session_id)
    rows = q.order_by(Order.placed_at.desc()).all()
    return [_order_to_out(o) for o in rows]


def create_order(db: Session, payload: OrderCreate) -> OrderOut:
    table = db.get(Table, payload.table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    session = None
    if payload.session_id:
        session = db.get(DiningSession, payload.session_id)
    if not session:
        session = active_session_for_table(db, payload.table_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active session for table")

    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must include items")

    now = datetime.now(timezone.utc)
    order = Order(
        id=new_id(),
        session_id=session.id,
        table_id=payload.table_id,
        placed_at=now,
        status="RECEIVED",
    )
    db.add(order)
    db.flush()

    for line in payload.items:
        menu_item = db.get(MenuItem, line.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        db.add(
            OrderItem(
                id=new_id(),
                order_id=order.id,
                menu_item_id=menu_item.id,
                item_name=menu_item.name,
                unit_price=float(menu_item.price),
                quantity=line.quantity,
            )
        )

    if table.status == "SEATED" and is_valid_transition("SEATED", "ACTIVE"):
        old = table.status
        table.status = "ACTIVE"
        session.status = "ACTIVE"
        record_history(db, table.id, old, "ACTIVE", None, session.id)

    db.commit()
    db.refresh(order)
    db.refresh(table)

    item_count = sum(line.quantity for line in payload.items)
    total_amount = round(
        sum(float(i.unit_price) * i.quantity for i in order.items),
        2,
    )
    emit_sync(
        "order_placed",
        {
            "tableId": table.id,
            "tableNumber": table.number,
            "floorId": table.floor_id,
            "itemCount": item_count,
            "totalAmount": total_amount,
        },
        room=str(table.floor_id),
    )
    _emit_table_updated(table)
    return _order_to_out(order)


def request_bill(db: Session, session_id: str, user_id: str | None) -> BillOut:
    session = db.get(DiningSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    table = db.get(Table, session.table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    existing = db.query(Bill).filter(Bill.session_id == session_id).first()
    if existing:
        return get_bill(db, session_id)

    items: list[OrderItem] = []
    for order in session.orders:
        items.extend(order.items)
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No order items to bill")

    subtotal = sum(float(i.unit_price) * i.quantity for i in items)
    total = round(subtotal, 2)
    now = datetime.now(timezone.utc)

    bill = Bill(
        id=new_id(),
        session_id=session_id,
        subtotal=subtotal,
        total=total,
        generated_at=now,
        status="OPEN",
    )
    db.add(bill)
    session.requested_bill_at = now

    if is_valid_transition(table.status, "BILLING"):
        old = table.status
        table.status = "BILLING"
        session.status = "BILLING"
        record_history(db, table.id, old, "BILLING", user_id, session.id)

    db.commit()
    db.refresh(bill)
    db.refresh(table)
    _emit_table_updated(table)
    return get_bill(db, session_id)


def get_bill(db: Session, session_id: str) -> BillOut:
    bill = db.query(Bill).filter(Bill.session_id == session_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    session = db.get(DiningSession, session_id)
    line_items = []
    for order in session.orders if session else []:
        for item in order.items:
            line_items.append(
                {
                    "item_name": item.item_name,
                    "unit_price": float(item.unit_price),
                    "quantity": item.quantity,
                    "line_total": round(float(item.unit_price) * item.quantity, 2),
                }
            )

    from app.schemas.order import BillItemOut

    return BillOut(
        id=bill.id,
        session_id=bill.session_id,
        subtotal=float(bill.subtotal),
        total=float(bill.total),
        status=bill.status,
        generated_at=_fmt_dt(bill.generated_at),
        paid_at=_fmt_dt(bill.paid_at) if bill.paid_at else None,
        items=[BillItemOut(**li) for li in line_items],
    )


def mark_paid(db: Session, session_id: str, user_id: str | None) -> BillOut:
    session = db.get(DiningSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    bill = db.query(Bill).filter(Bill.session_id == session_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    table = db.get(Table, session.table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    now = datetime.now(timezone.utc)
    bill.status = "PAID"
    bill.paid_at = now

    if is_valid_transition(table.status, "PAID"):
        old = table.status
        table.status = "PAID"
        session.status = "PAID"
        record_history(db, table.id, old, "PAID", user_id, session.id)

    if is_valid_transition(table.status, "CLEANING"):
        old = table.status
        table.status = "CLEANING"
        session.status = "CLEANING"
        record_history(db, table.id, old, "CLEANING", user_id, session.id)

    db.commit()
    db.refresh(bill)
    db.refresh(table)

    bill_out = get_bill(db, session_id)
    emit_sync("payment_confirmed", bill_out.model_dump(by_alias=True), room=table.floor_id)
    _emit_table_updated(table)
    return bill_out
