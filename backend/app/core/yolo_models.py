"""Global YOLO model holders — loaded once at app startup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.config import settings

if TYPE_CHECKING:
    from ultralytics import YOLO

logger = logging.getLogger(__name__)

person_model: YOLO | None = None
dirty_model: YOLO | None = None

DIRTY_CLASSES = {"plate", "bowl", "cup", "wine glass", "bottle"}
CUTLERY_CLASSES = {"fork", "knife", "spoon"}


def load_models() -> bool:
    """Load both YOLO models. Returns False if camera pipeline should stay disabled."""
    global person_model, dirty_model

    if not settings.camera_enabled:
        logger.info("Camera pipeline disabled (CAMERA_ENABLED=false)")
        return False

    try:
        from ultralytics import YOLO as YOLOClass
    except ImportError:
        logger.warning("ultralytics not installed — camera pipeline disabled")
        return False

    try:
        logger.info("Loading person detection model: %s", settings.yolo_person_model)
        person_model = YOLOClass(settings.yolo_person_model)

        logger.info("Loading cleanliness model: %s", settings.yolo_dirty_model_path)
        dirty_model = YOLOClass(settings.yolo_dirty_model_path)
        return True
    except Exception:
        logger.exception("Failed to load YOLO models — camera pipeline disabled")
        person_model = None
        dirty_model = None
        return False


def unload_models() -> None:
    global person_model, dirty_model
    person_model = None
    dirty_model = None


def count_persons(results: Any, threshold: float | None = None) -> int:
    """Count person detections above confidence threshold."""
    if person_model is None or not results or not results[0].boxes:
        return 0
    thresh = threshold if threshold is not None else settings.person_confidence_threshold
    return sum(
        1
        for box in results[0].boxes
        if person_model.names[int(box.cls)] == "person" and float(box.conf) > thresh
    )


def compute_dirty_score(results: Any, threshold: float | None = None) -> float:
    """
    Compute dirty signal from cleanliness model results.

    Supports our trained binary model (clean / dirty) and dish-level models
    with cutlery discounted at 0.2× confidence.
    """
    if dirty_model is None or not results or not results[0].boxes:
        return 0.0

    thresh = threshold if threshold is not None else settings.dirty_confidence_threshold
    class_names = {v.lower() for v in dirty_model.names.values()}
    dirty_score = 0.0

    for box in results[0].boxes:
        class_name = dirty_model.names[int(box.cls)].lower()
        confidence = float(box.conf)
        if confidence < thresh:
            continue

        if "dirty" in class_names and "clean" in class_names:
            if class_name == "dirty":
                dirty_score += confidence
        else:
            if class_name in DIRTY_CLASSES:
                dirty_score += confidence
            elif class_name in CUTLERY_CLASSES:
                dirty_score += confidence * 0.2

    return dirty_score
