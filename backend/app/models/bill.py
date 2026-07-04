from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Bill(Base):
    """
    One bill per dining session. Created when guest taps Request Bill.
    Holds the Stripe PaymentIntent so we can check intent status and
    prevent double-charging if the webhook fires more than once.
    Status: OPEN → PAID
    """
    __tablename__ = "bills"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("dining_sessions.id", ondelete="CASCADE"), unique=True, index=True
    )
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))
    total: Mapped[float] = mapped_column(Numeric(10, 2))  # subtotal + tax + service charge
    # Stripe PaymentIntent ID — one per bill, prevents double-charge
    stripe_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_client_secret: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # OPEN | PAID
    status: Mapped[str] = mapped_column(String(20), default="OPEN")

    session: Mapped["DiningSession"] = relationship(  # noqa: F821
        "DiningSession", back_populates="bill"
    )
    payment: Mapped["Payment | None"] = relationship(  # noqa: F821
        "Payment", back_populates="bill", uselist=False
    )
