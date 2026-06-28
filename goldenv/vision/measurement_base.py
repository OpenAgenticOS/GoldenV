from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import List, Optional, Tuple

import numpy as np

from goldenv.config import CalibrationConfig, MeasurementConfig


@dataclass(frozen=True)
class MeasurementValue:
    name: str
    value: float
    unit: str


@dataclass(frozen=True)
class MeasurementResult:
    values: List[MeasurementValue]
    elapsed_ms: float
    overlay: np.ndarray
    quality_ok: bool = True
    quality_message: str = ""


def _cv2():
    import cv2

    return cv2


class MeasurementBase:
    def _undistort(self, cv2, image: np.ndarray, calibration: CalibrationConfig) -> np.ndarray:
        if not calibration.camera_matrix or not calibration.dist_coeffs:
            return image
        matrix = np.asarray(calibration.camera_matrix, dtype=np.float64)
        coeffs = np.asarray(calibration.dist_coeffs, dtype=np.float64)
        return cv2.undistort(image, matrix, coeffs)

    def _crop_roi(self, image: np.ndarray, roi: Optional[Tuple[int, int, int, int]]):
        if roi is None:
            return image, (0, 0)
        x, y, w, h = roi
        if w <= 0 or h <= 0:
            raise ValueError("ROI 宽高必须为正")
        return image[y : y + h, x : x + w], (x, y)

    def _make_mask(self, cv2, image: np.ndarray, threshold: int) -> np.ndarray:
        if image.ndim == 2:
            gray = image
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        return mask
