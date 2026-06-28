from __future__ import annotations

from goldenv.cameras.dahua_sdk_loader import is_dahua_sdk_available
from goldenv.cameras.simulated import SimulatedCamera
from goldenv.config import CameraConfig
from goldenv.runtime.dahua_bootstrap import prepare_dahua_runtime


def build_camera(config: CameraConfig, allow_simulated_fallback: bool = True):
    if config.kind == "simulated":
        return SimulatedCamera(config)
    if config.kind == "dahua":
        from goldenv.cameras.dahua import DahuaCamera

        status = prepare_dahua_runtime()
        if is_dahua_sdk_available():
            return DahuaCamera(config)
        if allow_simulated_fallback:
            return SimulatedCamera(config)
        raise RuntimeError(status.message)
    if config.kind == "usb_opencv":
        from goldenv.cameras.usb_opencv import UsbOpenCVCamera

        return UsbOpenCVCamera(config)
    raise ValueError(f"不支持的相机类型: {config.kind}")
