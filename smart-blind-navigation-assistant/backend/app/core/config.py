from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    app_name: str = "Smart Blind Navigation API"
    api_prefix: str = "/api"
    host: str = os.getenv("APP_HOST", "0.0.0.0")
    port: int = int(os.getenv("APP_PORT", "8000"))
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    camera_index: int = int(os.getenv("CAMERA_INDEX", "0"))
    frame_width: int = int(os.getenv("FRAME_WIDTH", "1280"))
    frame_height: int = int(os.getenv("FRAME_HEIGHT", "720"))
    detection_backend: str = os.getenv("DETECTION_BACKEND", "auto")
    language: str = os.getenv("LANGUAGE", "en")
    voice_rate: int = int(os.getenv("VOICE_RATE", "175"))
    offline_mode: bool = _get_bool("OFFLINE_MODE", True)
    artifacts_dir: Path = BASE_DIR / "backend" / "artifacts"
    database_path: Path = BASE_DIR / os.getenv("DATABASE_PATH", "backend/artifacts/navigation.db")
    alert_email_enabled: bool = _get_bool("ALERT_EMAIL_ENABLED", True)
    alert_sms_enabled: bool = _get_bool("ALERT_SMS_ENABLED", True)
    emergency_contact_email: str = os.getenv("EMERGENCY_CONTACT_EMAIL", "guardian@example.com")
    emergency_contact_phone: str = os.getenv("EMERGENCY_CONTACT_PHONE", "+910000000000")
    location_sim_lat: float = float(os.getenv("LOCATION_SIM_LAT", "28.6139"))
    location_sim_lon: float = float(os.getenv("LOCATION_SIM_LON", "77.2090"))
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_sender: str = os.getenv("SMTP_SENDER", "")
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from_number: str = os.getenv("TWILIO_FROM_NUMBER", "")

    def ensure_directories(self) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
