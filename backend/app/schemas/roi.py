from app.schemas.common import CamelModel
from app.schemas.floor import RectBounds


class CameraRoiSuggestionOut(CamelModel):
    frame_width: int
    frame_height: int
    sampled_frames: int
    method: str
    confidence: float
    roi_coords: RectBounds
    candidates: list[RectBounds]


class CameraSnapshotAnalysisIn(CamelModel):
    roi_coords: RectBounds | None = None


class CameraSceneDetectionOut(CamelModel):
    label: str
    confidence: float
    bounds: RectBounds


class CameraSnapshotAnalysisOut(CamelModel):
    frame_width: int
    frame_height: int
    roi_used: RectBounds | None = None
    roi_label: str | None = None
    roi_confidence: float | None = None
    scene_summary: dict[str, int]
    scene_detections: list[CameraSceneDetectionOut]


# ─── Auto-detect floor layout ─────────────────────────────────────────────────


class DraftTableOut(CamelModel):
    """A table the camera proposes — not yet written to the DB. Shaped so the
    frontend can edit it and hand the list straight back to apply-layout."""
    number: str
    capacity: int
    type: str
    shape: str
    section_id: str
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    camera_url: str | None = None
    roi_coords: RectBounds | None = None
    confidence: float = 0.0


class CameraLayoutPreviewOut(CamelModel):
    camera_url: str
    frame_width: int
    frame_height: int
    method: str
    preview_image: str  # base64 JPEG data URI with detected boxes drawn
    draft_tables: list[DraftTableOut]


class LayoutSuggestionIn(CamelModel):
    # When omitted, the server uses every camera configured on existing tables,
    # falling back to the default demo camera.
    camera_urls: list[str] | None = None


class LayoutSuggestionOut(CamelModel):
    cameras: list[CameraLayoutPreviewOut]
    draft_tables: list[DraftTableOut]  # flattened across all cameras


class ApplyLayoutIn(CamelModel):
    tables: list[DraftTableOut]
    # True replaces the whole floor's tables (fresh generation); False adds the
    # detected tables alongside whatever already exists.
    replace: bool = True
