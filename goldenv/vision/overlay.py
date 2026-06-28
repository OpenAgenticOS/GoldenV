from __future__ import annotations

import cv2
import numpy as np

from goldenv.vision.measurement_base import MeasurementResult, MeasurementValue


def draw_measurement_overlay(
    overlay: np.ndarray,
    outer_center: tuple[float, float],
    outer_radius: float,
    inner_center: tuple[float, float],
    inner_radius: float,
    inner_diameter_mm: float,
) -> None:
    oc = (int(outer_center[0]), int(outer_center[1]))
    ic = (int(inner_center[0]), int(inner_center[1]))
    cv2.circle(overlay, oc, int(outer_radius), (0, 180, 255), 2)
    cv2.circle(overlay, ic, int(inner_radius), (0, 220, 0), 2)
    cv2.line(overlay, ic, (ic[0] + int(inner_radius), ic[1]), (0, 220, 0), 2)
    label = f"内径 {inner_diameter_mm:.2f} mm"
    cv2.putText(
        overlay,
        label,
        (ic[0] - 80, ic[1] - int(inner_radius) - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 220, 0),
        2,
    )
