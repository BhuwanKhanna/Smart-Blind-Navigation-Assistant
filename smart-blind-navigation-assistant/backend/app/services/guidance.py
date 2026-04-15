from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.detection import Detection, SceneAnalysis


TRANSLATIONS = {
    "en": {
        "move_left": "Step left",
        "move_right": "Step right",
        "go_straight": "Path clear, move straight",
        "obstacle_left": "Obstacle on the left",
        "obstacle_right": "Obstacle on the right",
        "obstacle_ahead": "Obstacle ahead",
        "stairs_ahead": "Stairs ahead, slow down",
        "vehicle_approaching": "Vehicle approaching, stop and wait",
        "door_ahead": "Door ahead",
        "hazard_close": "Hazard very close, pause",
        "safe": "Route looks safe",
    },
    "hi": {
        "move_left": "थोड़ा बाएं चलें",
        "move_right": "थोड़ा दाएं चलें",
        "go_straight": "रास्ता साफ है, सीधे चलें",
        "obstacle_left": "बाईं ओर बाधा है",
        "obstacle_right": "दाईं ओर बाधा है",
        "obstacle_ahead": "सामने बाधा है",
        "stairs_ahead": "आगे सीढ़ियां हैं, धीरे चलें",
        "vehicle_approaching": "वाहन पास आ रहा है, रुकें",
        "door_ahead": "आगे दरवाजा है",
        "hazard_close": "खतरा बहुत पास है, रुकें",
        "safe": "रास्ता सुरक्षित दिख रहा है",
    },
    "es": {
        "move_left": "Da un paso a la izquierda",
        "move_right": "Da un paso a la derecha",
        "go_straight": "Camino libre, sigue recto",
        "obstacle_left": "Obstaculo a la izquierda",
        "obstacle_right": "Obstaculo a la derecha",
        "obstacle_ahead": "Obstaculo adelante",
        "stairs_ahead": "Escaleras adelante, reduce la velocidad",
        "vehicle_approaching": "Vehiculo acercandose, detente",
        "door_ahead": "Puerta adelante",
        "hazard_close": "Peligro muy cerca, pausa",
        "safe": "La ruta parece segura",
    },
}


@dataclass(slots=True)
class GuidanceDecision:
    instruction: str
    priority: str
    direction: str
    arrow_target: tuple[int, int]
    confidence: float
    speak: bool


class GuidanceEngine:
    def decide(self, scene: SceneAnalysis, frame_width: int, frame_height: int, language: str) -> GuidanceDecision:
        dictionary = TRANSLATIONS.get(language, TRANSLATIONS["en"])
        priority = "normal"
        direction = scene.pathway_direction
        confidence = scene.pathway_confidence
        speak = False
        instruction = dictionary["safe"] if scene.pathway_confidence < 0.5 else dictionary["go_straight"]

        top_hazard = self._top_hazard(scene.detections)
        if top_hazard is not None:
            confidence = max(confidence, top_hazard.hazard_score)
            direction = scene.pathway_direction if scene.pathway_direction != "center" else self._avoid_direction(top_hazard.direction)

            if top_hazard.label == "vehicle" and (top_hazard.approaching or top_hazard.distance_m <= 3.5):
                instruction = dictionary["vehicle_approaching"]
                priority = "critical"
                speak = True
            elif top_hazard.label == "stairs" and top_hazard.distance_m <= 3.2:
                instruction = dictionary["stairs_ahead"]
                priority = "high"
                speak = True
            elif top_hazard.distance_m <= 1.2:
                instruction = dictionary["hazard_close"]
                priority = "critical"
                speak = True
            elif top_hazard.direction == "left":
                instruction = dictionary["obstacle_left"]
                priority = "high"
                speak = True
            elif top_hazard.direction == "right":
                instruction = dictionary["obstacle_right"]
                priority = "high"
                speak = True
            else:
                instruction = dictionary["obstacle_ahead"]
                priority = "high"
                speak = True

        if scene.pathway_confidence >= 0.58:
            if scene.pathway_direction == "left":
                instruction = dictionary["move_left"] if priority != "critical" else instruction
            elif scene.pathway_direction == "right":
                instruction = dictionary["move_right"] if priority != "critical" else instruction
            elif top_hazard is None:
                instruction = dictionary["go_straight"]

        for detection in scene.detections:
            if detection.label == "door" and detection.distance_m <= 3.0 and priority == "normal":
                instruction = dictionary["door_ahead"]
                speak = True
                confidence = max(confidence, detection.confidence)
                break

        arrow_target = _arrow_target(direction, frame_width, frame_height)
        return GuidanceDecision(
            instruction=instruction,
            priority=priority,
            direction=direction,
            arrow_target=arrow_target,
            confidence=round(confidence, 3),
            speak=speak or priority in {"high", "critical"},
        )

    @staticmethod
    def _top_hazard(detections: list[Detection]) -> Detection | None:
        candidates = [item for item in detections if item.category in {"vehicle", "obstacle", "hazard"}]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item.hazard_score, reverse=True)[0]

    @staticmethod
    def _avoid_direction(hazard_direction: str) -> str:
        if hazard_direction == "left":
            return "right"
        if hazard_direction == "right":
            return "left"
        return "center"


def _arrow_target(direction: str, frame_width: int, frame_height: int) -> tuple[int, int]:
    y = int(frame_height * 0.78)
    if direction == "left":
        return int(frame_width * 0.22), y
    if direction == "right":
        return int(frame_width * 0.78), y
    return int(frame_width * 0.5), y
