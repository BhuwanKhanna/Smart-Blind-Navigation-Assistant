from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from backend.app.services.depth import estimate_distance_meters


@dataclass(slots=True)
class Detection:
    label: str
    category: str
    confidence: float
    bbox: tuple[int, int, int, int]
    distance_m: float
    hazard_score: float
    direction: str
    approaching: bool


@dataclass(slots=True)
class SceneAnalysis:
    detections: list[Detection]
    pathway_direction: str
    pathway_confidence: float
    safe_corridor: tuple[int, int]
    backend_name: str


COCO_RELEVANT_MAP = {
    "person": ("obstacle", "person"),
    "chair": ("obstacle", "obstacle"),
    "bench": ("obstacle", "obstacle"),
    "suitcase": ("obstacle", "obstacle"),
    "backpack": ("obstacle", "obstacle"),
    "car": ("vehicle", "vehicle"),
    "bus": ("vehicle", "vehicle"),
    "truck": ("vehicle", "vehicle"),
    "motorcycle": ("vehicle", "vehicle"),
    "bicycle": ("vehicle", "vehicle"),
    "stop sign": ("hazard", "hazard"),
}


def create_scene_detector(preferred_backend: str):
    choices = ["yolo", "opencv"] if preferred_backend == "auto" else [preferred_backend]
    for backend in choices:
        try:
            if backend == "yolo":
                return YoloSceneDetector()
            if backend == "opencv":
                return OpenCVSceneDetector()
        except Exception:
            continue
    raise RuntimeError("No detection backend is available. Install ultralytics or use the OpenCV fallback.")


class YoloSceneDetector:
    def __init__(self) -> None:
        from ultralytics import YOLO

        self.model = YOLO("yolov8n.pt")
        self.backend_name = "yolo"

    def analyze(self, frame: np.ndarray, previous_distances: dict[str, float] | None = None) -> SceneAnalysis:
        height, width = frame.shape[:2]
        detections: list[Detection] = []
        prediction = self.model.predict(frame, conf=0.3, verbose=False)[0]

        if prediction.boxes is not None:
            names = prediction.names
            for box in prediction.boxes:
                class_name = names[int(box.cls[0])]
                if class_name not in COCO_RELEVANT_MAP:
                    continue
                category, label = COCO_RELEVANT_MAP[class_name]
                x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
                confidence = float(box.conf[0])
                distance = estimate_distance_meters(label, (x1, y1, x2, y2), width, height)
                direction = _direction_from_center((x1 + x2) / 2, width)
                approaching = _is_approaching(label, distance, previous_distances)
                hazard_score = _hazard_score(category, distance, confidence, approaching, y2 / max(height, 1))
                detections.append(
                    Detection(
                        label=label,
                        category=category,
                        confidence=round(confidence, 3),
                        bbox=(x1, y1, x2, y2),
                        distance_m=distance,
                        hazard_score=hazard_score,
                        direction=direction,
                        approaching=approaching,
                    )
                )

        structural = _detect_structural_features(frame, detections)
        detections.extend(structural["detections"])
        return SceneAnalysis(
            detections=sorted(detections, key=lambda item: item.hazard_score, reverse=True),
            pathway_direction=structural["pathway_direction"],
            pathway_confidence=structural["pathway_confidence"],
            safe_corridor=structural["safe_corridor"],
            backend_name=self.backend_name,
        )


class OpenCVSceneDetector:
    def __init__(self) -> None:
        self.backend_name = "opencv"

    def analyze(self, frame: np.ndarray, previous_distances: dict[str, float] | None = None) -> SceneAnalysis:
        detections = _detect_fallback_obstacles(frame, previous_distances)
        structural = _detect_structural_features(frame, detections)
        detections.extend(structural["detections"])
        return SceneAnalysis(
            detections=sorted(detections, key=lambda item: item.hazard_score, reverse=True),
            pathway_direction=structural["pathway_direction"],
            pathway_confidence=structural["pathway_confidence"],
            safe_corridor=structural["safe_corridor"],
            backend_name=self.backend_name,
        )


def _detect_fallback_obstacles(
    frame: np.ndarray,
    previous_distances: dict[str, float] | None,
) -> list[Detection]:
    height, width = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 70, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections: list[Detection] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < (width * height * 0.01):
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if y + h < int(height * 0.35):
            continue
        label = "vehicle" if w > width * 0.32 and y < height * 0.75 else "obstacle"
        category = "vehicle" if label == "vehicle" else "obstacle"
        distance = estimate_distance_meters(label, (x, y, x + w, y + h), width, height)
        direction = _direction_from_center(x + (w / 2), width)
        approaching = _is_approaching(label, distance, previous_distances)
        hazard_score = _hazard_score(category, distance, 0.58, approaching, (y + h) / max(height, 1))
        detections.append(
            Detection(
                label=label,
                category=category,
                confidence=0.58,
                bbox=(x, y, x + w, y + h),
                distance_m=distance,
                hazard_score=hazard_score,
                direction=direction,
                approaching=approaching,
            )
        )

    return sorted(detections, key=lambda item: item.hazard_score, reverse=True)[:6]


