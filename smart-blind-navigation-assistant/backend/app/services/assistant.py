from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

import cv2

from backend.app.core.config import Settings
from backend.app.models.schemas import AssistantStartRequest, EmergencyRequest, VoicePromptRequest
from backend.app.services.alerts import SafetyNotifier
from backend.app.services.detection import Detection, create_scene_detector
from backend.app.services.guidance import GuidanceDecision, GuidanceEngine
from backend.app.services.speech import VoiceGuide
from backend.app.services.storage import NavigationStore


class NavigationAssistantService:
    def __init__(self, settings: Settings, store: NavigationStore) -> None:
        self.settings = settings
        self.store = store
        self.notifier = SafetyNotifier(settings)
        self.guidance_engine = GuidanceEngine()
        self.voice = VoiceGuide(rate=settings.voice_rate, language=settings.language)
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._detector = None
        self._latest_frame: bytes | None = None
        self._latest_status: dict[str, Any] = self._default_status()
        self._session = AssistantStartRequest(
            camera_index=settings.camera_index,
            detection_backend=settings.detection_backend if settings.detection_backend in {"auto", "yolo", "opencv"} else "auto",
            language=settings.language if settings.language in {"en", "hi", "es"} else "en",
            voice_rate=settings.voice_rate,
        )
        self._last_spoken_text = ""
        self._last_spoken_at = 0.0
        self._last_logged_at: dict[str, float] = {}

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, payload: AssistantStartRequest) -> dict[str, Any]:
        with self._lock:
            if self.is_running:
                return self.get_status()
            self._session = payload
            self.voice.configure(rate=payload.voice_rate, language=payload.language)
            self._detector = create_scene_detector(payload.detection_backend)
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            self._latest_status.update(
                {
                    "running": True,
                    "message": "Navigation assistant started.",
                    "backend": self._detector.backend_name,
                    "language": payload.language,
                    "voice_rate": payload.voice_rate,
                }
            )
            return self.get_status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if not self.is_running:
                self._latest_status["message"] = "Navigation assistant is already stopped."
                return self.get_status()
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=2)
            self._thread = None
            self._latest_status.update({"running": False, "message": "Navigation assistant stopped."})
            return self.get_status()

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            status = dict(self._latest_status)
        status["summary"] = self.store.summary()
        return status

    def get_frame(self) -> bytes | None:
        with self._lock:
            return self._latest_frame

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.list_events(limit)

    def dashboard_snapshot(self) -> dict[str, Any]:
        return {
            "assistant": self.get_status(),
            "summary": self.store.summary(),
            "events": self.store.list_events(50),
        }

    def speak_prompt(self, payload: VoicePromptRequest) -> dict[str, Any]:
        self.voice.speak(payload.text, payload.language)
        return {"spoken": True, "text": payload.text, "language": payload.language}

    def share_location(self) -> dict[str, Any]:
        location = self.notifier.share_location()
        self.store.log_event(
            event_type="location_share",
            severity="info",
            confidence=1.0,
            status="shared",
            details=location,
            channels=["simulated-location-share"],
        )
        return location

    def emergency_alert(self, payload: EmergencyRequest) -> dict[str, Any]:
        location = self.notifier.share_location()
        event = {
            "reason": payload.reason,
            "location": location,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        channels = self.notifier.send_emergency(event)
        self.voice.speak("Emergency help has been requested", self._session.language)
        event_id = self.store.log_event(
            event_type="emergency",
            severity="critical",
            confidence=1.0,
            status="alerted",
            details=event,
            channels=channels,
        )
        return {"id": event_id, **event, "channels": channels}

    def _run_loop(self) -> None:
        capture = cv2.VideoCapture(self._session.camera_index)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.frame_height)

        if not capture.isOpened():
            with self._lock:
                self._latest_status.update(
                    {
                        "running": False,
                        "message": "Unable to access the camera. Check permissions or camera index.",
                    }
                )
            self._thread = None
            return

        previous_tick = time.perf_counter()
        previous_distances: dict[str, float] = {}

        while not self._stop_event.is_set():
            ok, frame = capture.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            scene = self._detector.analyze(frame, previous_distances) if self._detector else None
            if scene is None:
                time.sleep(0.05)
                continue

            previous_distances = self._distance_map(scene.detections)
            guidance = self.guidance_engine.decide(
                scene=scene,
                frame_width=frame.shape[1],
                frame_height=frame.shape[0],
                language=self._session.language,
            )
            self._maybe_speak(guidance)
            self._maybe_log_hazard(scene.detections, guidance)

            tick = time.perf_counter()
            fps = 1.0 / max(tick - previous_tick, 1e-6)
            previous_tick = tick

            annotated = self._render_overlay(frame, scene.detections, guidance, scene.safe_corridor, fps)
            success, buffer = cv2.imencode(".jpg", annotated)
            if success:
                with self._lock:
                    self._latest_frame = buffer.tobytes()
                    self._latest_status = {
                        "running": True,
                        "message": "Navigation assistant live.",
                        "backend": scene.backend_name,
                        "language": self._session.language,
                        "voice_rate": self._session.voice_rate,
                        "guidance": guidance.instruction,
                        "guidance_confidence": guidance.confidence,
                        "priority": guidance.priority,
                        "path_direction": scene.pathway_direction,
                        "path_confidence": scene.pathway_confidence,
                        "detections": [self._detection_payload(item) for item in scene.detections[:8]],
                        "tts_available": self.voice.available,
                        "last_voice_message": self.voice.last_message,
                        "fps": round(fps, 1),
                        "last_updated_at": datetime.now(timezone.utc).isoformat(),
                    }

            time.sleep(0.015)

        capture.release()

    def _maybe_speak(self, guidance: GuidanceDecision) -> None:
        now = time.time()
        should_speak = guidance.speak and (
            guidance.instruction != self._last_spoken_text or (now - self._last_spoken_at) >= 3.0
        )
        if should_speak:
            self.voice.speak(guidance.instruction, self._session.language)
            self._last_spoken_text = guidance.instruction
            self._last_spoken_at = now

    def _maybe_log_hazard(self, detections: list[Detection], guidance: GuidanceDecision) -> None:
        if not detections:
            return
        top = sorted(
            [item for item in detections if item.category in {"vehicle", "hazard", "obstacle"}],
            key=lambda item: item.hazard_score,
            reverse=True,
        )
        if not top:
            return
        top_hazard = top[0]
        if top_hazard.hazard_score < 0.72 and guidance.priority == "normal":
            return

        event_key = f"{top_hazard.label}:{guidance.priority}"
        now = time.time()
        if (now - self._last_logged_at.get(event_key, 0.0)) < 7.0:
            return

        severity = "critical" if guidance.priority == "critical" else "warning"
        self.store.log_event(
            event_type="hazard" if severity == "critical" else "navigation_warning",
            severity=severity,
            confidence=max(top_hazard.hazard_score, guidance.confidence),
            status="detected",
            details={
                "label": top_hazard.label,
                "direction": top_hazard.direction,
                "distance_m": top_hazard.distance_m,
                "instruction": guidance.instruction,
                "approaching": top_hazard.approaching,
            },
            channels=["voice-guidance"],
        )
        self._last_logged_at[event_key] = now

    def _render_overlay(
        self,
        frame,
        detections: list[Detection],
        guidance: GuidanceDecision,
        safe_corridor: tuple[int, int],
        fps: float,
    ):
        overlay = frame.copy()
        height, width = overlay.shape[:2]

        for detection in detections:
            color = {
                "vehicle": (74, 98, 255),
                "hazard": (0, 196, 255),
                "obstacle": (0, 173, 181),
                "landmark": (98, 214, 141),
                "path": (51, 214, 255),
            }.get(detection.category, (220, 220, 220))
            x1, y1, x2, y2 = detection.bbox
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            label = f"{detection.label} {detection.distance_m:.1f}m {detection.confidence:.2f}"
            cv2.putText(overlay, label, (x1, max(28, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 2)

        corridor_left, corridor_right = safe_corridor
        cv2.rectangle(
            overlay,
            (corridor_left, int(height * 0.60)),
            (corridor_right, height - 24),
            (74, 222, 128),
            2,
        )
        cv2.arrowedLine(
            overlay,
            (width // 2, int(height * 0.90)),
            guidance.arrow_target,
            (255, 214, 10),
            6,
            tipLength=0.2,
        )

        cv2.rectangle(overlay, (18, 18), (610, 166), (10, 15, 28), -1)
        cv2.putText(overlay, "Blind Navigation Assistant", (34, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (245, 247, 250), 2)
        cv2.putText(
            overlay,
            f"Guide: {guidance.instruction}",
            (34, 82),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            (120, 205, 255),
            2,
        )
        cv2.putText(
            overlay,
            f"Priority: {guidance.priority.title()}  Confidence: {guidance.confidence:.2f}",
            (34, 112),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 221, 128),
            2,
        )
        cv2.putText(
            overlay,
            f"FPS: {fps:.1f}  Detections: {len(detections)}",
            (34, 142),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (230, 236, 245),
            2,
        )
        return overlay

    @staticmethod
    def _distance_map(detections: list[Detection]) -> dict[str, float]:
        mapped: dict[str, float] = {}
        for detection in detections:
            mapped[detection.label] = min(mapped.get(detection.label, detection.distance_m), detection.distance_m)
        return mapped

    @staticmethod
    def _detection_payload(detection: Detection) -> dict[str, Any]:
        return {
            "label": detection.label,
            "category": detection.category,
            "confidence": detection.confidence,
            "distance_m": detection.distance_m,
            "hazard_score": detection.hazard_score,
            "direction": detection.direction,
            "approaching": detection.approaching,
        }

    @staticmethod
    def _default_status() -> dict[str, Any]:
        return {
            "running": False,
            "message": "Navigation assistant is idle.",
            "backend": "auto",
            "language": "en",
            "voice_rate": 175,
            "guidance": "Waiting to start",
            "guidance_confidence": 0.0,
            "priority": "normal",
            "path_direction": "center",
            "path_confidence": 0.0,
            "detections": [],
            "tts_available": False,
            "last_voice_message": "",
            "fps": 0.0,
            "last_updated_at": None,
        }
