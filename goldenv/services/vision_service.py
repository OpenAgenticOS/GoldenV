from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from goldenv.cameras.factory import build_camera
from goldenv.config_io import CalibrationValues
from goldenv.vision.inner_diameter import InnerDiameterMeasurer
from goldenv.vision.measurement_base import MeasurementResult


class VisionService:
    def __init__(self, config: AppConfig):
        self.config = config
        self._camera = None
        self._measurer = InnerDiameterMeasurer()
        self._camera_config: Optional[CameraConfig] = config.cameras[0] if config.cameras else None

    @property
    def camera_config(self) -> CameraConfig:
        if not self._camera_config:
            raise RuntimeError("未配置相机")
        return self._camera_config

    def connect(self, simulate: bool = False) -> None:
        cfg = self.camera_config
        if simulate:
            from goldenv.cameras.simulated import SimulatedCamera

            self._camera = SimulatedCamera(cfg)
        else:
            self._camera = build_camera(cfg)
        self._camera.connect()

    def disconnect(self) -> None:
        if self._camera:
            self._camera.disconnect()
        self._camera = None

    def capture_frame(self) -> np.ndarray:
        if not self._camera:
            raise RuntimeError("相机未连接")
        return self._camera.capture().image

    def measure_inner_diameter(self, image: Optional[np.ndarray] = None) -> MeasurementResult:
        if image is None:
            image = self.capture_frame()
        return self._measurer.measure(
            image,
            self.config.measurement,
            self.camera_config.calibration,
        )

    def save_image(self, image: np.ndarray, directory: Path, prefix: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        from datetime import datetime

        name = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        path = directory / name
        cv2.imwrite(str(path), image)
        return path

    def apply_calibration(self, values: CalibrationValues) -> None:
        cal = self.camera_config.calibration
        cal.mm_per_pixel = values.mm_per_pixel
        cal.mm_per_pixel_x = values.mm_per_pixel_x
        cal.mm_per_pixel_y = values.mm_per_pixel_y
