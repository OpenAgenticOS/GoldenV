from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from goldenv.config import ScaleConfig, scale_protocols_dir
from goldenv.scales.protocol_registry import ScaleProtocolRegistry
from goldenv.scales.serial_scale import SerialScale, SimulatedScale


def build_scale(
    config: ScaleConfig,
    config_path: Path | None = None,
    simulate: bool = False,
    on_debug: Optional[Callable[[str], None]] = None,
    debug_bus=None,
):
    if simulate:
        return SimulatedScale(config)
    registry = ScaleProtocolRegistry(scale_protocols_dir(config_path))
    protocol = registry.resolve(config.protocol_id, config.protocol_overrides)
    return SerialScale(config, protocol, on_debug=on_debug, debug_bus=debug_bus)
