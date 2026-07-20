from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class ZoneMatch:
    name: str
    polygon: list[tuple[int, int]]


class ZoneManager:
    def __init__(self, zones: dict[str, Any] | None = None, camera_id: str | None = None) -> None:
        self.zones = normalize_zones(camera_scoped_zones(zones or {}, camera_id))

    def get_zone(self, _camera_id: str, bbox: tuple[int, int, int, int]) -> str:
        point = bbox_center(bbox)
        for zone_name, polygon in self.zones.items():
            if point_in_polygon(point, polygon):
                return zone_name
        return "none"

    def draw_zones(self, frame, _camera_id: str, scale: float = 1.0) -> None:
        for zone_name, polygon in self.zones.items():
            scaled_polygon = np.array(
                [[int(x / scale), int(y / scale)] for x, y in polygon],
                dtype=np.int32,
            )
            cv2.polylines(frame, [scaled_polygon], isClosed=True, color=(255, 0, 0), thickness=2)
            label_x, label_y = scaled_polygon[0]
            cv2.putText(frame, zone_name, (label_x, max(20, label_y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    def to_payload(self) -> dict[str, list[list[int]]]:
        return {
            zone_name: [[int(x), int(y)] for x, y in polygon]
            for zone_name, polygon in self.zones.items()
        }


def camera_scoped_zones(zones: dict[str, Any], camera_id: str | None = None) -> dict[str, Any]:
    if not isinstance(zones, dict):
        return {}
    if camera_id and isinstance(zones.get(camera_id), dict):
        return zones[camera_id]
    return {
        zone_name: polygon
        for zone_name, polygon in zones.items()
        if not isinstance(polygon, dict)
    }


def normalize_zones(zones: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    normalized: dict[str, list[tuple[int, int]]] = {}
    if not isinstance(zones, dict):
        return normalized
    for raw_name, raw_polygon in zones.items():
        zone_name = str(raw_name or "").strip()
        if not zone_name or not isinstance(raw_polygon, list):
            continue
        polygon: list[tuple[int, int]] = []
        for point in raw_polygon:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                polygon = []
                break
            try:
                polygon.append((int(round(float(point[0]))), int(round(float(point[1])))))
            except (TypeError, ValueError):
                polygon = []
                break
        if len(polygon) >= 3:
            normalized[zone_name] = polygon
    return normalized


def bbox_center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[int, int]]) -> bool:
    if len(polygon) < 3:
        return False
    contour = np.array(polygon, dtype=np.int32)
    return cv2.pointPolygonTest(contour, point, False) >= 0
