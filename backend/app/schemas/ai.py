from app.schemas.common import CamelModel


class AIEventOut(CamelModel):
    id: str
    table_id: str | None = None
    event_type: str
    message: str
    target_role: str | None = None
    created_at: str
    resolved: bool


class AIEventCreate(CamelModel):
    event_type: str
    message: str
    target_role: str | None = None
    table_id: str | None = None


class SeatingSuggestIn(CamelModel):
    party_size: int


class SeatingResponse(CamelModel):
    suggestion: str
    party_size: int


class ShiftReport(CamelModel):
    report_date: str
    content: str
    stats: dict
