from __future__ import annotations

from pathlib import Path

import pytest

from goldenv.scales.parsers import parse_frame, parse_frame_detailed
from goldenv.scales.protocol_registry import ScaleProtocolRegistry


PROTO_DIR = Path(__file__).resolve().parent.parent / "configs" / "scale_protocols"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "scale_frames"


def _load_hex_fixture(name: str) -> bytes:
    text = (FIXTURE_DIR / name).read_text(encoding="utf-8")
    hex_str = "".join(line.split("#", 1)[0].strip() for line in text.splitlines())
    return bytes.fromhex(hex_str)


def test_fixed_12byte_valid_frame():
    registry = ScaleProtocolRegistry(PROTO_DIR)
    proto = registry.get("fixed_12byte_stx_etx")
    frame = _load_hex_fixture("fixed_12byte_valid.hex")
    reading = parse_frame(proto, frame)
    assert reading is not None
    assert reading.value_g == pytest.approx(12.34, rel=0.01)
    assert reading.stable is True


def test_fixed_12byte_invalid_header():
    registry = ScaleProtocolRegistry(PROTO_DIR)
    proto = registry.get("fixed_12byte_stx_etx")
    frame = _load_hex_fixture("fixed_12byte_bad_header.hex")
    result = parse_frame_detailed(proto, frame)
    assert result.reading is None
    assert result.error is not None


def test_hikrobot_12byte_alias():
    registry = ScaleProtocolRegistry(PROTO_DIR)
    proto = registry.get("hikrobot_12byte")
    frame = b"\x02+012.34 g\x01\x03"
    reading = parse_frame(proto, frame)
    assert reading is not None
    assert reading.value_g == pytest.approx(12.34, rel=0.01)


def test_delimiter_stx_etx():
    registry = ScaleProtocolRegistry(PROTO_DIR)
    proto = registry.get("delimiter_stx_etx")
    frame = b"\x02+45.67 g\x03"
    reading = parse_frame(proto, frame)
    assert reading is not None
    assert reading.value_g == pytest.approx(45.67, rel=0.01)


def test_and_fz_csv():
    registry = ScaleProtocolRegistry(PROTO_DIR)
    proto = registry.get("and_fz_csv")
    reading = parse_frame(proto, b"ST,GS,+00123.45,kg")
    assert reading is not None
    assert reading.value_g == pytest.approx(123450.0)


def test_protocol_overrides():
    registry = ScaleProtocolRegistry(PROTO_DIR)
    proto = registry.resolve("fixed_12byte_stx_etx", {"frame_length": 14})
    assert proto.frame_length == 14


def test_protocol_import_export(tmp_path):
    registry = ScaleProtocolRegistry(PROTO_DIR)
    dest = tmp_path / "exported.yaml"
    registry.export_yaml("ascii_line_kg", dest)
    assert dest.is_file()
    user_dir = tmp_path / "user_protocols"
    user_registry = ScaleProtocolRegistry(user_dir)
    imported = user_registry.import_yaml(dest)
    assert imported.id == "ascii_line_kg"


def test_checksum_sum():
    registry = ScaleProtocolRegistry(PROTO_DIR)
    proto = registry.resolve(
        "fixed_12byte_stx_etx",
        {
            "checksum": {"enabled": True, "type": "sum", "start": 0, "end": 12},
            "frame_length": 13,
            "fields": [
                {"name": "header", "offset": 0, "length": 1, "type": "hex", "expect": "02"},
                {"name": "sign", "offset": 1, "length": 1, "type": "ascii", "map": {"+": 1}},
                {"name": "weight", "offset": 2, "length": 6, "type": "ascii"},
                {"name": "unit", "offset": 8, "length": 2, "type": "ascii", "map": {" g": "g"}},
                {"name": "status", "offset": 10, "length": 1, "type": "bitfield", "stable_bit": 0},
                {"name": "tail", "offset": 11, "length": 1, "type": "hex", "expect": "03"},
            ],
        },
    )
    body = b"\x02+012.34 g\x01\x03"
    checksum = sum(body[0:12]) & 0xFF
    frame = body + bytes([checksum])
    reading = parse_frame(proto, frame)
    assert reading is not None
    assert reading.value_g == pytest.approx(12.34, rel=0.01)
