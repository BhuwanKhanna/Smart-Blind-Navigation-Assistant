from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AssistantStartRequest(BaseModel):
    camera_index: int = 0
    detection_backend: Literal["auto", "yolo", "opencv"] = "auto"
    language: Literal["en", "hi", "es"] = "en"
    voice_rate: int = Field(default=175, ge=120, le=240)


class VoicePromptRequest(BaseModel):
    text: str = Field(min_length=1, max_length=160)
    language: Literal["en", "hi", "es"] = "en"


class EmergencyRequest(BaseModel):
    reason: str = Field(default="User requested help", min_length=3, max_length=120)


class ControlResponse(BaseModel):
    ok: bool
    message: str
    status: dict[str, Any]


class EventRecord(BaseModel):
    id: int
    event_type: str
    severity: str
    confidence: float
    status: str
    details: dict[str, Any]
    channels: list[str]
    created_at: str


class DashboardSnapshot(BaseModel):
    assistant: dict[str, Any]
    summary: dict[str, Any]
    events: list[EventRecord]
