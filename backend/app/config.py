from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./foh.db"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expire_hours: int = 8
    cors_origins: str = "http://localhost:5173"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    guest_menu_base_url: str = "http://localhost:8000"

    # YOLO / camera pipeline
    camera_enabled: bool = True
    yolo_table_state_model_path: str = "backend/models/table_cleanliness_best.pt"
    camera_scan_interval_seconds: int = 30
    camera_cleaning_grace_seconds: int = 60
    # Edge-triggered CLEANING alerts: DIRTY_ALERT to waiter at 10 min,
    # escalate to manager at 20 min, no-camera manual-check alert at 15 min.
    camera_dirty_alert_seconds: int = 600
    camera_dirty_escalation_seconds: int = 1200
    camera_no_camera_cleaning_alert_seconds: int = 900
    table_state_confidence_threshold: float = 0.25
    consecutive_scans_required: int = 3
    # Consecutive clean ticks needed for CLEANING -> AVAILABLE. The written
    # spec says "if clean detected -> advance" (i.e. 1); the code has always
    # debounced this to avoid a half-cleared table flapping back to AVAILABLE.
    # Set to 1 for spec-literal behavior.
    camera_clean_scans_required: int = 3
    table_state_sample_frames: int = 5
    table_state_sample_stride: int = 3
    stream_label_history_size: int = 6
    stream_inference_stride: int = 3
    # Minimum fraction of a table's ROI that a full-frame detection box must
    # cover to be matched to that table (intersection-over-ROI-area).
    stream_roi_match_min_overlap: float = 0.3
    # Demo fallback when tables have no camera_url configured
    default_camera_url: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
