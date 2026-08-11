"""Match full-frame YOLO detections to per-table ROI rectangles.

Detections and saved roi_coords both live in raw-camera-resolution space, so
the overlap comparison needs no coordinate conversion.
"""

from __future__ import annotations

from app.config import settings
from app.core.yolo_models import TableStateDetection


def iou_over_roi(box: tuple[int, int, int, int], roi: dict[str, int]) -> float:
    """Overlap score between a detection box and the ROI rectangle.

    Detection boxes can be much larger than a table's ROI (a custom-model box
    spanning seated guests) or much smaller (a COCO cup or seated person), so
    plain IoU would punish valid matches in both directions. Score by whichever
    is better covered: the ROI by the box, or the box by the ROI.
    """
    x1, y1, x2, y2 = box
    rx, ry, rw, rh = roi["x"], roi["y"], roi["width"], roi["height"]
    ix1, iy1 = max(x1, rx), max(y1, ry)
    ix2, iy2 = min(x2, rx + rw), min(y2, ry + rh)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    intersection = iw * ih
    roi_area = max(rw * rh, 1)
    box_area = max((x2 - x1) * (y2 - y1), 1)
    return max(intersection / roi_area, intersection / box_area)


# When several detections overlap one ROI, a person at the table always wins
# over leftover tableware — "occupied" trumps "dirty" trumps "clean".
_LABEL_PRIORITY = ("occupied", "dirty", "clean")


def match_detection_for_roi(
    detections: list[tuple[int, int, int, int, TableStateDetection]],
    roi: dict[str, int],
    min_overlap: float | None = None,
) -> TableStateDetection | None:
    """Return the best detection overlapping the ROI, or None if none reaches
    ``min_overlap``. Higher-priority labels win over better-overlapping ones."""
    threshold = min_overlap if min_overlap is not None else settings.stream_roi_match_min_overlap
    best_by_label: dict[str, tuple[float, TableStateDetection]] = {}
    for x1, y1, x2, y2, detection in detections:
        score = iou_over_roi((x1, y1, x2, y2), roi)
        if score < threshold:
            continue
        current = best_by_label.get(detection.label)
        if current is None or score > current[0]:
            best_by_label[detection.label] = (score, detection)
    if not best_by_label:
        return None
    for label in _LABEL_PRIORITY:
        if label in best_by_label:
            return best_by_label[label][1]
    return max(best_by_label.values(), key=lambda item: item[0])[1]
