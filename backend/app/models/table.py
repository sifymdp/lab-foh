from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    floor_id: Mapped[str] = mapped_column(String(64), ForeignKey("floors.id"), index=True)
    section_id: Mapped[str] = mapped_column(String(64))  # soft ref — sections live in floors.sections JSON
    number: Mapped[str] = mapped_column(String(32))
    capacity: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))
    shape: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE")

    # canvas geometry
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    rotation: Mapped[float] = mapped_column(Float, default=0)

    # camera integration (Phase 2 — nullable until camera is configured)
    camera_url: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    # JSON: {"x":0,"y":0,"width":100,"height":100} — pixel coords in camera frame
    roi_coords: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    # counts consecutive person-detected scans; resets to 0 on status change
    # 3 consecutive scans → auto-advance to SEATED
    consecutive_person_scans: Mapped[int] = mapped_column(Integer, default=0)
    # counts consecutive empty scans during BILLING; 3 → DEPARTURE_ALERT
    consecutive_empty_scans: Mapped[int] = mapped_column(Integer, default=0)
    # ISO timestamp when table entered CLEANING (1-minute grace before dirty model runs)
    cleaning_started_at: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)

    # reservation auto-release: if status=RESERVED and reserved_until < now → AVAILABLE
    reserved_until: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)

    floor: Mapped["Floor"] = relationship("Floor", back_populates="tables")  # noqa: F821
