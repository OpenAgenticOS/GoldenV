from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class CameraFrame:
    camera_id: str
    captured_at: datetime
    image: np.ndarray


class Camera(Protocol):
    camera_id: str

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def capture(self) -> CameraFrame: ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
