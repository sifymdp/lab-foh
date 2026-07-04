import shutil
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.core import camera_utils
from app.core.deps import get_current_user, require_floor_editor
from app.database import get_db
from app.models import TableQRCode
from app.models.user import User
from app.schemas.floor import CreateTableIn, StatusPatchIn, TableOut, TablePatchIn
from app.schemas.roi import CameraRoiSuggestionOut
from app.services.roi_autodetect import suggest_camera_roi
from app.services import table_service

router = APIRouter(prefix="/tables", tags=["tables"])

# Directory where uploaded camera videos are stored
CAMERA_UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "camera_uploads"
CAMERA_UPLOADS_DIR.mkdir(exist_ok=True)


@router.get("/{table_id}/qr")
def table_qr_page(table_id: str, db: Session = Depends(get_db)) -> HTMLResponse:
    qr = (
        db.query(TableQRCode)
        .filter(TableQRCode.table_id == table_id, TableQRCode.is_active.is_(True))
        .first()
    )
    if not qr:
        raise HTTPException(404, "QR code not found for table")
    guest_url = f"{settings.guest_menu_base_url}/guest/menu?token={qr.token}"
    qr_img = f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={quote(guest_url)}"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Table QR</title>
<style>
  body {{ font-family: system-ui, sans-serif; text-align: center; padding: 40px; }}
  img {{ border: 8px solid #111; border-radius: 8px; }}
  p {{ color: #555; margin-top: 16px; word-break: break-all; }}
</style></head>
<body>
  <h1>Scan to order</h1>
  <img src="{qr_img}" alt="QR code" width="240" height="240" />
  <p>{guest_url}</p>
</body></html>"""
    return HTMLResponse(html)


@router.get("/{table_id}/camera/snapshot")
def camera_snapshot(
    table_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> Response:
    """Grab one still frame from this table's camera so the ROI tool has something to draw on."""
    table = table_service.get_table(db, table_id)
    if not table.camera_url:
        raise HTTPException(404, "This table has no camera_url configured yet")

    frame = camera_utils.capture_frame(table.camera_url)
    if frame is None:
        raise HTTPException(502, "Could not read a frame from that camera_url")

    jpeg_bytes = camera_utils.encode_jpeg(frame)
    return Response(content=jpeg_bytes, media_type="image/jpeg")


@router.post("/{table_id}/camera/auto-roi", response_model=CameraRoiSuggestionOut)
def auto_roi_suggestion(
    table_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> CameraRoiSuggestionOut:
    """Sample a pre-recorded camera source and suggest a stable ROI."""
    table = table_service.get_table(db, table_id)
    if not table.camera_url:
        raise HTTPException(404, "This table has no camera_url configured yet")

    try:
        suggestion = suggest_camera_roi(table.camera_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CameraRoiSuggestionOut(**suggestion)


@router.post("/{table_id}/camera/upload")
def upload_camera_video(
    table_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> dict:
    """Upload a video file to use as the camera source for this table."""
    table = table_service.get_table(db, table_id)

    # Save the file to disk
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    dest = CAMERA_UPLOADS_DIR / f"table_{table_id}{suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Update the table's camera_url to point to the saved file
    file_path = str(dest.resolve())
    table.camera_url = file_path
    db.commit()

    return {"cameraUrl": file_path, "filename": file.filename}


@router.post("", response_model=TableOut)
def create_table(
    body: CreateTableIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> TableOut:
    return table_service.add_table(db, body)


@router.put("/{table_id}", response_model=TableOut)
def update_table(
    table_id: str,
    body: TablePatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TableOut:
    return table_service.update_table(db, table_id, body)


@router.patch("/{table_id}/status", response_model=TableOut)
def patch_status(
    table_id: str,
    body: StatusPatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TableOut:
    return table_service.patch_table_status(db, table_id, body.status, user.id)


@router.delete("/{table_id}", status_code=204)
def remove_table(
    table_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> None:
    table_service.delete_table(db, table_id)
