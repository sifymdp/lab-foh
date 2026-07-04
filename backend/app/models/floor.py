from sqlalchemy import Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Floor(Base):
    __tablename__ = "floors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    width: Mapped[int] = mapped_column(Integer, default=1000)
    height: Mapped[int] = mapped_column(Integer, default=620)
    sections: Mapped[list] = mapped_column(JSON, default=list)
    labels: Mapped[list] = mapped_column(JSON, default=list)

    tables: Mapped[list["Table"]] = relationship(  # noqa: F821
        "Table", back_populates="floor", cascade="all, delete-orphan"
    )
