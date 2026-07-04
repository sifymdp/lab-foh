from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def migrate_schema() -> None:
    """Add Phase 2 columns to existing SQLite databases."""
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(tables)")).fetchall()
        col_names = {row[1] for row in rows}
        alters: list[str] = []
        if "roi_coords" not in col_names:
            alters.append("ALTER TABLE tables ADD COLUMN roi_coords VARCHAR(255)")
        if "consecutive_empty_scans" not in col_names:
            alters.append(
                "ALTER TABLE tables ADD COLUMN consecutive_empty_scans INTEGER DEFAULT 0"
            )
        if "cleaning_started_at" not in col_names:
            alters.append("ALTER TABLE tables ADD COLUMN cleaning_started_at VARCHAR(32)")
        for sql in alters:
            conn.execute(text(sql))
        conn.commit()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
