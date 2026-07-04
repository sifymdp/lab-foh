# Import order matters — parent tables must be imported before child tables
# so SQLAlchemy resolves ForeignKey references correctly.

from app.models.user import User
from app.models.floor import Floor
from app.models.section import Section          # NEW
from app.models.table import Table
from app.models.reservation import Reservation
from app.models.status_history import StatusHistory
from app.models.menu_item import MenuItem
from app.models.session import DiningSession
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.bill import Bill
from app.models.payment import Payment, PaymentTransaction
from app.models.qr_code import TableQRCode
from app.models.cleaning import CleaningEvent, DepartureEvent  # NEW
from app.models.ai_event import AIEvent

__all__ = [
    "User",
    "Floor",
    "Section",
    "Table",
    "Reservation",
    "StatusHistory",
    "MenuItem",
    "DiningSession",
    "Order",
    "OrderItem",
    "Bill",
    "Payment",
    "PaymentTransaction",
    "TableQRCode",
    "CleaningEvent",
    "DepartureEvent",
    "AIEvent",
]
