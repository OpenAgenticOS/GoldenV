from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from goldenv.config import AppConfig, ScaleConfig
from goldenv.scales.base import WeightReading
from goldenv.scales.debug_bus import ScaleDebugBus
from goldenv.scales.factory import build_scale


class ScaleService:
    def __init__(
        self,
        config: AppConfig,
        config_path: Path,
        simulate: bool = False,
        on_debug: Optional[Callable[[str], None]] = None,
        debug_bus: Optional[ScaleDebugBus] = None,
    ):
        self.config = config
        self.config_path = config_path
        self.simulate = simulate
        self._scale = None
        self._scale_config: Optional[ScaleConfig] = config.scales[0] if config.scales else None
        self._on_debug = on_debug
        self.debug_bus = debug_bus or ScaleDebugBus.shared()

    @property
    def scale_config(self) -> ScaleConfig:
        if not self._scale_config:
            raise RuntimeError("未配置电子秤")
        return self._scale_config

    def connect(self) -> None:
        self._scale = build_scale(
            self.scale_config,
            config_path=self.config_path,
            simulate=self.simulate,
            on_debug=self._on_debug,
            debug_bus=self.debug_bus,
        )
        self._scale.connect()

    def disconnect(self) -> None:
        if self._scale:
            self._scale.disconnect()
        self._scale = None

    def read_weight(self) -> WeightReading:
        if not self._scale:
            raise RuntimeError("电子秤未连接")
        self._scale.poll_if_needed()
        return self._scale.read_weight()
