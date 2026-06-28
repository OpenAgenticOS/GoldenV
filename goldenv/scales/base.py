from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class WeightReading:
    value_g: float
    stable: bool
    raw: str
    unit: str = "g"
    error: Optional[str] = None


class Scale(Protocol):
    scale_id: str

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def read_weight(self) -> WeightReading: ...

    def poll_if_needed(self) -> None: ...
