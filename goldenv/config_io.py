from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from goldenv.config import AppConfig


@dataclass
class CalibrationValues:
    mm_per_pixel: float
    mm_per_pixel_x: Optional[float] = None
    mm_per_pixel_y: Optional[float] = None


def save_app_config(config_path: Path, config: AppConfig) -> None:
    import yaml

    with config_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            config.model_dump(mode="json"),
            fh,
            allow_unicode=True,
            sort_keys=False,
        )


def save_calibration(
    config_path: Path,
    config: AppConfig,
    values: CalibrationValues,
) -> None:
    if not config.cameras:
        raise RuntimeError("未配置相机")
    cal = config.cameras[0].calibration
    cal.mm_per_pixel = values.mm_per_pixel
    cal.mm_per_pixel_x = values.mm_per_pixel_x
    cal.mm_per_pixel_y = values.mm_per_pixel_y
    save_app_config(config_path, config)
