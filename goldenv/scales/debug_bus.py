from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Literal


DebugKind = Literal["rx", "parse_ok", "parse_fail", "info", "error"]


@dataclass(frozen=True)
class DebugEvent:
    kind: DebugKind
    message: str


class ScaleDebugBus:
    """串口调试事件总线（线程安全）。"""

    _instance: "ScaleDebugBus | None" = None

    def __init__(self, max_size: int = 500):
        self._events: Deque[DebugEvent] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    @classmethod
    def shared(cls) -> "ScaleDebugBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit(self, kind: DebugKind, message: str) -> None:
        with self._lock:
            self._events.append(DebugEvent(kind=kind, message=message))

    def drain(self) -> List[DebugEvent]:
        with self._lock:
            items = list(self._events)
            self._events.clear()
            return items
