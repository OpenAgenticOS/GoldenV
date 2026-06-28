from __future__ import annotations

import sys
import threading
import time
from collections import deque
from typing import Callable, Deque, List, Optional

from goldenv.config import ScaleConfig
from goldenv.scales.base import WeightReading
from goldenv.scales.debug_bus import ScaleDebugBus
from goldenv.scales.frame_buffer import FrameBuffer
from goldenv.scales.parsers import parse_frame_detailed
from goldenv.scales.protocol_registry import ScaleProtocolConfig


def list_serial_ports() -> List[str]:
    try:
        import serial.tools.list_ports
    except ImportError:
        return []
    ports = []
    for port in serial.tools.list_ports.comports():
        if sys.platform == "win32":
            ports.append(port.device)
        elif port.device.startswith("/dev/tty"):
            ports.append(port.device)
    return sorted(set(ports))


def resolve_port(port: str) -> Optional[str]:
    if port and port != "auto":
        return port
    available = list_serial_ports()
    return available[0] if available else None


class SerialScale:
    def __init__(
        self,
        config: ScaleConfig,
        protocol: ScaleProtocolConfig,
        on_debug: Optional[Callable[[str], None]] = None,
        debug_bus: Optional[ScaleDebugBus] = None,
    ):
        self.config = config
        self.protocol = protocol
        self.scale_id = config.id
        self._serial = None
        self._buffer = FrameBuffer()
        self._latest = WeightReading(value_g=0.0, stable=False, raw="")
        self._history: Deque[float] = deque(maxlen=10)
        self._stable_count = 0
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._on_debug = on_debug
        self._debug_bus = debug_bus or ScaleDebugBus.shared()
        self._last_poll = 0.0

    def connect(self) -> None:
        import serial

        port = resolve_port(self.config.port)
        if not port:
            raise RuntimeError("未找到可用串口")
        parity_map = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}
        self._serial = serial.Serial(
            port=port,
            baudrate=self.config.baudrate,
            bytesize=self.config.bytesize,
            parity=parity_map.get(self.config.parity, serial.PARITY_NONE),
            stopbits=self.config.stopbits,
            timeout=0.1,
        )
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        self._emit("info", f"已连接串口 {port}")

    def disconnect(self) -> None:
        self._running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=1.0)
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def poll_if_needed(self) -> None:
        if not self.config.poll.enabled or not self._serial:
            return
        now = time.monotonic()
        interval = self.config.poll.interval_ms / 1000.0
        if now - self._last_poll < interval:
            return
        self._last_poll = now
        data = bytes.fromhex(self.config.poll.command_hex)
        self._serial.write(data)
        self._emit("info", f"TX {data.hex(' ')}")

    def read_weight(self) -> WeightReading:
        with self._lock:
            return self._latest

    def _read_loop(self) -> None:
        while self._running and self._serial:
            try:
                self.poll_if_needed()
                waiting = self._serial.in_waiting
                if waiting:
                    chunk = self._serial.read(waiting)
                    self._buffer.feed(chunk)
                    self._emit("rx", chunk.hex(" "))
                    self._process_buffer()
            except Exception as exc:
                self._emit("error", f"串口错误: {exc}")
                time.sleep(0.5)

    def _process_buffer(self) -> None:
        if self.protocol.type == "fixed_length":
            length = self.protocol.frame_length
            while length:
                frame = self._buffer.pop_fixed(length)
                if frame is None:
                    break
                self._handle_frame(frame)
        elif self.protocol.type == "delimiter":
            header = bytes.fromhex(self.protocol.header_hex) if self.protocol.header_hex else b"\x02"
            tail = bytes.fromhex(self.protocol.tail_hex) if self.protocol.tail_hex else b"\x03"
            frame = self._buffer.pop_delimited(header, tail)
            if frame:
                self._handle_frame(frame)
        else:
            ending = self.protocol.line_ending.encode(self.protocol.encoding)
            for line in self._buffer.pop_lines(ending):
                self._handle_frame(line)

    def _handle_frame(self, frame: bytes) -> None:
        result = parse_frame_detailed(self.protocol, frame)
        if result.ok and result.reading:
            self._update_reading(result.reading)
            self._emit(
                "parse_ok",
                f"{result.reading.value_g:.3f} g 稳定={result.reading.stable}",
            )
        else:
            msg = result.error or "未知解析错误"
            self._emit("parse_fail", f"{msg} | {result.frame_hex}")

    def _update_reading(self, reading: WeightReading) -> None:
        if self.protocol.stable_inference == "variance" or not reading.stable:
            self._history.append(reading.value_g)
            if len(self._history) >= self.config.stable.consecutive:
                recent = list(self._history)[-self.config.stable.consecutive :]
                if max(recent) - min(recent) <= self.config.stable.threshold_g:
                    reading = WeightReading(
                        value_g=reading.value_g,
                        stable=True,
                        raw=reading.raw,
                        unit=reading.unit,
                    )
        if reading.stable:
            self._stable_count += 1
        else:
            self._stable_count = 0
        if self._stable_count >= self.config.stable.consecutive:
            reading = WeightReading(
                value_g=reading.value_g,
                stable=True,
                raw=reading.raw,
                unit=reading.unit,
            )
        with self._lock:
            self._latest = reading

    def _emit(self, kind: str, message: str) -> None:
        self._debug_bus.emit(kind, message)  # type: ignore[arg-type]
        if self._on_debug:
            self._on_debug(message)


class SimulatedScale:
    """无硬件时的模拟秤。"""

    def __init__(self, config: ScaleConfig):
        self.config = config
        self.scale_id = config.id
        self._value = 12.35
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def poll_if_needed(self) -> None:
        return

    def read_weight(self) -> WeightReading:
        if not self._connected:
            raise RuntimeError("电子秤未连接")
        return WeightReading(value_g=self._value, stable=True, raw=f"{self._value:.2f} g", unit="g")
