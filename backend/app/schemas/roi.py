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
