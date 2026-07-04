import cv2
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.core.camera_utils import resolve_camera_source
from app.models import Table

router = APIRouter(tags=["stream"])


def _generate(camera_url: str):
    cap = cv2.VideoCapture(resolve_camera_source(camera_url))
    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        frame = cv2.resize(frame, (960, 540))
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
        )


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
    return StreamingResponse(
        _generate(camera_url),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
