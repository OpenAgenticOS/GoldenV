from __future__ import annotations

import numpy as np

from goldenv.cameras.base import CameraFrame, utc_now
from goldenv.config import CameraConfig


class SimulatedCamera:
    """模拟相机：生成带圆环的测试图，用于无硬件开发与 CI。"""

    def __init__(self, config: CameraConfig):
        self.config = config
        self.camera_id = config.id
        self.connected = False
        self._capture_count = 0

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def capture(self) -> CameraFrame:
        if not self.connected:
            raise RuntimeError(f"相机 {self.camera_id} 未连接")
        self._capture_count += 1
        return CameraFrame(
            camera_id=self.camera_id,
            captured_at=utc_now(),
            image=self._make_ring_image(),
        )

    def _make_ring_image(self) -> np.ndarray:
        height = self.config.height
        width = self.config.width
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:, :] = (24, 24, 24)

        cx, cy = width // 2, height // 2
        jitter = (self._capture_count % 5) - 2
        outer_r = min(width, height) // 4 + jitter
        inner_r = outer_r // 2

        yy, xx = np.ogrid[:height, :width]
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        ring = (dist <= outer_r) & (dist >= inner_r)
        image[ring] = (220, 190, 120)

        return image
