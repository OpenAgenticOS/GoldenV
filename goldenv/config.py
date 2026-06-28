from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, Field

from goldenv.paths import app_root, bundled_configs_dir, user_configs_dir


class CalibrationConfig(BaseModel):
    mm_per_pixel: float = Field(default=0.05, gt=0)
    mm_per_pixel_x: Optional[float] = Field(default=None, gt=0)
    mm_per_pixel_y: Optional[float] = Field(default=None, gt=0)
    camera_matrix: Optional[List[List[float]]] = None
    dist_coeffs: Optional[List[float]] = None

    @property
    def scale_x(self) -> float:
        return self.mm_per_pixel_x or self.mm_per_pixel

    @property
    def scale_y(self) -> float:
        return self.mm_per_pixel_y or self.mm_per_pixel


class CameraConfig(BaseModel):
    id: str
    name: str = ""
    kind: Literal["simulated", "dahua", "usb_opencv"] = "simulated"
    ip: Optional[str] = None
    user_defined_name: Optional[str] = None
    device_index: int = 0
    width: int = Field(default=1280, gt=0)
    height: int = Field(default=960, gt=0)
    pixel_format: str = "Mono8"
    exposure_us: Optional[float] = Field(default=8000, gt=0)
    gain: Optional[float] = Field(default=1.0, ge=0)
    packet_size: int = 1500
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)


class PollConfig(BaseModel):
    enabled: bool = False
    interval_ms: int = 200
    command_hex: str = "500D0A"


class StableConfig(BaseModel):
    threshold_g: float = 0.01
    consecutive: int = 3


class ScaleConfig(BaseModel):
    id: str
    name: str = ""
    protocol_id: str = "ascii_line_kg"
    port: str = "auto"
    baudrate: int = 9600
    bytesize: int = 8
    parity: Literal["N", "E", "O", "M", "S"] = "N"
    stopbits: float = 1
    protocol_overrides: Dict[str, Any] = Field(default_factory=dict)
    poll: PollConfig = Field(default_factory=PollConfig)
    stable: StableConfig = Field(default_factory=StableConfig)


class MeasurementConfig(BaseModel):
    type: Literal["inner_diameter", "diameter", "bounding_box"] = "inner_diameter"
    roi: Optional[Tuple[int, int, int, int]] = None
    threshold: int = Field(default=80, ge=0, le=255)
    min_area_px: int = Field(default=5000, gt=0)
    inner_min_area_px: int = Field(default=500, gt=0)
    max_eccentricity: float = Field(default=0.15, ge=0)


class StorageConfig(BaseModel):
    database_path: str = "data/goldenv.sqlite3"
    image_dir: str = "data/images"
    overlay_dir: str = "data/overlays"


class AppConfig(BaseModel):
    cameras: List[CameraConfig]
    scales: List[ScaleConfig] = Field(default_factory=list)
    measurement: MeasurementConfig = Field(default_factory=MeasurementConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


def scale_protocols_dir(config_path: Path | None = None) -> Path:
    if config_path:
        candidate = config_path.parent / "scale_protocols"
        if candidate.is_dir():
            return candidate
    user_proto = user_configs_dir() / "scale_protocols"
    if user_proto.is_dir():
        return user_proto
    bundled = bundled_configs_dir() / "scale_protocols"
    if bundled.is_dir():
        return bundled
    return app_root() / "configs" / "scale_protocols"


def load_config(path: Union[str, Path] = "configs/station.yaml") -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return AppConfig.model_validate(raw)
