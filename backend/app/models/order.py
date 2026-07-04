from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    """
    One order round per QR submission (a guest can submit multiple rounds
    in one session — each gets its own Order row).
    Status flows: RECEIVED → PREPARING → READY → SERVED
    The wait-alert worker resets its clock on every new Order placed_at.
    """
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("dining_sessions.id", ondelete="CASCADE"), index=True
    )
    table_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tables.id", ondelete="CASCADE"), index=True
    )
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # RECEIVED | PREPARING | READY | SERVED
    status: Mapped[str] = mapped_column(String(20), default="RECEIVED")

    session: Mapped["DiningSession"] = relationship(  # noqa: F821
        "DiningSession", back_populates="orders"
    )
    items: Mapped[list["OrderItem"]] = relationship(  # noqa: F821
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
