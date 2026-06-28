from __future__ import annotations

from typing import Iterator, List, Optional


class FrameBuffer:
    """串口字节流缓冲，按定长或分隔符切帧。"""

    def __init__(self, max_size: int = 4096):
        self._buffer = bytearray()
        self.max_size = max_size

    def feed(self, data: bytes) -> None:
        self._buffer.extend(data)
        if len(self._buffer) > self.max_size:
            self._buffer = self._buffer[-self.max_size :]

    def pop_fixed(self, length: int) -> Optional[bytes]:
        if len(self._buffer) < length:
            return None
        frame = bytes(self._buffer[:length])
        del self._buffer[:length]
        return frame

    def pop_delimited(self, header: bytes, tail: bytes) -> Optional[bytes]:
        start = self._buffer.find(header)
        if start == -1:
            if len(self._buffer) > len(header):
                self._buffer = self._buffer[-len(header) :]
            return None
        if start > 0:
            del self._buffer[:start]
        end = self._buffer.find(tail, len(header))
        if end == -1:
            return None
        end += len(tail)
        frame = bytes(self._buffer[:end])
        del self._buffer[:end]
        return frame

    def pop_lines(self, ending: bytes = b"\r\n") -> List[bytes]:
        lines: List[bytes] = []
        while True:
            idx = self._buffer.find(ending)
            if idx == -1:
                break
            line = bytes(self._buffer[:idx])
            del self._buffer[: idx + len(ending)]
            if line:
                lines.append(line)
        return lines

    @property
    def raw_hex(self) -> str:
        return self._buffer.hex(" ")
