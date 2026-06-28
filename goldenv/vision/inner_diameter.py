from __future__ import annotations

from time import perf_counter
from typing import Optional, Tuple

import numpy as np

from goldenv.config import CalibrationConfig, MeasurementConfig
from goldenv.vision.measurement_base import MeasurementBase, MeasurementResult, MeasurementValue, _cv2
from goldenv.vision.overlay import draw_measurement_overlay


class InnerDiameterMeasurer(MeasurementBase):
    """空心圆环内径测量：外轮廓 + 内孔轮廓 + 圆拟合。"""

    def measure(
        self,
        image: np.ndarray,
        config: MeasurementConfig,
        calibration: CalibrationConfig,
    ) -> MeasurementResult:
        cv2 = _cv2()
        started = perf_counter()
        corrected = self._undistort(cv2, image, calibration)
        roi_image, roi_offset = self._crop_roi(corrected, config.roi)
        mask = self._make_mask(cv2, roi_image, config.threshold)
        outer, inner = self._find_ring_contours(cv2, mask, config)
        overlay = corrected.copy()

        inner_circle = self._fit_circle(inner)
        outer_circle = self._fit_circle(outer)
        ox, oy = roi_offset
        inner_center = (inner_circle[0] + ox, inner_circle[1] + oy)
        inner_radius = inner_circle[2]
        outer_center = (outer_circle[0] + ox, outer_circle[1] + oy)
        outer_radius = outer_circle[2]

        mm_per_pixel = (calibration.scale_x + calibration.scale_y) / 2
        inner_diameter_mm = 2 * inner_radius * mm_per_pixel

        eccentricity = np.hypot(
            inner_center[0] - outer_center[0],
            inner_center[1] - outer_center[1],
        ) / max(outer_radius, 1)
        quality_ok = eccentricity <= config.max_eccentricity
        quality_message = "" if quality_ok else f"内外圆偏心过大 ({eccentricity:.3f})"

        draw_measurement_overlay(
            overlay,
            outer_center,
            outer_radius,
            inner_center,
            inner_radius,
            inner_diameter_mm,
        )

        elapsed_ms = (perf_counter() - started) * 1000
        return MeasurementResult(
            values=[MeasurementValue("inner_diameter", inner_diameter_mm, "mm")],
            elapsed_ms=elapsed_ms,
            overlay=overlay,
            quality_ok=quality_ok,
            quality_message=quality_message,
        )

    def _find_ring_contours(self, cv2, mask: np.ndarray, config: MeasurementConfig):
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if not contours or hierarchy is None:
            raise ValueError("未检测到可测量轮廓")
        hierarchy = hierarchy[0]
        outer_candidates = []
        for idx, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area >= config.min_area_px and hierarchy[idx][3] == -1:
                outer_candidates.append((area, idx, cnt))
        if not outer_candidates:
            raise ValueError("未找到外轮廓")
        _, outer_idx, outer_cnt = max(outer_candidates, key=lambda x: x[0])

        inner_candidates = []
        child = hierarchy[outer_idx][2]
        while child != -1:
            cnt = contours[child]
            area = cv2.contourArea(cnt)
            if area >= config.inner_min_area_px:
                inner_candidates.append((area, cnt))
            child = hierarchy[child][0]
        if not inner_candidates:
            raise ValueError("未找到内孔轮廓")
        _, inner_cnt = max(inner_candidates, key=lambda x: x[0])
        return outer_cnt, inner_cnt

    def _fit_circle(self, contour: np.ndarray) -> Tuple[float, float, float]:
        cv2 = _cv2()
        if len(contour) >= 5:
            (cx, cy), radius = cv2.minEnclosingCircle(contour)
            return float(cx), float(cy), float(radius)
        raise ValueError("轮廓点数不足，无法拟合圆")
