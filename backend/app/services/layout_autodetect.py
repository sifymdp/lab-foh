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


def _clamp(value: float, low: float, high: float) -> float:
    if high < low:
        return low
    return max(low, min(value, high))


def _guess_shape(width: float, height: float) -> str:
    aspect = width / height if height else 1.0
    return "CIRCLE" if 0.8 <= aspect <= 1.25 else "RECTANGLE"


def _guess_capacity(box_area: float, frame_area: float) -> int:
    """Rough capacity from how much of the camera frame the table box covers.
    Staff adjust this in the confirm step; the goal is a sensible default."""
    frac = box_area / frame_area if frame_area else 0.0
    if frac < 0.035:
        return 2
    if frac < 0.080:
        return 4
    if frac < 0.140:
        return 6
    return 8


# Standard on-canvas table sizes by capacity — mirrors the sizes the manual
# "Add table" flow uses, so an auto-detected floor looks like a hand-built one
# instead of scaling the (often huge) raw detection box onto the canvas.
_RECT_SIZE = {2: (76.0, 66.0), 4: (104.0, 76.0), 6: (134.0, 86.0), 8: (164.0, 96.0)}
_CIRCLE_DIAM = {2: 64.0, 4: 88.0, 6: 108.0, 8: 124.0}


def _standard_size(capacity: int, shape: str) -> tuple[float, float]:
    if shape == "CIRCLE":
        d = _CIRCLE_DIAM.get(capacity, 72.0)
        return d, d
    return _RECT_SIZE.get(capacity, (104.0, 76.0))


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
    target_region: RectBounds | None = None,
) -> dict:
    """Detect tables from one camera and return draft tables + a preview.

    Tables are laid out at standard sizes and spread across ``target_region``
    (the designated section's bounds, when provided) preserving their detected
    relative arrangement — rather than scaling the raw detection boxes straight
    onto the canvas, which produced oversized, overlapping tables spilling
    outside the section.

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

    frame_area = float(frame_w * frame_h)

    # Target rectangle on the canvas to lay the tables into: the designated
    # section (clamped to the canvas), otherwise the whole floor with a margin.
    if target_region is not None:
        rx = max(0.0, float(target_region.x))
        ry = max(0.0, float(target_region.y))
        rw = min(float(target_region.width), floor_width - rx)
        rh = min(float(target_region.height), floor_height - ry)
    else:
        margin = 48.0
        rx, ry = margin, margin
        rw, rh = floor_width - 2 * margin, floor_height - 2 * margin
    rw = max(rw, 120.0)
    rh = max(rh, 120.0)

    # Detected box centres in frame space, and their spread, so we can stretch
    # the arrangement to fill the target region while keeping relative positions.
    centers = [(r.x + r.width / 2.0, r.y + r.height / 2.0) for r in deduped]
    xs = [c[0] for c in centers] or [0.0]
    ys = [c[1] for c in centers] or [0.0]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = (max_x - min_x) or 1.0
    span_y = (max_y - min_y) or 1.0

    # Inner padding keeps tables off the section edge (half the largest table).
    pad = 70.0
    inner_w = max(rw - 2 * pad, 10.0)
    inner_h = max(rh - 2 * pad, 10.0)
    single = len(deduped) <= 1

    drafts: list[DraftTableOut] = []
    preview_boxes: list[tuple[str, RectBounds]] = []
    for i, rect in enumerate(deduped):
        number = f"T{start_index + i}"
        shape = _guess_shape(rect.width, rect.height)
        capacity = _guess_capacity(rect.width * rect.height, frame_area)
        tw, th = _standard_size(capacity, shape)

        # Position: map the detected centre into the target region, preserving
        # the left-to-right / top-to-bottom arrangement the camera saw.
        cxn = 0.5 if single else (centers[i][0] - min_x) / span_x
        cyn = 0.5 if single else (centers[i][1] - min_y) / span_y
        center_x = rx + pad + cxn * inner_w
        center_y = ry + pad + cyn * inner_h
        x = _clamp(center_x - tw / 2.0, 0.0, floor_width - tw)
        y = _clamp(center_y - th / 2.0, 0.0, floor_height - th)

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
                capacity=capacity,
                type="STANDARD",
                shape=shape,
                section_id=section_id,
                x=round(x, 1), y=round(y, 1), width=tw, height=th,
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
