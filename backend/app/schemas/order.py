from app.schemas.common import CamelModel


class OrderItemIn(CamelModel):
    menu_item_id: str
    quantity: int = 1


class OrderCreate(CamelModel):
    table_id: str
    session_id: str | None = None
    items: list[OrderItemIn]


class OrderItemOut(CamelModel):
    id: str
    item_name: str
    unit_price: float
    quantity: int


class OrderOut(CamelModel):
    id: str
    session_id: str
    table_id: str
    placed_at: str
    status: str
    items: list[OrderItemOut]


class BillItemOut(CamelModel):
    item_name: str
    unit_price: float
    quantity: int
    line_total: float


class BillOut(CamelModel):
    id: str
    session_id: str
    subtotal: float
    total: float
    status: str
    generated_at: str
    paid_at: str | None = None
    items: list[BillItemOut]
