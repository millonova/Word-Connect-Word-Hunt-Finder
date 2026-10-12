"""Settings Modal Dialog for Word Hunt / Boggle Solver Pro.

Features card-based groupings:
- Capture Card: Inset crop ratio & Sniper ROI dimension inputs.
- Window Behavior Card: Always-on-Top toggles for Main Window and Sniper Overlay.
- OCR Engine Card: Tesseract binary picker with live "Test Path" verification.
- Sticky bottom actions: Cancel and Save & Apply.
"""

import os
import subprocess
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QSpinBox,
    QDoubleSpinBox, QSlider, QFileDialog, QFrame, QMessageBox
)
from PyQt6.QtGui import QFont, QColor

from word_connect.core.config import AppConfig
from word_connect.core.path_utils import get_resource_path
from .styles import Theme


SETTINGS_STYLESHEET = f"""
QDialog {{
    background-color: {Theme.BG_OBSIDIAN};
    color: {Theme.TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, sans-serif;
}}

/* Card Containers */
QFrame.settings-card {{
    background-color: {Theme.BG_SURFACE};
    border: 1px solid {Theme.BORDER_SUBTLE};
    border-radius: 12px;
    padding: 14px;
}}

QLabel.card-heading {{
    font-size: 13px;
    font-weight: 800;
    color: {Theme.EMERALD_PRIMARY};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QLabel.card-desc {{
    font-size: 11px;
    color: {Theme.TEXT_MUTED};
    margin-bottom: 6px;
}}

QLabel.field-label {{
    color: {Theme.TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
}}

/* Form Inputs */
QLineEdit {{
    background-color: {Theme.BG_INPUT};
    border: 1px solid {Theme.BORDER_DEFAULT};
    border-radius: 8px;
    color: {Theme.TEXT_PRIMARY};
    padding: 7px 10px;
    font-size: 12px;
}}
QLineEdit:focus {{
    border-color: {Theme.EMERALD_PRIMARY};
    background-color: {Theme.BG_INPUT_FOCUS};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {Theme.BG_INPUT};
    border: 1px solid {Theme.BORDER_DEFAULT};
    border-radius: 8px;
    color: {Theme.TEXT_PRIMARY};
    font-weight: 700;
    font-size: 12px;
    padding: 5px 8px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {Theme.EMERALD_PRIMARY};
}}

QCheckBox {{
    color: {Theme.TEXT_PRIMARY};
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {Theme.BORDER_DEFAULT};
    background-color: {Theme.BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {Theme.EMERALD_PRIMARY};
    border-color: {Theme.EMERALD_PRIMARY};
}}

/* Buttons */
QPushButton.primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Theme.EMERALD_PRIMARY}, stop:1 #15803D);
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
    border-radius: 8px;
    padding: 8px 18px;
    border: none;
}}
QPushButton.primary:hover {{
    background: {Theme.EMERALD_HOVER};
    color: #090D14;
}}

QPushButton.secondary {{
    background-color: {Theme.BG_SURFACE};
    color: {Theme.TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 600;
    border-radius: 8px;
    padding: 7px 14px;
    border: 1px solid {Theme.BORDER_DEFAULT};
}}
QPushButton.secondary:hover {{
    background-color: {Theme.BG_SURFACE_HOVER};
    border-color: {Theme.BORDER_HOVER};
}}

/* Test Indicator Badges */
QLabel.badge-ok {{
    background-color: {Theme.EMERALD_BADGE_BG};
    color: {Theme.EMERALD_BADGE_TXT};
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
}}
QLabel.badge-warn {{
    background-color: #451A03;
    color: #FBBF24;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
}}
"""


