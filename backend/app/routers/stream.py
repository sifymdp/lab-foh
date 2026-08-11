import cv2
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.core import camera_utils
from app.core.roi_matching import match_detection_for_roi
from app.core.yolo_models import (
    TableStateDetection,
    is_table_state_model_ready,
    is_using_fallback_model,
    iter_full_frame_detections,
    smooth_table_state,
)
from app.models import Table

router = APIRouter(tags=["stream"])

DETECTION_COLORS: dict[str, tuple[int, int, int]] = {
    "clean": (0, 200, 0),
    "dirty": (0, 140, 255),
    "occupied": (0, 0, 255),
}

OUTPUT_FRAME_SIZE = (960, 540)
OUTPUT_FPS = 30
CONFIG_REFRESH_SECONDS = 1.0


@dataclass
class StreamWorkerState:
    floor_id: str
    camera_url: str
    frame: bytes | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    running: bool = False
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    config_signature: tuple[str, tuple[tuple[str, int, int, int, int], ...]] | None = None
    last_error: str | None = None
    roi_history: dict[str, deque[TableStateDetection | None]] = field(default_factory=dict)
    roi_labels: dict[str, TableStateDetection | None] = field(default_factory=dict)
    full_frame_detections: list[tuple[int, int, int, int, TableStateDetection]] = field(default_factory=list)
    processed_frames: int = 0


_stream_workers: dict[str, StreamWorkerState] = {}
_stream_workers_lock = threading.Lock()


def _tables_for_floor(floor_id: str) -> list[dict]:
    db = SessionLocal()
    try:
        tables = db.query(Table).filter(Table.floor_id == floor_id).all()
        return [
            {
                "id": table.id,
                "number": table.number,
                "camera_url": table.camera_url,
                "status": table.status,
                "roi": camera_utils.parse_roi(table.roi_coords),
            }
            for table in tables
        ]
    finally:
        db.close()


def _stream_signature(camera_url: str, tables: list[dict]) -> tuple[str, tuple[tuple[str, int, int, int, int], ...]]:
    roi_signature = tuple(
        sorted(
            (
                str(table["id"]),
                int(table["roi"]["x"]),
                int(table["roi"]["y"]),
                int(table["roi"]["width"]),
                int(table["roi"]["height"]),
            )
            for table in tables
            if table.get("roi")
        )
    )
    return (camera_url, roi_signature)


def _scale_roi_for_output(roi: dict[str, int], frame_width: int, frame_height: int) -> dict[str, int]:
    scale_x = OUTPUT_FRAME_SIZE[0] / max(frame_width, 1)
    scale_y = OUTPUT_FRAME_SIZE[1] / max(frame_height, 1)
    return {
        "x": int(round(roi["x"] * scale_x)),
        "y": int(round(roi["y"] * scale_y)),
        "width": max(int(round(roi["width"] * scale_x)), 1),
        "height": max(int(round(roi["height"] * scale_y)), 1),
    }


