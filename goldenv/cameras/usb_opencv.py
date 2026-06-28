from __future__ import annotations

import numpy as np

from goldenv.cameras.base import CameraFrame, utc_now
from goldenv.config import CameraConfig


class UsbOpenCVCamera:
    """USB 摄像头备用 Adapter（OpenCV VideoCapture）。"""

    def __init__(self, config: CameraConfig):
        self.config = config
        self.camera_id = config.id
        self._cap = None

    def connect(self) -> None:
        import cv2

        self._cap = cv2.VideoCapture(self.config.device_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开 USB 相机 index={self.config.device_index}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)

    def disconnect(self) -> None:
        if self._cap:
            self._cap.release()
        self._cap = None

    def capture(self) -> CameraFrame:
        if self._cap is None:
            raise RuntimeError(f"相机 {self.camera_id} 未连接")
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("USB 相机采图失败")
        return CameraFrame(camera_id=self.camera_id, captured_at=utc_now(), image=frame)
