"""OpenCV helpers for frame capture and ROI cropping."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

CAMERA_UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "camera_uploads"

# Shared latest annotated frame for MJPEG stream (BGR numpy array)
latest_stream_frame: np.ndarray | None = None


def parse_roi(roi_coords: str | None) -> dict[str, int] | None:
    if not roi_coords:
        return None
    try:
        data = json.loads(roi_coords)
        return {
            "x": int(data["x"]),
            "y": int(data["y"]),
            "width": int(data["width"]),
            "height": int(data["height"]),
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def crop_roi(frame: np.ndarray, roi: dict[str, int]) -> np.ndarray | None:
    h_frame, w_frame = frame.shape[:2]
    x = max(0, min(roi["x"], w_frame - 1))
    y = max(0, min(roi["y"], h_frame - 1))
    w = min(roi["width"], w_frame - x)
    h = min(roi["height"], h_frame - y)
    if w <= 0 or h <= 0:
        return None
    return frame[y : y + h, x : x + w]


def resolve_camera_source(camera_url: str) -> str:
    path = Path(camera_url)
    if path.exists():
        return str(path)

    candidates: list[Path] = []
    if path.name:
        candidates.append(CAMERA_UPLOADS_DIR / path.name)
    if settings.default_camera_url:
        default_name = Path(settings.default_camera_url).name
        if default_name:
            candidates.append(CAMERA_UPLOADS_DIR / default_name)
    candidates.extend(sorted(CAMERA_UPLOADS_DIR.glob("*.mp4")))

    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)

    return camera_url


def capture_frame(camera_url: str) -> np.ndarray | None:
    cap = cv2.VideoCapture(resolve_camera_source(camera_url))
    if not cap.isOpened():
        logger.warning("Could not open camera: %s", camera_url)
        return None
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        logger.warning("Failed to read frame from: %s", camera_url)
        return None
    return frame


def capture_frame_sequence(
    camera_url: str,
    sample_frames: int,
    frame_stride: int = 1,
) -> list[np.ndarray]:
    """Capture a short sequence of frames for temporal smoothing.

    For uploaded videos this samples forward in time; for streams it still
    reads nearby frames from the source. Empty results mean the source could
    not provide any readable frames.
    """
    cap = cv2.VideoCapture(resolve_camera_source(camera_url))
    if not cap.isOpened():
        logger.warning("Could not open camera for sequence capture: %s", camera_url)
        return []

    frames: list[np.ndarray] = []
    stride = max(frame_stride, 1)
    try:
        while len(frames) < max(sample_frames, 1):
            ok, frame = cap.read()
            if not ok or frame is None:
                if frames:
                    break
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
            frames.append(frame)
            for _ in range(stride - 1):
                ok, _ = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    break
    finally:
        cap.release()

    return frames


def set_stream_frame(frame: np.ndarray) -> None:
    global latest_stream_frame
    latest_stream_frame = frame


def encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("JPEG encode failed")
    return buf.tobytes()


def draw_table_overlay(
    frame: np.ndarray,
    roi: dict[str, int],
    table_number: str,
    label: str,
    color_bgr: tuple[int, int, int],
    sub_label: str | None = None,
) -> None:
    x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
    cv2.rectangle(frame, (x, y), (x + w, y + h), color_bgr, 2)
    cv2.putText(
        frame,
        f"T{table_number}",
        (x, max(y - 8, 16)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color_bgr,
        2,
    )
    cv2.putText(
        frame,
        label,
        (x + 4, y + 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color_bgr,
        1,
    )
    if sub_label:
        cv2.putText(
            frame,
            sub_label,
            (x + 4, y + h - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color_bgr,
            1,
        )


STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    "AVAILABLE": (0, 200, 0),      # green
    "SEATED": (0, 0, 220),         # red
    "ACTIVE": (0, 0, 220),         # red — Occupied
    "RESERVED": (0, 140, 255),     # orange
    "BILLING": (180, 0, 180),      # purple
    "CLEANING": (0, 140, 255),     # orange
    "PAID": (200, 180, 0),         # teal-ish
}


def status_label(status: str, dirty: bool = False) -> str:
    if status == "AVAILABLE":
        return "Available"
    if status in ("SEATED", "ACTIVE"):
        return "Occupied"
    if status == "RESERVED":
        return "Reserved"
    if status == "BILLING":
        return "Billing"
    if status == "CLEANING":
        return "Dirty" if dirty else "Cleaning"
    if status == "PAID":
        return "Paid"
    return status