def _draw_full_frame_detections(
    frame,
    detections: list[tuple[int, int, int, int, TableStateDetection]],
    raw_width: int,
    raw_height: int,
) -> None:
    # Detections are in raw-camera coordinates; scale them down to the output frame.
    scale_x = OUTPUT_FRAME_SIZE[0] / max(raw_width, 1)
    scale_y = OUTPUT_FRAME_SIZE[1] / max(raw_height, 1)
    for x1, y1, x2, y2, detection in detections:
        ox1, oy1 = int(round(x1 * scale_x)), int(round(y1 * scale_y))
        ox2, oy2 = int(round(x2 * scale_x)), int(round(y2 * scale_y))
        color = DETECTION_COLORS.get(detection.label, (128, 128, 128))
        cv2.rectangle(frame, (ox1, oy1), (ox2, oy2), color, 2)
        cv2.putText(
            frame,
            f"{detection.label} {detection.confidence:.2f}",
            (ox1, max(oy1 - 8, 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )


def _update_state_detections(raw_frame, tables: list[dict], state: StreamWorkerState) -> None:
    """Detect once on the full raw frame, then match detections to each table's ROI.

    Both the detections and the saved roi_coords live in raw-camera-resolution
    space, so the overlap comparison needs no coordinate conversion.
    """
    roi_tables = [table for table in tables if table.get("roi")]

    if not is_table_state_model_ready():
        state.full_frame_detections = []
        for table in roi_tables:
            state.roi_labels.setdefault(str(table["id"]), None)
        return

    detections = iter_full_frame_detections(raw_frame)
    state.full_frame_detections = detections

    if not roi_tables:
        return

    history_size = max(settings.stream_label_history_size, 1)
    for table in roi_tables:
        table_id = str(table["id"])
        matched = match_detection_for_roi(detections, table["roi"])
        history = state.roi_history.setdefault(table_id, deque(maxlen=history_size))
        history.append(matched)
        # Custom model: a briefly unmatched table (e.g. someone blocking the
        # camera) holds its last known label instead of flipping to "clean" —
        # None means "no reading". COCO fallback: there is no "clean" class,
        # so an empty ROI produces no detections and None really does mean
        # clean; without this, a table that empties out would keep its stale
        # "occupied" label forever.
        smoothed = smooth_table_state(list(history), treat_none_as_clean=is_using_fallback_model())
        if smoothed is not None:
            state.roi_labels[table_id] = smoothed
        else:
            state.roi_labels.setdefault(table_id, None)


def _draw_stream_annotations(
    output_frame,
    tables: list[dict],
    state: StreamWorkerState,
    raw_width: int,
    raw_height: int,
) -> None:
    roi_tables = [table for table in tables if table.get("roi")]

    if not roi_tables:
        _draw_full_frame_detections(output_frame, state.full_frame_detections, raw_width, raw_height)
        return

    for table in roi_tables:
        roi = table["roi"]
        output_roi = _scale_roi_for_output(roi, raw_width, raw_height)
        stable_detection = state.roi_labels.get(str(table["id"]))

        if stable_detection is None:
            # No camera reading — fall back to the table's live status from the
            # DB (refreshed every CONFIG_REFRESH_SECONDS) in its status color.
            status = str(table.get("status") or "")
            label = camera_utils.status_label(status) if status else "ROI"
            color = camera_utils.STATUS_COLORS.get(status, (128, 128, 128))
        else:
            label = stable_detection.label.title()
            color = DETECTION_COLORS.get(stable_detection.label, (128, 128, 128))

        camera_utils.draw_table_overlay(
            output_frame,
            output_roi,
            str(table["number"]),
            label,
            color,
        )


def _stream_worker_loop(state: StreamWorkerState) -> None:
    cap = None
    last_refresh = 0.0
    cached_tables: list[dict] = []

    try:
        while not state.stop_event.is_set():
            now = time.time()
            if cap is None or now - last_refresh >= CONFIG_REFRESH_SECONDS:
                tables = _tables_for_floor(state.floor_id)
                signature = _stream_signature(state.camera_url, tables)
                if cap is None or signature != state.config_signature:
                    if cap is not None:
                        cap.release()
                    cap = cv2.VideoCapture(camera_utils.resolve_camera_source(state.camera_url))
                    state.config_signature = signature
                    state.roi_history.clear()
                    state.roi_labels.clear()
                    state.full_frame_detections = []
                    state.processed_frames = 0
                cached_tables = tables
                last_refresh = now

            if cap is None or not cap.isOpened():
                state.last_error = f"Could not open camera source for floor {state.floor_id}"
                time.sleep(0.2)
                continue

            ret, raw_frame = cap.read()
            if not ret or raw_frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                time.sleep(0.01)
                continue

            raw_height, raw_width = raw_frame.shape[:2]

            # Detection + ROI matching run on the untouched raw frame, in the
            # same coordinate space the ROIs were calibrated in. Resizing for
            # the browser happens only after.
            state.processed_frames += 1
            stride = max(settings.stream_inference_stride, 1)
            if state.processed_frames % stride == 1 % stride:
                _update_state_detections(raw_frame, cached_tables, state)

            output_frame = cv2.resize(raw_frame, OUTPUT_FRAME_SIZE)
            _draw_stream_annotations(output_frame, cached_tables, state, raw_width, raw_height)

            ok, buf = cv2.imencode(".jpg", output_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                state.last_error = "JPEG encode failed"
                continue

            with state.lock:
                state.frame = buf.tobytes()
                state.last_error = None
    finally:
        if cap is not None:
            cap.release()
        state.running = False


def _ensure_stream_worker(floor_id: str, camera_url: str) -> StreamWorkerState:
    with _stream_workers_lock:
        state = _stream_workers.get(floor_id)
        if state is None:
            state = StreamWorkerState(floor_id=floor_id, camera_url=camera_url)
            _stream_workers[floor_id] = state

        if state.camera_url != camera_url and state.running:
            state.stop_event.set()
            if state.thread is not None:
                state.thread.join(timeout=2.0)
            state.running = False
            state.thread = None
            state.frame = None
            state.stop_event = threading.Event()
            state.config_signature = None
            state.roi_history.clear()
            state.roi_labels.clear()
            state.full_frame_detections = []
            state.processed_frames = 0

        state.camera_url = camera_url
        if not state.running:
            state.stop_event.clear()
            state.running = True
            state.thread = threading.Thread(
                target=_stream_worker_loop,
                args=(state,),
                name=f"stream-worker-{floor_id}",
                daemon=True,
            )
            state.thread.start()
        return state


def stop_all_stream_workers() -> None:
    with _stream_workers_lock:
        states = list(_stream_workers.values())
        _stream_workers.clear()
    for state in states:
        state.stop_event.set()
        if state.thread is not None:
            state.thread.join(timeout=2.0)


def _generate(state: StreamWorkerState):
    frame_interval = 1.0 / OUTPUT_FPS
    while True:
        with state.lock:
            frame = state.frame

        if frame is None:
            time.sleep(0.05)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )
        time.sleep(frame_interval)


@router.get("/stream/{floor_id}")
def live_stream(floor_id: str, db: Session = Depends(get_db)):
    tables = db.query(Table).filter(Table.floor_id == floor_id).all()
    camera_url = None
    for t in tables:
        if t.camera_url:
            camera_url = t.camera_url
            break
    if not camera_url:
        camera_url = settings.default_camera_url
    if not camera_url:
        raise HTTPException(404, "No camera configured")
    state = _ensure_stream_worker(floor_id, camera_url)
    return StreamingResponse(
        _generate(state),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
