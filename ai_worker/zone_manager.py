from dataclasses import dataclass

import cv2
import numpy as np

from config import CAMERA_ZONES


@dataclass(frozen=True)
class ZoneMatch:
    name: str
    polygon: list[tuple[int, int]]


class ZoneManager:
    def __init__(self, zones_by_camera: dict = CAMERA_ZONES) -> None:
        self.zones_by_camera = zones_by_camera

    def get_zone(self, camera_id: str, bbox: tuple[int, int, int, int]) -> str:
        point = bbox_center(bbox)
        for zone_name, polygon in self.zones_by_camera.get(camera_id, {}).items():
            if point_in_polygon(point, polygon):
                return zone_name
        return "none"

    def draw_zones(self, frame, camera_id: str, scale: float = 1.0) -> None:
        for zone_name, polygon in self.zones_by_camera.get(camera_id, {}).items():
            scaled_polygon = np.array(
                [[int(x / scale), int(y / scale)] for x, y in polygon],
                dtype=np.int32,
            )
            cv2.polylines(frame, [scaled_polygon], isClosed=True, color=(255, 0, 0), thickness=2)
            label_x, label_y = scaled_polygon[0]
            cv2.putText(frame, zone_name, (label_x, max(20, label_y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)


def bbox_center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[int, int]]) -> bool:
    contour = np.array(polygon, dtype=np.int32)
    return cv2.pointPolygonTest(contour, point, False) >= 0
