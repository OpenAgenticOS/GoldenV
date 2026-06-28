from __future__ import annotations

import re
import struct
from typing import Optional

from goldenv.scales.base import WeightReading
from goldenv.scales.parsers.types import ParseResult
from goldenv.scales.protocol_registry import ScaleProtocolConfig


def parse_frame(protocol: ScaleProtocolConfig, frame: bytes) -> Optional[WeightReading]:
    return parse_frame_detailed(protocol, frame).reading


def parse_frame_detailed(protocol: ScaleProtocolConfig, frame: bytes) -> ParseResult:
    frame_hex = frame.hex(" ")
    try:
        if protocol.type == "fixed_length":
            result = _parse_fixed_length(protocol, frame)
        elif protocol.type in ("line_terminated", "regex", "command_response"):
            result = _parse_line(protocol, frame)
        elif protocol.type == "delimiter":
            result = _parse_delimiter(protocol, frame)
        else:
            return ParseResult(None, f"不支持的协议类型: {protocol.type}", frame_hex)
        if result is None:
            return ParseResult(None, "帧校验或字段解析失败", frame_hex)
        if protocol.checksum.enabled and not _validate_checksum(protocol, frame):
            return ParseResult(None, "校验和错误", frame_hex)
        return ParseResult(result, None, frame_hex)
    except Exception as exc:
        return ParseResult(None, str(exc), frame_hex)


def _decode(protocol: ScaleProtocolConfig, data: bytes) -> str:
    encoding = "gbk" if protocol.encoding.lower() == "gbk" else protocol.encoding
    return data.decode(encoding, errors="replace")


def _validate_checksum(protocol: ScaleProtocolConfig, frame: bytes) -> bool:
    cfg = protocol.checksum
    start = max(cfg.start, 0)
    end = len(frame) if cfg.end < 0 else min(cfg.end, len(frame))
    if end <= start:
        return False
    payload = frame[start:end]
    if cfg.type == "sum":
        expected = sum(payload) & 0xFF
        actual = frame[end] if end < len(frame) else None
        return actual == expected
    if cfg.type == "xor":
        value = 0
        for b in payload:
            value ^= b
        actual = frame[end] if end < len(frame) else None
        return actual == value
    if cfg.type == "mod256":
        expected = sum(payload) % 256
        actual = frame[end] if end < len(frame) else None
        return actual == expected
    return True


def _parse_field_value(field, protocol: ScaleProtocolConfig, chunk: bytes):
    if field.type == "hex":
        hex_val = chunk.hex().upper()
        if field.expect and hex_val != field.expect.replace(" ", "").upper():
            return None
        if field.name == "status":
            stable = bool(int(hex_val, 16) & (1 << field.stable_bit))
            return None, stable, None
        return None, None, None
    if field.type == "ascii":
        text = _decode(protocol, chunk)
        if field.expect and text != field.expect:
            return None
        if field.name == "sign":
            return int(field.map.get(text, 1)), None, None
        if field.name == "weight":
            return None, None, float(text.strip())
        if field.name == "unit":
            return None, None, field.map.get(text, text.strip())
    if field.type == "bcd":
        text = _decode(protocol, chunk).strip()
        return None, None, float(text) / (10 ** field.decimal_places)
    if field.type == "int":
        if protocol.encoding == "gbk":
            text = _decode(protocol, chunk).strip()
            return None, None, float(int(text))
        endian = ">" if protocol.endian == "big" else "<"
        fmt = {1: "b", 2: "h", 4: "i"}.get(field.length, "i")
        return None, None, float(struct.unpack(endian + fmt, chunk[:field.length])[0])
    if field.type == "float":
        endian = ">" if protocol.endian == "big" else "<"
        fmt = endian + ("f" if field.length == 4 else "d")
        return None, None, float(struct.unpack(fmt, chunk[:field.length])[0])
    if field.type == "bitfield":
        stable = bool(chunk[0] & (1 << field.stable_bit))
        return None, stable, None
    return None, None, None


def _parse_fixed_length(protocol: ScaleProtocolConfig, frame: bytes) -> Optional[WeightReading]:
    if protocol.frame_length and len(frame) != protocol.frame_length:
        return None
    sign = 1
    value: Optional[float] = None
    unit = protocol.unit_output
    stable = False

    for field in protocol.fields:
        chunk = frame[field.offset : field.offset + field.length]
        if len(chunk) < field.length:
            return None
        parsed = _parse_field_value(field, protocol, chunk)
        if parsed is None:
            return None
        sign_delta, stable_delta, value_delta = parsed
        if sign_delta is not None:
            sign = sign_delta
        if stable_delta is not None:
            stable = stable_delta
        if value_delta is not None:
            if isinstance(value_delta, str):
                unit = value_delta
            else:
                value = float(value_delta)

    if value is None:
        return None
    value_g = _to_grams(value * sign, str(unit), protocol.unit_output)
    return WeightReading(value_g=value_g, stable=stable, raw=frame.hex(" "), unit="g")


def _parse_delimiter(protocol: ScaleProtocolConfig, frame: bytes) -> Optional[WeightReading]:
    header = bytes.fromhex(protocol.header_hex) if protocol.header_hex else b"\x02"
    tail = bytes.fromhex(protocol.tail_hex) if protocol.tail_hex else b"\x03"
    if not frame.startswith(header) or not frame.endswith(tail):
        return None
    inner = frame[len(header) : len(frame) - len(tail)]
    if protocol.fields:
        return _parse_fixed_length(protocol, inner)
    text = _decode(protocol, inner).strip()
    match = re.search(r"([+-]?\d+\.?\d*)", text)
    if not match:
        return None
    value_g = _to_grams(float(match.group(1)), protocol.unit_output, protocol.unit_output)
    return WeightReading(value_g=value_g, stable=True, raw=frame.hex(" "), unit="g")


def _parse_line(protocol: ScaleProtocolConfig, frame: bytes) -> Optional[WeightReading]:
    text = _decode(protocol, frame).strip()
    if not protocol.pattern:
        return None
    match = re.match(protocol.pattern, text)
    if not match:
        return None

    sign = 1
    value = float(match.group(protocol.groups["value"]))
    if "sign" in protocol.groups:
        s = match.group(protocol.groups["sign"])
        if s == "-":
            sign = -1
    unit = protocol.unit_output
    if "unit" in protocol.groups:
        unit = match.group(protocol.groups["unit"])
    stable = False
    if "stable" in protocol.groups:
        flag = match.group(protocol.groups["stable"])
        if flag:
            stable = flag in protocol.stable_values
    else:
        stable = True

    value_g = _to_grams(value * sign, unit, protocol.unit_output)
    return WeightReading(value_g=value_g, stable=stable, raw=text, unit="g")


def _to_grams(value: float, unit: str, target: str) -> float:
    unit = (unit or "g").lower()
    if unit == "kg":
        value *= 1000
    return value
