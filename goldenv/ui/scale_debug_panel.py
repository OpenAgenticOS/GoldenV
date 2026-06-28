from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from goldenv.services.scale_service import ScaleService
from goldenv.ui import strings as S


class ScaleDebugPanel(QDialog):
    def __init__(self, scale: ScaleService, parent=None):
        super().__init__(parent)
        self.scale = scale
        self.setWindowTitle(S.DEBUG_TITLE)
        self.resize(720, 480)
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain_events)
        self._timer.start(150)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(S.LABEL_RAW_DATA))
        self.raw_log = QTextEdit()
        self.raw_log.setReadOnly(True)
        layout.addWidget(self.raw_log)

        layout.addWidget(QLabel(S.LABEL_PARSE_RESULT))
        self.parse_log = QTextEdit()
        self.parse_log.setReadOnly(True)
        layout.addWidget(self.parse_log)

        row = QHBoxLayout()
        btn_read = QPushButton(S.BTN_READ_WEIGHT)
        btn_read.clicked.connect(self._read_once)
        btn_clear = QPushButton(S.BTN_CLEAR_LOG)
        btn_clear.clicked.connect(self._clear_logs)
        row.addWidget(btn_read)
        row.addWidget(btn_clear)
        row.addStretch()
        layout.addLayout(row)

    def _clear_logs(self) -> None:
        self.raw_log.clear()
        self.parse_log.clear()

    def _append_colored(self, widget: QTextEdit, text: str, color: str) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", fmt)
        widget.setTextCursor(cursor)
        widget.ensureCursorVisible()

    def _drain_events(self) -> None:
        for event in self.scale.debug_bus.drain():
            if event.kind == "rx":
                self._append_colored(self.raw_log, f"RX {event.message}", "#4fc3f7")
            elif event.kind == "parse_ok":
                self._append_colored(self.parse_log, f"✓ {event.message}", "#81c784")
            elif event.kind == "parse_fail":
                self._append_colored(self.parse_log, f"✗ {event.message}", "#e57373")
            elif event.kind in ("info", "error"):
                color = "#ffb74d" if event.kind == "info" else "#ef5350"
                self._append_colored(self.parse_log, event.message, color)

    def _read_once(self) -> None:
        try:
            reading = self.scale.read_weight()
            stable = S.STATUS_STABLE if reading.stable else S.STATUS_UNSTABLE
            self._append_colored(
                self.parse_log,
                f"当前读数: {reading.value_g:.3f} g ({stable})",
                "#fff176",
            )
        except Exception as exc:
            self._append_colored(self.parse_log, f"错误: {exc}", "#ef5350")

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)
