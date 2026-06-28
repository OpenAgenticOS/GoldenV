from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from goldenv.scales.base import WeightReading


@dataclass(frozen=True)
class ParseResult:
    reading: Optional[WeightReading]
    error: Optional[str] = None
    frame_hex: str = ""

    @property
    def ok(self) -> bool:
        return self.reading is not None and self.error is None
