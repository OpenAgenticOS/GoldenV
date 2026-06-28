from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from goldenv.config_io import CalibrationValues, save_calibration
from goldenv.services.vision_service import VisionService
from goldenv.ui import strings as S


class CalibrationWizard(QDialog):
    def __init__(self, vision: VisionService, config_path, config, parent=None):
        super().__init__(parent)
        self.vision = vision
        self.config_path = config_path
        self.config = config
        cal = vision.camera_config.calibration
        self.mm_per_pixel = cal.mm_per_pixel
        self.mm_per_pixel_x: Optional[float] = cal.mm_per_pixel_x
        self.mm_per_pixel_y: Optional[float] = cal.mm_per_pixel_y
        self._preview_before_mm: Optional[float] = None
        self._saved = False
        self.setWindowTitle(S.CALIBRATION_TITLE)
        self.resize(480, 420)
        self._build_ui()
        self._load_current_values()

    @property
    def saved(self) -> bool:
        return self._saved

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        ring_tab = QWidget()
        ring_layout = QVBoxLayout(ring_tab)
        ring_layout.addWidget(QLabel(S.CALIBRATION_PROMPT))

        ring_form = QFormLayout()
        self.known_diameter = QDoubleSpinBox()
        self.known_diameter.setRange(40.0, 80.0)
        self.known_diameter.setDecimals(2)
        self.known_diameter.setValue(58.0)
        ring_form.addRow(S.LABEL_KNOWN_DIAMETER, self.known_diameter)
        ring_layout.addLayout(ring_form)

        ring_btn_row = QHBoxLayout()
        btn_preview = QPushButton(S.BTN_MEASURE_PREVIEW)
        btn_preview.clicked.connect(self._preview_measure)
        btn_apply = QPushButton(S.BTN_RUN_CALIBRATION)
        btn_apply.clicked.connect(self._apply_ring_calibration)
        ring_btn_row.addWidget(btn_preview)
        ring_btn_row.addWidget(btn_apply)
        ring_layout.addLayout(ring_btn_row)

        result_box = QGroupBox(S.LABEL_CURRENT_SCALE)
        result_form = QFormLayout(result_box)
        self.label_before = QLabel("—")
        self.label_after = QLabel("—")
        self.label_error = QLabel("—")
        self.label_scale_change = QLabel("—")
        result_form.addRow(S.LABEL_RESULT_BEFORE, self.label_before)
        result_form.addRow(S.LABEL_RESULT_AFTER, self.label_after)
        result_form.addRow(S.LABEL_RESULT_ERROR, self.label_error)
        result_form.addRow(S.LABEL_MM_PER_PIXEL, self.label_scale_change)
        ring_layout.addWidget(result_box)
        ring_layout.addStretch()
        tabs.addTab(ring_tab, S.TAB_RING_CALIBRATION)

        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        manual_layout.addWidget(QLabel(S.LABEL_CALIBRATION_HINT))

        self.separate_xy = QCheckBox(S.LABEL_SEPARATE_XY)
        self.separate_xy.toggled.connect(self._toggle_xy_inputs)
        manual_layout.addWidget(self.separate_xy)

        manual_form = QFormLayout()
        self.uniform_scale = QDoubleSpinBox()
        self.uniform_scale.setRange(0.0001, 10.0)
        self.uniform_scale.setDecimals(6)
        self.uniform_scale.setSingleStep(0.001)
        manual_form.addRow(S.LABEL_MM_PER_PIXEL, self.uniform_scale)

        self.scale_x = QDoubleSpinBox()
        self.scale_x.setRange(0.0001, 10.0)
        self.scale_x.setDecimals(6)
        self.scale_x.setSingleStep(0.001)
        self.scale_x.setEnabled(False)
        manual_form.addRow(S.LABEL_MM_PER_PIXEL_X, self.scale_x)

        self.scale_y = QDoubleSpinBox()
        self.scale_y.setRange(0.0001, 10.0)
        self.scale_y.setDecimals(6)
        self.scale_y.setSingleStep(0.001)
        self.scale_y.setEnabled(False)
        manual_form.addRow(S.LABEL_MM_PER_PIXEL_Y, self.scale_y)
        manual_layout.addLayout(manual_form)

        btn_save_manual = QPushButton(S.BTN_SAVE_MANUAL)
        btn_save_manual.clicked.connect(self._save_manual)
        manual_layout.addWidget(btn_save_manual)
        manual_layout.addStretch()
        tabs.addTab(manual_tab, S.TAB_MANUAL_CALIBRATION)

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText(S.BTN_CANCEL)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _load_current_values(self) -> None:
        cal = self.vision.camera_config.calibration
        self.uniform_scale.setValue(cal.mm_per_pixel)
        has_xy = cal.mm_per_pixel_x is not None or cal.mm_per_pixel_y is not None
        self.separate_xy.setChecked(has_xy)
        self.scale_x.setValue(cal.mm_per_pixel_x or cal.mm_per_pixel)
        self.scale_y.setValue(cal.mm_per_pixel_y or cal.mm_per_pixel)
        self._update_scale_label()

    def _toggle_xy_inputs(self, enabled: bool) -> None:
        self.uniform_scale.setEnabled(not enabled)
        self.scale_x.setEnabled(enabled)
        self.scale_y.setEnabled(enabled)

    def _current_scale_x(self) -> float:
        cal = self.vision.camera_config.calibration
        return cal.mm_per_pixel_x or cal.mm_per_pixel

    def _current_scale_y(self) -> float:
        cal = self.vision.camera_config.calibration
        return cal.mm_per_pixel_y or cal.mm_per_pixel

    def _avg_scale(self) -> float:
        return (self._current_scale_x() + self._current_scale_y()) / 2

    def _update_scale_label(self) -> None:
        cal = self.vision.camera_config.calibration
        if cal.mm_per_pixel_x is not None or cal.mm_per_pixel_y is not None:
            text = (
                f"X={self._current_scale_x():.6f}，"
                f"Y={self._current_scale_y():.6f}，"
                f"统一={cal.mm_per_pixel:.6f}"
            )
        else:
            text = f"{cal.mm_per_pixel:.6f}（统一）"
        self.label_scale_change.setText(text)

    def _preview_measure(self) -> None:
        try:
            result = self.vision.measure_inner_diameter()
            self._preview_before_mm = result.values[0].value
            self.label_before.setText(f"{self._preview_before_mm:.2f} mm")
            self.label_after.setText("—")
            self.label_error.setText("—")
            QMessageBox.information(
                self,
                S.INFO_TITLE,
                S.MSG_CALIBRATION_PREVIEW.format(before=self._preview_before_mm),
            )
        except Exception as exc:
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _apply_ring_calibration(self) -> None:
        try:
            known = self.known_diameter.value()
            if self._preview_before_mm is None:
                result = self.vision.measure_inner_diameter()
                self._preview_before_mm = result.values[0].value
                self.label_before.setText(f"{self._preview_before_mm:.2f} mm")

            measured_mm = self._preview_before_mm
            if measured_mm <= 0:
                raise ValueError("测量内径无效")

            scale_factor = known / measured_mm
            cal = self.vision.camera_config.calibration
            old_x = self._current_scale_x()
            old_y = self._current_scale_y()
            new_x = old_x * scale_factor
            new_y = old_y * scale_factor
            new_uniform = cal.mm_per_pixel * scale_factor

            if cal.mm_per_pixel_x is not None or cal.mm_per_pixel_y is not None:
                values = CalibrationValues(
                    mm_per_pixel=new_uniform,
                    mm_per_pixel_x=new_x,
                    mm_per_pixel_y=new_y,
                )
            else:
                values = CalibrationValues(
                    mm_per_pixel=new_uniform,
                    mm_per_pixel_x=None,
                    mm_per_pixel_y=None,
                )

            self._apply_values(values)

            after_mm = measured_mm * scale_factor
            error_pct = abs(after_mm - known) / known * 100 if known else 0
            self.label_after.setText(f"{after_mm:.2f} mm（目标 {known:.2f} mm）")
            self.label_error.setText(f"{error_pct:.2f} %")
            self._update_scale_label()

            QMessageBox.information(
                self,
                S.INFO_TITLE,
                S.MSG_CALIBRATION_APPLIED.format(
                    before=measured_mm,
                    after=after_mm,
                    error=error_pct,
                    old_scale=(old_x + old_y) / 2,
                    new_scale=(new_x + new_y) / 2,
                ),
            )
        except Exception as exc:
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _save_manual(self) -> None:
        try:
            if self.separate_xy.isChecked():
                values = CalibrationValues(
                    mm_per_pixel=self.uniform_scale.value(),
                    mm_per_pixel_x=self.scale_x.value(),
                    mm_per_pixel_y=self.scale_y.value(),
                )
            else:
                uniform = self.uniform_scale.value()
                values = CalibrationValues(
                    mm_per_pixel=uniform,
                    mm_per_pixel_x=None,
                    mm_per_pixel_y=None,
                )
            self._apply_values(values)
            self._update_scale_label()
            QMessageBox.information(self, S.INFO_TITLE, S.MSG_MANUAL_SAVED)
        except Exception as exc:
            QMessageBox.critical(self, S.ERROR_TITLE, str(exc))

    def _apply_values(self, values: CalibrationValues) -> None:
        self.vision.apply_calibration(values)
        self.mm_per_pixel = values.mm_per_pixel
        self.mm_per_pixel_x = values.mm_per_pixel_x
        self.mm_per_pixel_y = values.mm_per_pixel_y
        save_calibration(self.config_path, self.config, values)
        self._saved = True
        self.uniform_scale.setValue(values.mm_per_pixel)
        if values.mm_per_pixel_x is not None:
            self.scale_x.setValue(values.mm_per_pixel_x)
        if values.mm_per_pixel_y is not None:
            self.scale_y.setValue(values.mm_per_pixel_y)