class SettingsDialog(QDialog):
    """Modern card-based preferences and configuration dialog."""

    settings_applied = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences - Word Hunt Solver Pro")
        self.setFixedSize(540, 680)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        self.config = AppConfig()
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Dialog Title Header
        header_row = QHBoxLayout()
        lbl_title = QLabel("⚙ Settings & Hardware Tuning")
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {Theme.TEXT_PRIMARY};")
        header_row.addWidget(lbl_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        # -------------------------------------------------------------
        # Card 1: Capture & Sniper ROI Geometry
        # -------------------------------------------------------------
        card_capture = QFrame()
        card_capture.setProperty("class", "settings-card")
        cap_layout = QVBoxLayout(card_capture)
        cap_layout.setSpacing(10)

        lbl_cap_title = QLabel("📷 Capture & Inset Preprocessing")
        lbl_cap_title.setProperty("class", "card-heading")
        lbl_cap_desc = QLabel("Tune game tile border inset to crop out tile shadows and margins.")
        lbl_cap_desc.setProperty("class", "card-desc")
        cap_layout.addWidget(lbl_cap_title)
        cap_layout.addWidget(lbl_cap_desc)

        grid_geo = QGridLayout()
        grid_geo.setSpacing(8)

        # Position X, Y
        grid_geo.addWidget(QLabel("Position X:"), 0, 0)
        self.spin_x = QSpinBox()
        self.spin_x.setRange(0, 10000)
        grid_geo.addWidget(self.spin_x, 0, 1)

        grid_geo.addWidget(QLabel("Position Y:"), 0, 2)
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 10000)
        grid_geo.addWidget(self.spin_y, 0, 3)

        # Width, Height
        grid_geo.addWidget(QLabel("Width:"), 1, 0)
        self.spin_w = QSpinBox()
        self.spin_w.setRange(100, 5000)
        grid_geo.addWidget(self.spin_w, 1, 1)

        grid_geo.addWidget(QLabel("Height:"), 1, 2)
        self.spin_h = QSpinBox()
        self.spin_h.setRange(100, 5000)
        grid_geo.addWidget(self.spin_h, 1, 3)

        # Inset Crop Ratio
        grid_geo.addWidget(QLabel("Inset Crop:"), 2, 0)
        self.spin_crop = QDoubleSpinBox()
        self.spin_crop.setRange(0.05, 0.40)
        self.spin_crop.setSingleStep(0.01)
        self.spin_crop.setDecimals(2)
        grid_geo.addWidget(self.spin_crop, 2, 1)

        btn_reset_roi = QPushButton("↺ Reset (930x930)")
        btn_reset_roi.setProperty("class", "secondary")
        btn_reset_roi.clicked.connect(self._reset_default_roi)
        grid_geo.addWidget(btn_reset_roi, 2, 2, 1, 2)

        cap_layout.addLayout(grid_geo)
        layout.addWidget(card_capture)

        # -------------------------------------------------------------
        # Card 2: Window Behavior
        # -------------------------------------------------------------
        card_win = QFrame()
        card_win.setProperty("class", "settings-card")
        win_layout = QVBoxLayout(card_win)
        win_layout.setSpacing(10)

        lbl_win_title = QLabel("🪟 Window Display & Layering")
        lbl_win_title.setProperty("class", "card-heading")
        lbl_win_desc = QLabel("Keep windows pinned above game emulators or mobile mirror clients.")
        lbl_win_desc.setProperty("class", "card-desc")
        win_layout.addWidget(lbl_win_title)
        win_layout.addWidget(lbl_win_desc)

        self.chk_main_always_on_top = QCheckBox("Keep Solver Main Window Always on Top")
        self.chk_overlay_always_on_top = QCheckBox("Keep Sniper Overlay Always on Top")
        win_layout.addWidget(self.chk_main_always_on_top)
        win_layout.addWidget(self.chk_overlay_always_on_top)

        layout.addWidget(card_win)

        # -------------------------------------------------------------
        # Card 3: OCR & Template Matching Engine
        # -------------------------------------------------------------
        card_ocr = QFrame()
        card_ocr.setProperty("class", "settings-card")
        ocr_layout = QVBoxLayout(card_ocr)
        ocr_layout.setSpacing(10)

        lbl_ocr_title = QLabel("🔍 Recognition Engine & OCR Fallback")
        lbl_ocr_title.setProperty("class", "card-heading")
        lbl_ocr_desc = QLabel("Primary engine uses autonomous OpenCV template matching (no install needed).")
        lbl_ocr_desc.setProperty("class", "card-desc")
        ocr_layout.addWidget(lbl_ocr_title)
        ocr_layout.addWidget(lbl_ocr_desc)

        tess_row = QHBoxLayout()
        self.txt_tesseract = QLineEdit()
        self.txt_tesseract.setPlaceholderText("Optional path to tesseract.exe")
        btn_browse = QPushButton("Browse...")
        btn_browse.setProperty("class", "secondary")
        btn_browse.clicked.connect(self._browse_tesseract)
        tess_row.addWidget(self.txt_tesseract)
        tess_row.addWidget(btn_browse)
        ocr_layout.addLayout(tess_row)

        test_row = QHBoxLayout()
        btn_test = QPushButton("⚡ Test OCR Path")
        btn_test.setProperty("class", "secondary")
        btn_test.clicked.connect(self._test_tesseract_path)
        
        self.lbl_test_result = QLabel("● Built-in Template Engine Active")
        self.lbl_test_result.setProperty("class", "badge-ok")
        test_row.addWidget(btn_test)
        test_row.addWidget(self.lbl_test_result)
        test_row.addStretch()
        ocr_layout.addLayout(test_row)

        layout.addWidget(card_ocr)

        layout.addStretch()

        # -------------------------------------------------------------
        # Sticky Bottom Actions
        # -------------------------------------------------------------
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "secondary")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save & Apply Changes")
        btn_save.setProperty("class", "primary")
        btn_save.clicked.connect(self._save_and_apply)

        btn_bar.addWidget(btn_cancel)
        btn_bar.addWidget(btn_save)
        layout.addLayout(btn_bar)

    def _load_values(self) -> None:
        self.chk_main_always_on_top.setChecked(self.config.get_always_on_top())
        self.chk_overlay_always_on_top.setChecked(self.config.get_overlay_always_on_top())

        roi = self.config.get_sniper_overlay_geometry()
        self.spin_x.setValue(roi.get("x", 300))
        self.spin_y.setValue(roi.get("y", 200))
        self.spin_w.setValue(roi.get("width", 930))
        self.spin_h.setValue(roi.get("height", 930))

        self.spin_crop.setValue(self.config.get_inset_crop_ratio())
        self.txt_tesseract.setText(self.config.get_tesseract_path())
        self._test_tesseract_path(silent=True)

    def _reset_default_roi(self) -> None:
        self.spin_x.setValue(300)
        self.spin_y.setValue(200)
        self.spin_w.setValue(930)
        self.spin_h.setValue(930)
        self.spin_crop.setValue(0.20)

    def _browse_tesseract(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Tesseract Binary",
            r"C:\Program Files\Tesseract-OCR",
            "Executable (*.exe);;All Files (*)"
        )
        if file_path:
            self.txt_tesseract.setText(file_path)
            self._test_tesseract_path()

    def _test_tesseract_path(self, silent: bool = False) -> None:
        path = self.txt_tesseract.text().strip()
        if not path:
            bundled = get_resource_path("assets/tesseract/tesseract.exe")
            if os.path.exists(bundled):
                path = bundled

        if path and os.path.exists(path):
            try:
                res = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=2)
                first_line = res.stdout.splitlines()[0] if res.stdout else "Tesseract OCR"
                self.lbl_test_result.setText(f"● {first_line[:24]}")
                self.lbl_test_result.setProperty("class", "badge-ok")
                self.lbl_test_result.setStyle(self.lbl_test_result.style())
                return
            except Exception:
                pass

        self.lbl_test_result.setText("● Autonomous Template Engine (Active)")
        self.lbl_test_result.setProperty("class", "badge-ok")
        self.lbl_test_result.setStyle(self.lbl_test_result.style())

    def _save_and_apply(self) -> None:
        self.config.set_always_on_top(self.chk_main_always_on_top.isChecked())
        self.config.set_overlay_always_on_top(self.chk_overlay_always_on_top.isChecked())

        self.config.set_sniper_overlay_geometry(
            self.spin_x.value(),
            self.spin_y.value(),
            self.spin_w.value(),
            self.spin_h.value()
        )

        self.config.set_inset_crop_ratio(self.spin_crop.value())
        self.config.set_tesseract_path(self.txt_tesseract.text().strip())

        self.config.save()
        self.settings_applied.emit()
        self.accept()
