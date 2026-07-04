from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./foh.db"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expire_hours: int = 8
    cors_origins: str = "http://localhost:5173"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    default_camera_url: str | None = None
    guest_menu_base_url: str = "http://localhost:8000"

    # YOLO / camera pipeline
    camera_enabled: bool = True
    yolo_person_model: str = "yolov8n.pt"
    yolo_table_model_path: str = ""
    yolo_dirty_model_path: str = (
        r"C:\Users\lucky\foh-yolo\runs\detect\foh_training\table_cleanliness_v2\weights\best.pt"
    )
    camera_scan_interval_seconds: int = 30
    camera_cleaning_grace_seconds: int = 60
    person_confidence_threshold: float = 0.5
    dirty_confidence_threshold: float = 0.25
    consecutive_scans_required: int = 3
    # Demo fallback when tables have no camera_url configured
    default_camera_url: str = r"C:/Users/lucky/demo_video.mp4"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    guest_menu_base_url: str = "http://localhost:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
