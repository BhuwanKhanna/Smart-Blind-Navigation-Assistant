from __future__ import annotations

from typing import Final


REAL_WIDTH_PRIORS: Final[dict[str, float]] = {
    "person": 0.45,
    "obstacle": 0.55,
    "vehicle": 1.8,
    "door": 0.95,
    "stairs": 1.4,
    "pathway": 1.6,
    "hazard": 0.8,
}


def estimate_distance_meters(
    label: str,
    bbox: tuple[int, int, int, int],
    frame_width: int,
    frame_height: int,
) -> float:
    x1, y1, x2, y2 = bbox
    width_px = max(x2 - x1, 1)
    height_px = max(y2 - y1, 1)
    focal_length_px = frame_width * 0.9
    real_width = REAL_WIDTH_PRIORS.get(label, 0.7)
    distance = (real_width * focal_length_px) / width_px

    if label == "stairs":
        distance = max(0.7, 4.6 - ((y2 / max(frame_height, 1)) * 3.5))
    elif label == "pathway":
        distance = max(0.5, 3.8 - ((y2 / max(frame_height, 1)) * 2.2))
    elif label == "door":
        distance = max(0.7, min(distance, 5.0))

    return round(max(0.35, min(distance, 12.0)), 2)
