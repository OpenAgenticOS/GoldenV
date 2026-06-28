from __future__ import annotations

import yaml
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from goldenv.config import AppConfig, scale_protocols_dir
from goldenv.config_io import save_app_config
from goldenv.scales.protocol_registry import ScaleProtocolRegistry
from goldenv.scales.serial_scale import list_serial_ports
from goldenv.ui import strings as S


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.SETTINGS_TITLE)
        self.config_path = config_path
        self.config = config.model_copy(deep=True)
        self.registry = ScaleProtocolRegistry(scale_protocols_dir(config_path))
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        cam_widget = QWidget()
        cam_tab = QFormLayout(cam_widget)
        cam = self.config.cameras[0] if self.config.cameras else None
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["simulated", "dahua", "usb_opencv"])
        if cam:
            self.kind_combo.setCurrentText(cam.kind)
        cam_tab.addRow(S.LABEL_CAMERA_KIND, self.kind_combo)

        self.ip_edit = QLineEdit(cam.ip if cam and cam.ip else "")
        cam_tab.addRow(S.LABEL_CAMERA_IP, self.ip_edit)

        self.exposure_spin = QSpinBox()
        self.exposure_spin.setRange(100, 1_000_000)
        self.exposure_spin.setValue(int(cam.exposure_us) if cam and cam.exposure_us else 8000)
        cam_tab.addRow(S.LABEL_EXPOSURE, self.exposure_spin)

        self.gain_edit = QLineEdit(str(cam.gain if cam and cam.gain is not None else 1.0))
        cam_tab.addRow(S.LABEL_GAIN, self.gain_edit)
        tabs.addTab(cam_widget, S.TAB_CAMERA)

        scale_widget = QWidget()
        scale_tab = QFormLayout(scale_widget)
        scale = self.config.scales[0] if self.config.scales else None
        self.protocol_combo = QComboBox()
        self._reload_protocol_combo()
        if scale:
            idx = self.protocol_combo.findData(scale.protocol_id)
            if idx >= 0:
                self.protocol_combo.setCurrentIndex(idx)
        scale_tab.addRow(S.LABEL_PROTOCOL, self.protocol_combo)

        proto_row = QHBoxLayout()
        btn_import = QPushButton(S.BTN_IMPORT_PROTOCOL)
        btn_import.clicked.connect(self._import_protocol)
        btn_export = QPushButton(S.BTN_EXPORT_PROTOCOL)
        btn_export.clicked.connect(self._export_protocol)
        proto_row.addWidget(btn_import)
        proto_row.addWidget(btn_export)
        scale_tab.addRow(S.LABEL_PROTOCOL_IO, proto_row)

        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.addItem("auto")
        for port in list_serial_ports():
            self.port_combo.addItem(port)
        if scale:
            self.port_combo.setCurrentText(scale.port)
        scale_tab.addRow(S.LABEL_PORT, self.port_combo)

        self.baud_spin = QSpinBox()
        self.baud_spin.setRange(1200, 921600)
        self.baud_spin.setValue(scale.baudrate if scale else 9600)
        scale_tab.addRow(S.LABEL_BAUDRATE, self.baud_spin)

        self.bytesize_spin = QSpinBox()
        self.bytesize_spin.setRange(5, 8)
        self.bytesize_spin.setValue(scale.bytesize if scale else 8)
        scale_tab.addRow(S.LABEL_BYTESIZE, self.bytesize_spin)

        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["N", "E", "O"])
        if scale:
            self.parity_combo.setCurrentText(scale.parity)
        scale_tab.addRow(S.LABEL_PARITY, self.parity_combo)

        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "1.5", "2"])
        if scale:
            self.stopbits_combo.setCurrentText(str(scale.stopbits))
        scale_tab.addRow(S.LABEL_STOPBITS, self.stopbits_combo)

        self.poll_enabled = QCheckBox(S.LABEL_POLL_ENABLED)
        self.poll_enabled.setChecked(scale.poll.enabled if scale else False)
        scale_tab.addRow(self.poll_enabled)

        self.poll_interval = QSpinBox()
        self.poll_interval.setRange(50, 5000)
        self.poll_interval.setValue(scale.poll.interval_ms if scale else 200)
        scale_tab.addRow(S.LABEL_POLL_INTERVAL, self.poll_interval)

        self.poll_cmd = QLineEdit(scale.poll.command_hex if scale else "500D0A")
        scale_tab.addRow(S.LABEL_POLL_COMMAND, self.poll_cmd)

        self.stable_threshold = QLineEdit(str(scale.stable.threshold_g if scale else 0.01))
        scale_tab.addRow(S.LABEL_STABLE_THRESHOLD, self.stable_threshold)

        self.stable_count = QSpinBox()
        self.stable_count.setRange(1, 20)
        self.stable_count.setValue(scale.stable.consecutive if scale else 3)
        scale_tab.addRow(S.LABEL_STABLE_COUNT, self.stable_count)
        tabs.addTab(scale_widget, S.TAB_SCALE)

        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(S.BTN_SAVE_SETTINGS)
        buttons.button(QDialogButtonBox.Cancel).setText(S.BTN_CANCEL)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _reload_protocol_combo(self) -> None:
        current = self.protocol_combo.currentData() if hasattr(self, "protocol_combo") else None
        self.protocol_combo.clear()
        self.registry.reload()
        for proto in self.registry.list_protocols():
            self.protocol_combo.addItem(proto.name, proto.id)
        if current:
            idx = self.protocol_combo.findData(current)
            if idx >= 0:
                self.protocol_combo.setCurrentIndex(idx)

    def _import_protocol(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, S.BTN_IMPORT_PROTOCOL, "", "YAML (*.yaml *.yml)"
        )
        if not path:
            return
        try:
            proto = self.registry.import_yaml(__import__("pathlib").Path(path))
            self._reload_protocol_combo()
            idx = self.protocol_combo.findData(proto.id)
            if idx >= 0:
                self.protocol_combo.setCurrentIndex(idx)
            QMessageBox.information(self, S.INFO_TITLE, S.MSG_PROTOCOL_IMPORTED.format(id=proto.id))
        except Exception as exc:
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _export_protocol(self) -> None:
        protocol_id = self.protocol_combo.currentData()
        if not protocol_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, S.BTN_EXPORT_PROTOCOL, f"{protocol_id}.yaml", "YAML (*.yaml *.yml)"
        )
        if not path:
            return
        try:
            self.registry.export_yaml(protocol_id, __import__("pathlib").Path(path))
            QMessageBox.information(self, S.INFO_TITLE, S.MSG_PROTOCOL_EXPORTED)
        except Exception as exc:
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _save(self) -> None:
        if self.config.cameras:
            cam = self.config.cameras[0]
            cam.kind = self.kind_combo.currentText()  # type: ignore[assignment]
            cam.ip = self.ip_edit.text() or None
            cam.exposure_us = float(self.exposure_spin.value())
            cam.gain = float(self.gain_edit.text())
        if self.config.scales:
            sc = self.config.scales[0]
            sc.protocol_id = self.protocol_combo.currentData()
            sc.port = self.port_combo.currentText()
            sc.baudrate = self.baud_spin.value()
            sc.bytesize = self.bytesize_spin.value()
            sc.parity = self.parity_combo.currentText()  # type: ignore[assignment]
            sc.stopbits = float(self.stopbits_combo.currentText())
            sc.poll.enabled = self.poll_enabled.isChecked()
            sc.poll.interval_ms = self.poll_interval.value()
            sc.poll.command_hex = self.poll_cmd.text().strip()
            sc.stable.threshold_g = float(self.stable_threshold.text())
            sc.stable.consecutive = self.stable_count.value()
        save_app_config(self.config_path, self.config)
        self.accept()
