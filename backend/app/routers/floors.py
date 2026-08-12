import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user, require_floor_editor
from app.database import get_db
from app.models.user import User
from app.schemas.floor import FloorOut
from app.schemas.roi import (
    ApplyLayoutIn,
    CameraLayoutPreviewOut,
    DraftTableOut,
    LayoutSuggestionIn,
    LayoutSuggestionOut,
)
from app.services import layout_autodetect
from app.services.floor_service import (
    apply_detected_layout,
    floor_to_out,
    get_current_floor,
    reset_floor,
    update_floor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/floors", tags=["floors"])


def _resolve_camera_urls(floor, requested: list[str] | None) -> list[str]:
    if requested:
        return [u.strip() for u in requested if u and u.strip()]
    seen: set[str] = set()
    urls: list[str] = []
    for table in floor.tables:
        if table.camera_url and table.camera_url not in seen:
            seen.add(table.camera_url)
            urls.append(table.camera_url)
    if urls:
        return urls
    if settings.default_camera_url:
        return [settings.default_camera_url]
    return []


@router.get("/current", response_model=FloorOut)
def get_floor(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> FloorOut:
    return floor_to_out(get_current_floor(db))


@router.put("/current", response_model=FloorOut)
def put_floor(
    body: FloorOut,
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> FloorOut:
    return update_floor(db, body)


@router.post("/current/reset", response_model=FloorOut)
def post_reset(
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> FloorOut:
    return reset_floor(db)


@router.post("/current/auto-detect-layout", response_model=LayoutSuggestionOut)
def auto_detect_layout(
    body: LayoutSuggestionIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> LayoutSuggestionOut:
    """Detect tables from one or more cameras and return draft tables + previews.

    Suggest-only: nothing is written. Staff review the drafts and call
    apply-layout to commit them.
    """
    floor = get_current_floor(db)
    sections = floor.sections or []
    if not sections:
        raise HTTPException(400, "Create at least one section before auto-detecting a layout.")
    section_id = sections[0]["id"]

    camera_urls = _resolve_camera_urls(floor, body.camera_urls)
    if not camera_urls:
        raise HTTPException(
            400,
            "No camera to detect from. Configure a camera on a table (or set a default) first.",
        )

    cameras: list[CameraLayoutPreviewOut] = []
    all_drafts: list[DraftTableOut] = []
    errors: list[str] = []
    next_index = 1

    for url in camera_urls:
        try:
            result = layout_autodetect.detect_layout(
                url, floor.width, floor.height, section_id, start_index=next_index
            )
        except ValueError as exc:
            logger.warning("Auto-detect failed for camera %s: %s", url, exc)
            errors.append(f"{url}: {exc}")
            continue
        drafts = result["draft_tables"]
        next_index += len(drafts)
        all_drafts.extend(drafts)
        cameras.append(CameraLayoutPreviewOut(**result))

    if not cameras:
        raise HTTPException(422, "Could not detect a layout. " + " | ".join(errors))

    return LayoutSuggestionOut(cameras=cameras, draft_tables=all_drafts)


@router.post("/current/apply-layout", response_model=FloorOut)
def apply_layout(
    body: ApplyLayoutIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_floor_editor),
) -> FloorOut:
    """Commit the (staff-reviewed) draft tables as real, camera-monitored tables."""
    if not body.tables:
        raise HTTPException(400, "No tables to apply.")
    return apply_detected_layout(db, body.tables, replace=body.replace)
