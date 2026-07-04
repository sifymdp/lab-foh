"""Camera pipeline hooks for YOLO-based table monitoring (Phase 2)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_frame(_frame: Any, _table_id: str) -> dict[str, Any] | None:
    """Placeholder for per-frame analysis; returns optional alert payload."""
    return None


def run_scan_cycle(_db: Any) -> None:
    """Placeholder for periodic camera scan worker."""
    logger.debug("Camera pipeline scan cycle (stub)")
