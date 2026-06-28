from __future__ import annotations

import pytest

from goldenv.config import load_config
from goldenv.config_io import CalibrationValues, save_calibration


def test_save_calibration_uniform(tmp_path):
    cfg_path = tmp_path / "station.yaml"
    cfg_path.write_text(
        "cameras:\n  - id: cam1\n    calibration:\n      mm_per_pixel: 0.05\n",
        encoding="utf-8",
    )
    config = load_config(cfg_path)
    save_calibration(
        cfg_path,
        config,
        CalibrationValues(mm_per_pixel=0.123456, mm_per_pixel_x=None, mm_per_pixel_y=None),
    )
    reloaded = load_config(cfg_path)
    cal = reloaded.cameras[0].calibration
    assert cal.mm_per_pixel == pytest.approx(0.123456)
    assert cal.mm_per_pixel_x is None
    assert cal.mm_per_pixel_y is None


def test_save_calibration_separate_xy(tmp_path):
    cfg_path = tmp_path / "station.yaml"
    cfg_path.write_text(
        "cameras:\n  - id: cam1\n    calibration:\n      mm_per_pixel: 0.05\n",
        encoding="utf-8",
    )
    config = load_config(cfg_path)
    save_calibration(
        cfg_path,
        config,
        CalibrationValues(mm_per_pixel=0.08, mm_per_pixel_x=0.081, mm_per_pixel_y=0.079),
    )
    reloaded = load_config(cfg_path)
    cal = reloaded.cameras[0].calibration
    assert cal.mm_per_pixel == pytest.approx(0.08)
    assert cal.mm_per_pixel_x == pytest.approx(0.081)
    assert cal.mm_per_pixel_y == pytest.approx(0.079)
