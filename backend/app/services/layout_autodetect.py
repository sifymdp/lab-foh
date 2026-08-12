"""Auto-detect a whole floor layout from a ceiling camera.

Rewires the detection output that already powers the live pipeline into the
floor-creation path. Nothing here writes to the database — it produces *draft*
tables plus an annotated preview; a human confirms them before anything is
saved (see routers/floors.py apply-layout).

Reuses the frame sampling, median-background, detector cascade, and IoU dedupe
from ``roi_autodetect`` — the only genuinely new work is mapping camera-pixel
boxes onto the abstract floor canvas and guessing shape/capacity.
"""

from __future__ import annotations

import base64
import logging

import cv2
import numpy as np

from app.schemas.floor import RectBounds
from app.schemas.roi import DraftTableOut
from app.services.roi_autodetect import (
    _dedupe_rects,
    _detect_with_contours,
    _detect_with_table_tops,
    _detect_with_yolo,
    _is_reasonable_table_rect,
    _median_frame,
    _sample_frames,
)

logger = logging.getLogger(__name__)

# Minimum boxes from the trained model before we bother pulling in the
# classical fallback detectors (a wide establishing shot the model wasn't
# trained on will return too few).
_MIN_YOLO_BOXES = 2


def _guess_shape(width: float, height: float) -> str:
    aspect = width / height if height else 1.0
    return "CIRCLE" if 0.8 <= aspect <= 1.25 else "RECTANGLE"


def _guess_capacity(canvas_area: float, floor_area: float) -> int:
    """Rough capacity from how much of the floor the table occupies. Staff
    adjust this in the confirm step; the goal is a sensible default, not truth."""
    frac = canvas_area / floor_area if floor_area else 0.0
    if frac < 0.020:
        return 2
    if frac < 0.045:
        return 4
    if frac < 0.075:
        return 6
    return 8


def _annotated_preview(frame: np.ndarray, boxes: list[tuple[str, RectBounds]]) -> str:
    """Draw numbered boxes on the frame and return a base64 JPEG data URI."""
    canvas = frame.copy()
    for number, rect in boxes:
        x, y = int(rect.x), int(rect.y)
        w, h = int(rect.width), int(rect.height)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (34, 197, 94), 3)
        cv2.putText(
            canvas, number, (x + 4, max(y - 8, 18)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (34, 197, 94), 2,
        )
    ok, buf = cv2.imencode(".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def detect_layout(
    camera_url: str,
    floor_width: int,
    floor_height: int,
    section_id: str,
    start_index: int = 1,
    max_frames: int = 30,
) -> dict:
    """Detect tables from one camera and return draft tables + a preview.

    Raises ValueError if the camera source can't be read (caller maps to 422).
    """
    frames, (frame_w, frame_h) = _sample_frames(camera_url, max_frames=max_frames)
    median = _median_frame(frames, (frame_w, frame_h))

    # Primary: the trained table-state model (now wired up via Phase 0 fix).
    candidates = _detect_with_yolo(median)
    method = "yolo"

    # Fallback: for camera angles the model wasn't trained on, add the classical
    # table-top mask + contour detectors so a wide shot still yields boxes.
    if len(candidates) < _MIN_YOLO_BOXES:
        extra = _detect_with_table_tops(median) or _detect_with_contours(median)
        if extra:
            candidates = candidates + extra
            method = "yolo+classical" if candidates else "classical"

    deduped = [
        rect
        for rect in _dedupe_rects(candidates)
        if _is_reasonable_table_rect(rect, frame_w, frame_h)
    ]

    scale_x = floor_width / frame_w if frame_w else 1.0
    scale_y = floor_height / frame_h if frame_h else 1.0
    floor_area = float(floor_width * floor_height)

    drafts: list[DraftTableOut] = []
    preview_boxes: list[tuple[str, RectBounds]] = []
    for i, rect in enumerate(deduped):
        number = f"T{start_index + i}"
        # Map camera-pixel box → floor-canvas box (linear scale; straight-down).
        cx = round(rect.x * scale_x, 1)
        cy = round(rect.y * scale_y, 1)
        cw = round(rect.width * scale_x, 1)
        ch = round(rect.height * scale_y, 1)
        # The detected box itself is the ROI, in raw-camera coordinates — the
        # exact space the monitoring pipeline matches detections against — so a
        # newly-created table is camera-monitored with zero extra setup.
        roi = RectBounds(
            x=round(rect.x), y=round(rect.y),
            width=round(rect.width), height=round(rect.height),
        )
        drafts.append(
            DraftTableOut(
                number=number,
                capacity=_guess_capacity(cw * ch, floor_area),
                type="STANDARD",
                shape=_guess_shape(cw, ch),
                section_id=section_id,
                x=cx, y=cy, width=cw, height=ch,
                rotation=0.0,
                camera_url=camera_url,
                roi_coords=roi,
                confidence=0.0,
            )
        )
        preview_boxes.append((number, rect))

    preview = _annotated_preview(median, preview_boxes)

    return {
        "camera_url": camera_url,
        "frame_width": frame_w,
        "frame_height": frame_h,
        "method": method,
        "preview_image": preview,
        "draft_tables": drafts,
    }
