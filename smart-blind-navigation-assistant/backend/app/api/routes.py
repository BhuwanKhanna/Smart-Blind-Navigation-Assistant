from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from backend.app.models.schemas import (
    AssistantStartRequest,
    ControlResponse,
    DashboardSnapshot,
    EmergencyRequest,
    VoicePromptRequest,
)


router = APIRouter()


def _service(request: Request):
    return request.app.state.assistant


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/assistant/start", response_model=ControlResponse)
def start_assistant(payload: AssistantStartRequest, request: Request) -> ControlResponse:
    try:
        status = _service(request).start(payload)
        return ControlResponse(ok=True, message="Assistant started.", status=status)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/assistant/stop", response_model=ControlResponse)
def stop_assistant(request: Request) -> ControlResponse:
    status = _service(request).stop()
    return ControlResponse(ok=True, message="Assistant stopped.", status=status)


@router.get("/assistant/status")
def assistant_status(request: Request) -> dict:
    return _service(request).get_status()


@router.get("/assistant/frame")
def assistant_frame(request: Request) -> Response:
    frame = _service(request).get_frame()
    if frame is None:
        raise HTTPException(status_code=404, detail="No frame available. Start the assistant first.")
    return Response(content=frame, media_type="image/jpeg")


@router.post("/assistant/speak")
def speak_prompt(payload: VoicePromptRequest, request: Request) -> dict:
    return _service(request).speak_prompt(payload)


@router.post("/assistant/share-location")
def share_location(request: Request) -> dict:
    return _service(request).share_location()


@router.post("/assistant/emergency")
def emergency(payload: EmergencyRequest, request: Request) -> dict:
    return _service(request).emergency_alert(payload)


@router.get("/events")
def list_events(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return _service(request).list_events(limit)


@router.get("/dashboard", response_model=DashboardSnapshot)
def dashboard_snapshot(request: Request) -> DashboardSnapshot:
    return DashboardSnapshot(**_service(request).dashboard_snapshot())
