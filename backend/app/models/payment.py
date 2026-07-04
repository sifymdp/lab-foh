from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Payment(Base):
    """One payment record per bill. Created when cash is tendered (staff tap)
    or when the Stripe webhook confirms success."""
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    bill_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("bills.id", ondelete="CASCADE"), unique=True, index=True
    )
    # CASH | STRIPE
    method: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    # Stripe PaymentIntent ID for card payments; cash receipt ref or NULL for cash
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    bill: Mapped["Bill"] = relationship("Bill", back_populates="payment")  # noqa: F821
    transactions: Mapped[list["PaymentTransaction"]] = relationship(  # noqa: F821
        "PaymentTransaction", back_populates="payment", cascade="all, delete-orphan"
    )


class PaymentTransaction(Base):
    """
    Log of every Stripe webhook event received for a payment.
    The stripe_event_id unique constraint is the idempotency key —
    a duplicate webhook for the same event is silently ignored.
    """
    __tablename__ = "payment_transactions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("payments.id", ondelete="CASCADE"), index=True
    )
    # Stripe event ID — unique prevents duplicate webhook processing
    stripe_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # e.g. payment_intent.succeeded, payment_intent.payment_failed
    event_type: Mapped[str] = mapped_column(String(80))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    payment: Mapped["Payment"] = relationship("Payment", back_populates="transactions")  # noqa: F821
