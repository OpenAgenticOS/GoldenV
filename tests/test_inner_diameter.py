from __future__ import annotations

import pytest

from goldenv.config import load_config
from goldenv.scales.parsers import parse_frame
from goldenv.scales.protocol_registry import ScaleProtocolRegistry
from goldenv.vision.inner_diameter import InnerDiameterMeasurer


@pytest.fixture
def config_path():
    from pathlib import Path

    return Path(__file__).resolve().parent.parent / "configs" / "station.yaml"


def test_load_config(config_path):
    cfg = load_config(config_path)
    assert cfg.cameras
    assert cfg.measurement.type == "inner_diameter"


def test_fixed_length_parser():
    registry = ScaleProtocolRegistry(
        __import__("pathlib").Path(__file__).resolve().parent.parent / "configs" / "scale_protocols"
    )
    proto = registry.get("hikrobot_12byte")
    frame = b"\x02+012.34 g\x01\x03"
    reading = parse_frame(proto, frame)
    assert reading is not None
    assert reading.value_g == pytest.approx(12.34, rel=0.01)


def test_ascii_line_parser():
    registry = ScaleProtocolRegistry(
        __import__("pathlib").Path(__file__).resolve().parent.parent / "configs" / "scale_protocols"
    )
    proto = registry.get("ascii_line_kg")
    reading = parse_frame(proto, b"+123.45 g ST")
    assert reading is not None
    assert reading.value_g == pytest.approx(123.45)
    assert reading.stable is True


def test_inner_diameter_on_simulated_ring():
    import numpy as np

    from goldenv.config import CalibrationConfig, MeasurementConfig

    height, width = 480, 640
    image = np.zeros((height, width, 3), dtype=np.uint8)
    cx, cy = width // 2, height // 2
    outer_r, inner_r = 120, 60
    yy, xx = np.ogrid[:height, :width]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    image[(dist <= outer_r) & (dist >= inner_r)] = (220, 190, 120)

    measurer = InnerDiameterMeasurer()
    config = MeasurementConfig(threshold=50, min_area_px=1000, inner_min_area_px=100)
    calibration = CalibrationConfig(mm_per_pixel=0.1)
    result = measurer.measure(image, config, calibration)
    expected_inner_px = inner_r * 2
    expected_mm = expected_inner_px * calibration.mm_per_pixel
    assert result.values[0].value == pytest.approx(expected_mm, rel=0.15)


def test_protocol_registry_list():
    registry = ScaleProtocolRegistry(
        __import__("pathlib").Path(__file__).resolve().parent.parent / "configs" / "scale_protocols"
    )
    ids = {p.id for p in registry.list_protocols()}
    assert "ascii_line_kg" in ids
    assert "hikrobot_12byte" in ids