def _detect_structural_features(frame: np.ndarray, detections: list[Detection]) -> dict[str, Any]:
    height, width = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 120)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=65, minLineLength=70, maxLineGap=16)
    structural_detections: list[Detection] = []

    if lines is not None:
        horizontal = []
        for line in lines[:, 0]:
            x1, y1, x2, y2 = line
            if abs(y2 - y1) <= 18 and min(y1, y2) > int(height * 0.38):
                horizontal.append((x1, y1, x2, y2))
        if len(horizontal) >= 4:
            xs = [point for line in horizontal for point in (line[0], line[2])]
            ys = [point for line in horizontal for point in (line[1], line[3])]
            bbox = (max(min(xs) - 20, 0), max(min(ys) - 20, 0), min(max(xs) + 20, width), min(max(ys) + 20, height))
            distance = estimate_distance_meters("stairs", bbox, width, height)
            structural_detections.append(
                Detection(
                    label="stairs",
                    category="hazard",
                    confidence=round(min(0.92, 0.48 + (len(horizontal) * 0.05)), 3),
                    bbox=bbox,
                    distance_m=distance,
                    hazard_score=_hazard_score("hazard", distance, 0.78, False, bbox[3] / max(height, 1)),
                    direction=_direction_from_center((bbox[0] + bbox[2]) / 2, width),
                    approaching=False,
                )
            )

    # Door heuristic based on tall vertical rectangles.
    _, thresh = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < (width * height * 0.02):
            continue
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / max(h, 1)
        if 0.28 <= aspect_ratio <= 0.8 and h > int(height * 0.28) and y < int(height * 0.65):
            bbox = (x, y, x + w, y + h)
            distance = estimate_distance_meters("door", bbox, width, height)
            structural_detections.append(
                Detection(
                    label="door",
                    category="landmark",
                    confidence=0.66,
                    bbox=bbox,
                    distance_m=distance,
                    hazard_score=round(min(0.48, 0.18 + (1 / max(distance, 1))), 3),
                    direction=_direction_from_center((x + x + w) / 2, width),
                    approaching=False,
                )
            )
            break

    occupancy = np.zeros(width, dtype=np.float32)
    for detection in detections + structural_detections:
        x1, _, x2, y2 = detection.bbox
        if y2 < int(height * 0.45):
            continue
        occupancy[max(x1, 0):min(x2, width)] += detection.hazard_score + 0.2

    segments = _largest_free_segment(occupancy, width)
    safe_corridor = segments["corridor"]
    pathway_direction = segments["direction"]
    pathway_confidence = segments["confidence"]

    if pathway_confidence >= 0.52:
        corridor_bbox = (
            safe_corridor[0],
            int(height * 0.55),
            safe_corridor[1],
            height - 30,
        )
        distance = estimate_distance_meters("pathway", corridor_bbox, width, height)
        structural_detections.append(
            Detection(
                label="pathway",
                category="path",
                confidence=pathway_confidence,
                bbox=corridor_bbox,
                distance_m=distance,
                hazard_score=round(max(0.05, 0.3 - (pathway_confidence * 0.18)), 3),
                direction=pathway_direction,
                approaching=False,
            )
        )

    return {
        "detections": structural_detections,
        "pathway_direction": pathway_direction,
        "pathway_confidence": pathway_confidence,
        "safe_corridor": safe_corridor,
    }


def _largest_free_segment(occupancy: np.ndarray, width: int) -> dict[str, Any]:
    threshold = max(0.55, float(np.mean(occupancy) + np.std(occupancy) * 0.3))
    free_mask = occupancy <= threshold
    best_start = int(width * 0.35)
    best_end = int(width * 0.65)
    best_length = best_end - best_start
    current_start = None

    for index, is_free in enumerate(free_mask):
        if is_free and current_start is None:
            current_start = index
        if not is_free and current_start is not None:
            current_length = index - current_start
            if current_length > best_length:
                best_start, best_end = current_start, index
                best_length = current_length
            current_start = None
    if current_start is not None and (width - current_start) > best_length:
        best_start, best_end = current_start, width - 1
        best_length = width - current_start

    center = (best_start + best_end) / 2
    direction = _direction_from_center(center, width)
    confidence = round(min(0.95, max(0.25, best_length / max(width, 1))), 3)
    return {"corridor": (int(best_start), int(best_end)), "direction": direction, "confidence": confidence}


def _direction_from_center(center_x: float, frame_width: int) -> str:
    normalized = center_x / max(frame_width, 1)
    if normalized < 0.38:
        return "left"
    if normalized > 0.62:
        return "right"
    return "center"


def _is_approaching(label: str, distance: float, previous_distances: dict[str, float] | None) -> bool:
    if not previous_distances:
        return False
    previous = previous_distances.get(label)
    if previous is None:
        return False
    return (previous - distance) >= 0.45


def _hazard_score(category: str, distance: float, confidence: float, approaching: bool, vertical_position: float) -> float:
    base = {
        "vehicle": 0.76,
        "hazard": 0.72,
        "obstacle": 0.58,
        "landmark": 0.25,
        "path": 0.1,
    }.get(category, 0.4)
    distance_factor = max(0.0, 1.0 - (distance / 7.0))
    approach_bonus = 0.18 if approaching else 0.0
    vertical_bonus = max(0.0, vertical_position - 0.5) * 0.28
    score = base * 0.45 + confidence * 0.25 + distance_factor * 0.2 + approach_bonus + vertical_bonus
    return round(min(0.99, score), 3)
