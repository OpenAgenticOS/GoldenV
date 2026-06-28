from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from goldenv.config import AppConfig
from goldenv.runtime.dahua_bootstrap import prepare_dahua_runtime
from goldenv.services.record_service import RecordService
from goldenv.services.scale_service import ScaleService
from goldenv.services.vision_service import VisionService
from goldenv.ui import strings as S
from goldenv.ui.calibration_wizard import CalibrationWizard
from goldenv.ui.first_run import maybe_prompt_mv_viewer
from goldenv.ui.scale_debug_panel import ScaleDebugPanel
from goldenv.ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    weight_updated = Signal(float, bool, str)

    def __init__(
        self,
        config: AppConfig,
        config_path,
        base_dir,
        simulate: bool = False,
    ):
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.base_dir = base_dir
        self.simulate = simulate

        self.vision = VisionService(config)
        self.scale = ScaleService(
            config,
            config_path,
            simulate=simulate,
            on_debug=self._on_scale_debug,
        )
        self.records = RecordService(config, base_dir)

        self._last_overlay: np.ndarray | None = None
        self._last_raw: np.ndarray | None = None
        self._inner_diameter: float | None = None
        self._weight_g: float | None = None
        self._weight_stable = False
        self._connected = False

        self.setWindowTitle(S.APP_TITLE)
        self.resize(1200, 800)
        self._build_ui()

        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)
        self._weight_timer = QTimer(self)
        self._weight_timer.timeout.connect(self._poll_weight)
        self.weight_updated.connect(self._on_weight_updated)

        self._refresh_history()
        maybe_prompt_mv_viewer(self, self.config)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        left = QVBoxLayout()
        self.preview_label = QLabel(S.LABEL_CAMERA_PREVIEW)
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background:#181818;color:#888;")
        left.addWidget(self.preview_label)

        btn_row = QHBoxLayout()
        for text, slot in [
            (S.BTN_CONNECT, self._connect_devices),
            (S.BTN_DISCONNECT, self._disconnect_devices),
            (S.BTN_ONE_CLICK_DETECT, self._one_click_detect),
            (S.BTN_MEASURE_DIAMETER, self._measure_diameter),
            (S.BTN_READ_WEIGHT, self._read_weight_once),
            (S.BTN_SAVE_RECORD, self._save_record),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        left.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        for text, slot in [
            (S.BTN_SETTINGS, self._open_settings),
            (S.BTN_CALIBRATE, self._open_calibration),
            (S.BTN_SCALE_DEBUG, self._open_debug),
            (S.BTN_EXPORT_CSV, self._export_csv),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn_row2.addWidget(btn)
        left.addLayout(btn_row2)
        root.addLayout(left, stretch=3)

        right = QVBoxLayout()
        self.diameter_label = QLabel(f"{S.LABEL_INNER_DIAMETER}：—")
        self.diameter_label.setFont(QFont("", 18))
        self.weight_label = QLabel(f"{S.LABEL_WEIGHT}：—")
        self.weight_label.setFont(QFont("", 18))
        self.status_label = QLabel(f"{S.LABEL_STATUS}：{S.STATUS_DISCONNECTED}")
        right.addWidget(self.diameter_label)
        right.addWidget(self.weight_label)
        right.addWidget(self.status_label)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            [S.COL_ID, S.COL_TIME, S.COL_DIAMETER, S.COL_WEIGHT, S.COL_NOTES]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        right.addWidget(QLabel(S.LABEL_HISTORY))
        right.addWidget(self.history_table)
        root.addLayout(right, stretch=2)

        self.statusBar().showMessage(S.STATUS_READY)

    @Slot(float, bool, str)
    def _on_weight_updated(self, value: float, stable: bool, raw: str) -> None:
        self._weight_g = value
        self._weight_stable = stable
        st = S.STATUS_STABLE if stable else S.STATUS_UNSTABLE
        self.weight_label.setText(f"{S.LABEL_WEIGHT}：{value:.3f} g ({st})")

    def _on_scale_debug(self, message: str) -> None:
        self.statusBar().showMessage(message, 3000)

    def _connect_devices(self) -> None:
        try:
            cam = self.config.cameras[0] if self.config.cameras else None
            if cam and cam.kind == "dahua" and not self.simulate:
                status = prepare_dahua_runtime()
                if not status.ready:
                    QMessageBox.warning(
                        self,
                        S.INFO_TITLE,
                        f"{status.message}\n\n{S.MSG_CAMERA_FALLBACK}",
                    )
                    self.simulate = True
            if self.config.cameras:
                self.vision.connect(simulate=self.simulate)
            if self.config.scales:
                self.scale.connect()
            self._connected = True
            self._preview_timer.start(200)
            self._weight_timer.start(300)
            self.status_label.setText(f"{S.LABEL_STATUS}：{S.STATUS_CONNECTED}")
            self.statusBar().showMessage(S.MSG_CONNECT_OK)
        except Exception as exc:
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _disconnect_devices(self) -> None:
        self._preview_timer.stop()
        self._weight_timer.stop()
        self.vision.disconnect()
        self.scale.disconnect()
        self._connected = False
        self.status_label.setText(f"{S.LABEL_STATUS}：{S.STATUS_DISCONNECTED}")
        self.statusBar().showMessage(S.MSG_DISCONNECT_OK)

    def _update_preview(self) -> None:
        if not self._connected:
            return
        try:
            frame = self.vision.capture_frame()
            self._show_image(frame)
        except Exception:
            pass

    def _show_image(self, image: np.ndarray) -> None:
        if image.ndim == 2:
            h, w = image.shape
            fmt = QImage.Format_Grayscale8
            qimg = QImage(image.data, w, h, w, fmt)
        else:
            rgb = image[:, :, ::-1].copy()
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_label.setPixmap(pix)

    def _one_click_detect(self) -> None:
        if not self._connected:
            if self.config.cameras or self.config.scales:
                self._connect_devices()
            if not self._connected:
                QMessageBox.warning(self, S.ERROR_TITLE, "请先连接设备")
                return
        errors: list[str] = []
        try:
            result = self.vision.measure_inner_diameter()
            self._last_overlay = result.overlay
            self._last_raw = self.vision.capture_frame()
            self._inner_diameter = result.values[0].value
            self.diameter_label.setText(
                f"{S.LABEL_INNER_DIAMETER}：{self._inner_diameter:.2f} mm"
            )
            self._show_image(result.overlay)
            if not result.quality_ok:
                errors.append(result.quality_message)
        except Exception as exc:
            errors.append(f"内径: {exc}")
            self.status_label.setText(f"{S.LABEL_STATUS}：{S.STATUS_MEASURE_FAILED}")

        if self.config.scales:
            try:
                reading = self.scale.read_weight()
                self.weight_updated.emit(reading.value_g, reading.stable, reading.raw)
                if not reading.stable:
                    errors.append("重量未稳定")
            except Exception as exc:
                errors.append(f"重量: {exc}")

        try:
            self.records.save_inspection(
                self.vision,
                self._inner_diameter,
                self._weight_g,
                self._last_overlay,
                self._last_raw,
                notes="一键检测",
                error="; ".join(errors) if errors else None,
            )
            self._refresh_history()
        except Exception as exc:
            errors.append(f"存库: {exc}")

        if errors:
            QMessageBox.warning(self, S.INFO_TITLE, f"{S.MSG_ONE_CLICK_PARTIAL}\n" + "\n".join(errors))
            self.statusBar().showMessage(S.MSG_ONE_CLICK_PARTIAL)
        else:
            self.statusBar().showMessage(S.MSG_ONE_CLICK_DONE)

    def _measure_diameter(self) -> None:
        if not self._connected:
            QMessageBox.warning(self, S.ERROR_TITLE, "请先连接设备")
            return
        self.statusBar().showMessage(S.STATUS_MEASURING)
        try:
            result = self.vision.measure_inner_diameter()
            self._last_overlay = result.overlay
            self._last_raw = self.vision.capture_frame()
            self._inner_diameter = result.values[0].value
            self.diameter_label.setText(
                f"{S.LABEL_INNER_DIAMETER}：{self._inner_diameter:.2f} mm"
            )
            self._show_image(result.overlay)
            if not result.quality_ok:
                QMessageBox.warning(self, S.INFO_TITLE, result.quality_message)
            self.statusBar().showMessage(S.STATUS_READY)
        except Exception as exc:
            self.status_label.setText(f"{S.LABEL_STATUS}：{S.STATUS_MEASURE_FAILED}")
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _read_weight_once(self) -> None:
        if not self._connected:
            QMessageBox.warning(self, S.ERROR_TITLE, "请先连接设备")
            return
        try:
            reading = self.scale.read_weight()
            self.weight_updated.emit(reading.value_g, reading.stable, reading.raw)
        except Exception as exc:
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _poll_weight(self) -> None:
        if not self._connected or not self.config.scales:
            return
        try:
            reading = self.scale.read_weight()
            self.weight_updated.emit(reading.value_g, reading.stable, reading.raw)
        except Exception:
            pass

    def _save_record(self) -> None:
        try:
            self.records.save_inspection(
                self.vision,
                self._inner_diameter,
                self._weight_g,
                self._last_overlay,
                self._last_raw,
            )
            self._refresh_history()
            self.statusBar().showMessage(S.MSG_SAVE_OK)
        except Exception as exc:
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _refresh_history(self) -> None:
        records = self.records.store.list_records(limit=50)
        self.history_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.history_table.setItem(row, 0, QTableWidgetItem(str(rec.id)))
            self.history_table.setItem(row, 1, QTableWidgetItem(rec.captured_at))
            d = "" if rec.inner_diameter_mm is None else f"{rec.inner_diameter_mm:.2f}"
            w = "" if rec.weight_g is None else f"{rec.weight_g:.3f}"
            self.history_table.setItem(row, 2, QTableWidgetItem(d))
            self.history_table.setItem(row, 3, QTableWidgetItem(w))
            self.history_table.setItem(row, 4, QTableWidgetItem(rec.notes))

    def _export_csv(self) -> None:
        from datetime import datetime

        path = self.base_dir / "data" / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        count = self.records.export_csv(path)
        QMessageBox.information(self, S.INFO_TITLE, f"{S.MSG_EXPORT_OK}\n{path}\n共 {count} 条")
        self.statusBar().showMessage(S.MSG_EXPORT_OK)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.config, self.config_path, self)
        if dlg.exec():
            self.config = dlg.config
            self.statusBar().showMessage("设置已更新，请重新连接设备")

    def _open_calibration(self) -> None:
        if not self._connected:
            QMessageBox.warning(self, S.ERROR_TITLE, "请先连接设备")
            return
        dlg = CalibrationWizard(self.vision, self.config_path, self.config, self)
        dlg.exec()
        if dlg.saved:
            x = dlg.mm_per_pixel_x if dlg.mm_per_pixel_x is not None else dlg.mm_per_pixel
            y = dlg.mm_per_pixel_y if dlg.mm_per_pixel_y is not None else dlg.mm_per_pixel
            self.statusBar().showMessage(
                S.MSG_CALIBRATE_OK.format(value=dlg.mm_per_pixel, x=x, y=y)
            )

    def _open_debug(self) -> None:
        dlg = ScaleDebugPanel(self.scale, self)
        dlg.exec()

    def closeEvent(self, event) -> None:
        self._disconnect_devices()
        super().closeEvent(event)
