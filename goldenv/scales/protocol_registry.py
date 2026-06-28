from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class ProtocolFieldConfig(BaseModel):
    name: str
    offset: int = 0
    length: int = 1
    type: str = "ascii"
    expect: Optional[str] = None
    map: Dict[str, Any] = Field(default_factory=dict)
    decimal_places: int = 0
    stable_bit: int = 0


class ChecksumConfig(BaseModel):
    enabled: bool = False
    type: str = "sum"
    start: int = 0
    end: int = -1


class ScaleProtocolConfig(BaseModel):
    id: str
    name: str = ""
    type: str
    frame_length: int = 0
    encoding: str = "ascii"
    endian: str = "big"
    line_ending: str = "\r\n"
    pattern: str = ""
    groups: Dict[str, int] = Field(default_factory=dict)
    stable_values: List[str] = Field(default_factory=list)
    stable_inference: str = ""
    fields: List[ProtocolFieldConfig] = Field(default_factory=list)
    checksum: ChecksumConfig = Field(default_factory=ChecksumConfig)
    unit_output: str = "g"
    header_hex: str = ""
    tail_hex: str = ""


class ScaleProtocolRegistry:
    def __init__(self, protocols_dir: Path):
        self.protocols_dir = protocols_dir
        self._protocols: Dict[str, ScaleProtocolConfig] = {}
        self.reload()

    def reload(self) -> None:
        self._protocols.clear()
        if not self.protocols_dir.is_dir():
            return
        for path in sorted(self.protocols_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            proto = ScaleProtocolConfig.model_validate(raw)
            self._protocols[proto.id] = proto

    def get(self, protocol_id: str) -> ScaleProtocolConfig:
        if protocol_id not in self._protocols:
            raise KeyError(f"未找到协议: {protocol_id}")
        return self._protocols[protocol_id]

    def list_protocols(self) -> List[ScaleProtocolConfig]:
        return list(self._protocols.values())

    def resolve(self, protocol_id: str, overrides: Dict[str, Any]) -> ScaleProtocolConfig:
        base = self.get(protocol_id)
        if not overrides:
            return base
        data = base.model_dump()
        merged = _deep_merge(data, overrides)
        return ScaleProtocolConfig.model_validate(merged)

    def save(self, protocol: ScaleProtocolConfig) -> Path:
        self.protocols_dir.mkdir(parents=True, exist_ok=True)
        path = self.protocols_dir / f"{protocol.id}.yaml"
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                protocol.model_dump(mode="json"),
                fh,
                allow_unicode=True,
                sort_keys=False,
            )
        self._protocols[protocol.id] = protocol
        return path

    def import_yaml(self, source: Path) -> ScaleProtocolConfig:
        with source.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        proto = ScaleProtocolConfig.model_validate(raw)
        self.save(proto)
        return proto

    def export_yaml(self, protocol_id: str, destination: Path) -> Path:
        proto = self.get(protocol_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                proto.model_dump(mode="json"),
                fh,
                allow_unicode=True,
                sort_keys=False,
            )
        return destination


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if key == "fields" and isinstance(value, list):
            field_map = {f["name"]: f for f in result.get("fields", [])}
            for item in value:
                name = item.get("name")
                if name in field_map:
                    field_map[name].update(item)
                else:
                    result.setdefault("fields", []).append(item)
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
