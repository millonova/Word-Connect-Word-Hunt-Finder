"""PyQt6 Main Window for Word Hunt / Boggle Solver Pro.

Elevated Modern Design:
- Cohesive Top Header Bar with glowing live status pill badge & quick actions.
- Left Workspace: 4x4 Editable Board Matrix + Antialiased Glowing Swipe Path Visualizer.
- Right Solution Drawer: High-density ranked words with score badges, length chips, and instant search filter.
- Live Footer Status Bar displaying inference latency, sniper ROI, and solver metrics.
"""

import sys
import os
import time
from typing import List, Dict, Optional, Tuple

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSlider, QFileDialog,
    QMessageBox, QFrame, QStatusBar, QCheckBox
)
from PyQt6.QtGui import (
    QFont, QColor, QBrush, QPen, QKeyEvent, QKeySequence, QShortcut,
    QMoveEvent, QResizeEvent, QCloseEvent
)

from word_connect.core.solver import BoggleSolver, Path, Grid
from word_connect.core.dictionary import WordDictionary, calculate_word_score
from word_connect.core.vision import VisionEngine
from word_connect.core.config import AppConfig
from word_connect.ui.overlay import OverlayWindow
from word_connect.ui.settings_dialog import SettingsDialog
from word_connect.ui.mini_board import MiniBoardWidget
from word_connect.ui.styles import MAIN_STYLESHEET, Theme


class ScanWorker(QThread):
    """Background QThread for continuous live scan or single-shot snapshot."""

    scan_completed = pyqtSignal(list, dict, float, int)
    status_updated = pyqtSignal(str)

    def __init__(self, vision_engine: VisionEngine, dictionary: WordDictionary) -> None:
        super().__init__()
        self.vision = vision_engine
        self.dictionary = dictionary
        self.running = False
        self.is_live_mode = False
        self.single_shot_requested = False
        self.roi: Tuple[int, int, int, int] = (300, 200, 930, 930)
        self.interval_sec = 1.0
        self._scan_generation = 0

    def update_roi(self, x: int, y: int, w: int, h: int) -> None:
        self.roi = (x, y, w, h)

    def trigger_snap_and_solve(self) -> int:
        self._scan_generation += 1
        self.single_shot_requested = True
        if not self.isRunning():
            self.start()
        return self._scan_generation

    def set_live_mode(self, enabled: bool) -> int:
        self._scan_generation += 1
        self.is_live_mode = enabled
        if enabled:
            self.running = True
            if not self.isRunning():
                self.start()
        else:
            if not self.single_shot_requested:
                self.running = False
        return self._scan_generation

    def cancel_active_scan(self) -> None:
        """Safely invalidate any pending or in-flight scan tasks."""
        self._scan_generation += 1
        self.single_shot_requested = False

    def stop(self) -> None:
        self.running = False
        self.is_live_mode = False
        self.single_shot_requested = False
        self._scan_generation += 1
        if self.isRunning():
            self.wait(1000)

    def run(self) -> None:
        self.running = True
        solver = BoggleSolver()

        while self.running:
            do_scan = self.single_shot_requested or self.is_live_mode
            if do_scan:
                self.single_shot_requested = False
                cur_gen = self._scan_generation
                x, y, w, h = self.roi

                # 1. Grab Frame
                frame = self.vision.capture_roi(x, y, w, h)
                if not self.running or cur_gen != self._scan_generation:
                    if not self.is_live_mode:
                        break
                    continue

                if frame is not None and frame.size > 0:
                    # 2. Vision & Tile Letter Recognition
                    grid, ocr_time = self.vision.process_board_roi(frame)
                    if not self.running or cur_gen != self._scan_generation:
                        if not self.is_live_mode:
                            break
                        continue

                    # 3. Solve Board
                    solver.set_grid(grid)
                    all_words = solver.find_all_dictionary_words(self.dictionary.get_word_list())
                    if not self.running or cur_gen != self._scan_generation:
                        if not self.is_live_mode:
                            break
                        continue

                    self.scan_completed.emit(grid, all_words, ocr_time, cur_gen)
                    self.status_updated.emit(f"Vision Latency: {ocr_time:.0f}ms | Words Found: {len(all_words)}")
                else:
                    if cur_gen == self._scan_generation:
                        self.status_updated.emit("Failed to capture screen ROI.")

            if not self.is_live_mode:
                break

            # Interruptible sleep in 50ms slices (responsive cancelation)
            sleep_ticks = int(max(0.1, self.interval_sec) / 0.05)
            for _ in range(max(1, sleep_ticks)):
                if not self.running or not self.is_live_mode:
                    break
                time.sleep(0.05)


class WordHuntApp(QMainWindow):
    """Main Application Window with Modern Design System & Fluent Layout."""

    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig()

        # Window Flags & Geometry
        self.setWindowTitle("Word Hunt Solver Pro")
        saved_main_geo = self.config.get_main_window_geometry()
        self.setGeometry(
            saved_main_geo.get("x", 100),
            saved_main_geo.get("y", 100),
            saved_main_geo.get("width", 1120),
            saved_main_geo.get("height", 800)
        )
        self.setStyleSheet(MAIN_STYLESHEET)

        if self.config.get_always_on_top():
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        # Initialize engines
        self.dictionary = WordDictionary()
        self.vision = VisionEngine(tesseract_cmd=self.config.get_tesseract_path() or None)
        self.solver = BoggleSolver()

        # Word results cache
        self._active_scan_generation: int = 0
        self.current_results: List[Tuple[str, int, int, Path]] = []
        self.current_grid: Grid = [
            ["C", "D", "F", "E"],
            ["N", "E", "A", "M"],
            ["A", "R", "T", "G"],
            ["D", "C", "O", "N"]
        ]
        self.last_latency_ms: float = 0.0

        # Restore Sniper Overlay Window with saved ROI
        saved_roi = self.config.get_sniper_overlay_geometry()
        init_rect = QRect(
            saved_roi.get("x", 300),
            saved_roi.get("y", 200),
            saved_roi.get("width", 930),
            saved_roi.get("height", 930)
        )
        self.overlay = OverlayWindow(initial_rect=init_rect)
        self.overlay.roi_changed.connect(self._on_roi_changed)

        if self.config.get_overlay_visible():
            self.overlay.show()
        else:
            self.overlay.hide()

        # Background Worker Thread
        self.worker = ScanWorker(self.vision, self.dictionary)
        self.worker.interval_sec = self.config.get_scan_interval()
        self.worker.scan_completed.connect(self._on_scan_completed)
        self.worker.status_updated.connect(self._on_status_updated)
        self.worker.update_roi(*self.overlay.get_roi_rect())

        self._build_ui()
        self._recalculate_solutions(self.current_grid)
        self._update_status_display("Ready")

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(14)

        # =============================================================
        # 1. Header Bar: Brand, Status Badge & Primary Action Controls
        # =============================================================
        header_bar = QFrame()
        header_bar.setProperty("class", "card")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(14)

        # Brand & Status Pill
        brand_box = QHBoxLayout()
        brand_box.setSpacing(10)
        lbl_icon = QLabel("🎯")
        lbl_icon.setStyleSheet("font-size: 20px;")
        
        lbl_app_name = QLabel("Word Hunt Solver Pro")
        lbl_app_name.setProperty("class", "app-title")

        self.badge_status = QLabel("● READY")
        self.badge_status.setProperty("class", "status-pill-ready")

        brand_box.addWidget(lbl_icon)
        brand_box.addWidget(lbl_app_name)
        brand_box.addWidget(self.badge_status)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Action Buttons Toolbar
        actions_box = QHBoxLayout()
        actions_box.setSpacing(10)

        # Snap & Solve (F8)
        self.btn_snap_solve = QPushButton("⚡ Snap & Solve (F8)")
        self.btn_snap_solve.setProperty("class", "primary")
        self.btn_snap_solve.clicked.connect(self._snap_and_solve)
        actions_box.addWidget(self.btn_snap_solve)

        # Live Scan Toggle
        self.btn_live_scan = QPushButton("▶ Live Scan")
        self.btn_live_scan.setProperty("class", "secondary")
        self.btn_live_scan.clicked.connect(self._toggle_live_scan)
        actions_box.addWidget(self.btn_live_scan)

        # Scan Interval Slider
        interval_box = QHBoxLayout()
        interval_box.setSpacing(6)
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(2, 50)  # 0.2s to 5.0s
        self.slider_speed.setValue(int(round(self.config.get_scan_interval() * 10)))
        self.slider_speed.setFixedWidth(80)
        self.slider_speed.setToolTip("Continuous scan polling interval (0.2s - 5.0s)")
        self.lbl_speed_val = QLabel(f"{self.config.get_scan_interval():.1f}s")
        self.lbl_speed_val.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {Theme.TEXT_SECONDARY}; min-width: 28px;")
        self.slider_speed.valueChanged.connect(self._on_speed_changed)
        interval_box.addWidget(self.slider_speed)
        interval_box.addWidget(self.lbl_speed_val)
        actions_box.addLayout(interval_box)

        # Sniper Overlay Toggle (F9)
        self.btn_toggle_sniper = QPushButton(
            "🎯 Sniper: Visible" if self.config.get_overlay_visible() else "🎯 Sniper: Hidden"
        )
        self.btn_toggle_sniper.setProperty("class", "secondary")
        self.btn_toggle_sniper.clicked.connect(self._toggle_sniper_overlay)
        actions_box.addWidget(self.btn_toggle_sniper)

        # Settings Gear Icon
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setProperty("class", "icon-button")
        self.btn_settings.setToolTip("Open Preferences & Settings (ROI, Crop, OCR)")
        self.btn_settings.clicked.connect(self._open_settings)
        actions_box.addWidget(self.btn_settings)

        header_layout.addLayout(actions_box)
        root_layout.addWidget(header_bar)

        # =============================================================
        # 2. Main Workspace Split: Left (Board Matrix) | Right (Drawer)
        # =============================================================
        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        # -------------------------------------------------------------
        # Left Workspace: 4x4 Board Matrix + Path Visualizer
        # -------------------------------------------------------------
        left_card = QFrame()
        left_card.setProperty("class", "card")
        left_card.setFixedWidth(430)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 16, 18, 16)
        left_layout.setSpacing(12)

        # Section Heading
        matrix_header = QHBoxLayout()
        lbl_matrix_title = QLabel("4x4 BOARD MATRIX")
        lbl_matrix_title.setProperty("class", "card-title")
        matrix_header.addWidget(lbl_matrix_title)
        matrix_header.addStretch()

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setProperty("class", "secondary")
        self.btn_clear.setFixedWidth(64)
        self.btn_clear.clicked.connect(self._clear_board)
        matrix_header.addWidget(self.btn_clear)
        left_layout.addLayout(matrix_header)

        # 4x4 Grid Input Matrix
        matrix_frame = QFrame()
        matrix_frame.setProperty("class", "sub-card")
        matrix_frame_layout = QVBoxLayout(matrix_frame)
        matrix_frame_layout.setContentsMargins(12, 12, 12, 12)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(8)
        self.tile_inputs: List[List[QLineEdit]] = []

        for r in range(4):
            row_inputs = []
            for c in range(4):
                edit = QLineEdit()
                edit.setMaxLength(1)
                edit.setFixedSize(62, 62)
                edit.setProperty("class", "board-tile")
                edit.setText(self.current_grid[r][c])
                edit.textChanged.connect(lambda text, row=r, col=c: self._on_tile_text_changed(row, col, text))
                self.grid_layout.addWidget(edit, r, c)
                row_inputs.append(edit)
            self.tile_inputs.append(row_inputs)

        matrix_frame_layout.addLayout(self.grid_layout)
        left_layout.addWidget(matrix_frame)

        # Path Visualizer Section
        path_header = QHBoxLayout()
        lbl_path_title = QLabel("SWIPE TRAJECTORY PREVIEW")
        lbl_path_title.setProperty("class", "card-title")
        path_header.addWidget(lbl_path_title)
        path_header.addStretch()
        left_layout.addLayout(path_header)

        # Mini Board Path Widget
        self.mini_board = MiniBoardWidget()
        self.mini_board.set_grid(self.current_grid)
        left_layout.addWidget(self.mini_board, alignment=Qt.AlignmentFlag.AlignCenter)

        # Active Word Detail Strip
        self.lbl_active_word_info = QLabel("Hover or click any discovered word to view swipe path.")
        self.lbl_active_word_info.setStyleSheet(f"font-size: 11px; color: {Theme.TEXT_MUTED};")
        self.lbl_active_word_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.lbl_active_word_info)

        left_layout.addStretch()
        body_layout.addWidget(left_card)

        # -------------------------------------------------------------
        # Right Workspace: Solution Drawer & Word List
        # -------------------------------------------------------------
        right_card = QFrame()
        right_card.setProperty("class", "card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 16, 18, 16)
        right_layout.setSpacing(12)

        # Search / Filter Bar
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.lbl_results_count = QLabel("DISCOVERED WORDS")
        self.lbl_results_count.setProperty("class", "card-title")
        search_row.addWidget(self.lbl_results_count)
        search_row.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter words (e.g. 'DREAM', 5L)...")
        self.search_box.setProperty("class", "search-input")
        self.search_box.setFixedWidth(240)
        self.search_box.textChanged.connect(self._filter_table)
        search_row.addWidget(self.search_box)

        right_layout.addLayout(search_row)

        # High-Density Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "WORD", "SCORE", "LEN", "SWIPE PATH"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_table_row_selected)
        right_layout.addWidget(self.table)

        # Bottom Quick Utility Bar
        bottom_util_row = QHBoxLayout()
        lbl_dict_info = QLabel(f"Dictionary: {len(self.dictionary.words):,} words")
        lbl_dict_info.setStyleSheet(f"font-size: 11px; color: {Theme.TEXT_MUTED};")

        self.btn_load_dict = QPushButton("📖 Load Dictionary")
        self.btn_load_dict.setProperty("class", "secondary")
        self.btn_load_dict.clicked.connect(self._load_custom_dict)

        bottom_util_row.addWidget(lbl_dict_info)
        bottom_util_row.addStretch()
        bottom_util_row.addWidget(self.btn_load_dict)
        right_layout.addLayout(bottom_util_row)

        body_layout.addWidget(right_card)
        root_layout.addLayout(body_layout)

        # =============================================================
        # 3. Live Footer Status Bar
        # =============================================================
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Keyboard Shortcuts
        self.shortcut_f8 = QShortcut(QKeySequence("F8"), self)
        self.shortcut_f8.activated.connect(self._snap_and_solve)

        self.shortcut_f9 = QShortcut(QKeySequence("F9"), self)
        self.shortcut_f9.activated.connect(self._toggle_sniper_overlay)

    # -------------------------------------------------------------------------
    # Window Geometry & Event Hooks
    # -------------------------------------------------------------------------

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self._save_main_geo()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._save_main_geo()

    def _save_main_geo(self) -> None:
        self.config.set_main_window_geometry(
            self.x(), self.y(), self.width(), self.height()
        )

    # -------------------------------------------------------------------------
    # Core Application Logic & Event Handlers
    # -------------------------------------------------------------------------

    def set_always_on_top(self, enable: bool) -> None:
        self.config.set_always_on_top(enable)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enable)
        self.show()
        self._update_status_display()

    def _on_roi_changed(self, x: int, y: int, w: int, h: int) -> None:
        self.worker.update_roi(x, y, w, h)
        self.config.set_sniper_overlay_geometry(x, y, w, h)
        self._update_status_display()

    def _on_speed_changed(self, val: int) -> None:
        sec = max(0.2, min(5.0, val / 10.0))
        self.lbl_speed_val.setText(f"{sec:.1f}s")
        self.worker.interval_sec = sec
        self.config.set_scan_interval(sec)

    def _toggle_sniper_overlay(self) -> None:
        is_visible = self.overlay.isVisible()
        new_state = not is_visible
        self.config.set_overlay_visible(new_state)

        if new_state:
            self.overlay.show()
            self.btn_toggle_sniper.setText("🎯 Sniper: Visible")
        else:
            self.overlay.hide()
            self.btn_toggle_sniper.setText("🎯 Sniper: Hidden")
        self._update_status_display()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.settings_applied.connect(self._on_settings_applied)
        dialog.exec()

    def _on_settings_applied(self) -> None:
        self.set_always_on_top(self.config.get_always_on_top())
        self.overlay.set_always_on_top(self.config.get_overlay_always_on_top())

        saved_roi = self.config.get_sniper_overlay_geometry()
        self.overlay.set_geometry_rect(
            saved_roi.get("x", 300),
            saved_roi.get("y", 200),
            saved_roi.get("width", 930),
            saved_roi.get("height", 930)
        )

        self.vision.set_tesseract_path(self.config.get_tesseract_path())
        self._update_status_display("Settings applied")

    def _snap_and_solve(self) -> None:
        self.badge_status.setText("● SCANNING")
        self.badge_status.setProperty("class", "status-pill-busy")
        self.badge_status.setStyle(self.badge_status.style())
        self._update_status_display("Capturing board...")
        self._active_scan_generation = self.worker.trigger_snap_and_solve()

    def _toggle_live_scan(self) -> None:
        if self.worker.is_live_mode:
            self._active_scan_generation = self.worker.set_live_mode(False)
            self.btn_live_scan.setText("▶ Live Scan")
            self.btn_live_scan.setProperty("class", "secondary")
            self.btn_live_scan.setStyle(self.btn_live_scan.style())
            self.badge_status.setText("● READY")
            self.badge_status.setProperty("class", "status-pill-ready")
            self.badge_status.setStyle(self.badge_status.style())
            self._update_status_display("Live scan paused")
        else:
            self._active_scan_generation = self.worker.set_live_mode(True)
            self.btn_live_scan.setText("⏹ Stop Live")
            self.btn_live_scan.setProperty("class", "danger")
            self.btn_live_scan.setStyle(self.btn_live_scan.style())
            self.badge_status.setText("● LIVE SCAN")
            self.badge_status.setProperty("class", "status-pill-busy")
            self.badge_status.setStyle(self.badge_status.style())
            self._update_status_display("Continuous scan active")

    def _on_scan_completed(self, grid: Grid, words_found: Dict[str, Path], elapsed_ms: float, scan_id: Optional[int] = None) -> None:
        if scan_id is not None and scan_id != self._active_scan_generation:
            # Stale scan result from previous canceled or cleared generation
            return

        self.last_latency_ms = elapsed_ms
        self.current_grid = grid

        for r in range(4):
            for c in range(4):
                self.tile_inputs[r][c].blockSignals(True)
                self.tile_inputs[r][c].setText(grid[r][c])
                self.tile_inputs[r][c].blockSignals(False)

        self.mini_board.set_grid(grid)
        self._populate_results(words_found)

        if not self.worker.is_live_mode:
            self.badge_status.setText("● READY")
            self.badge_status.setProperty("class", "status-pill-ready")
            self.badge_status.setStyle(self.badge_status.style())

        self._update_status_display(f"Found {len(words_found)} words in {elapsed_ms:.0f}ms")

    def _on_status_updated(self, msg: str) -> None:
        self._update_status_display(msg)

    def _update_status_display(self, extra_msg: Optional[str] = None) -> None:
        x, y, w, h = self.overlay.get_roi_rect()
        vis_text = "VISIBLE" if self.overlay.isVisible() else "HIDDEN"
        aot_text = "ON" if self.config.get_always_on_top() else "OFF"
        latency_str = f"{self.last_latency_ms:.0f}ms" if self.last_latency_ms > 0 else "Instant"

        status_text = f"Latency: {latency_str}  |  Sniper ROI: [{x}, {y}, {w}x{h}] ({vis_text})  |  Always on Top: {aot_text}"
        if extra_msg:
            status_text = f"{extra_msg}  •  {status_text}"
        self.status.showMessage(status_text)

    def _on_tile_text_changed(self, row: int, col: int, text: str) -> None:
        upper_char = text.strip().upper()
        char = upper_char[0] if upper_char else " "
        self.current_grid[row][col] = char
        self.tile_inputs[row][col].blockSignals(True)
        self.tile_inputs[row][col].setText(char)
        self.tile_inputs[row][col].blockSignals(False)

        # Auto-advance cursor to next tile
        if char != " ":
            next_col = (col + 1) % 4
            next_row = row + 1 if col == 3 else row
            if next_row < 4:
                self.tile_inputs[next_row][next_col].setFocus()
                self.tile_inputs[next_row][next_col].selectAll()

        self._recalculate_solutions(self.current_grid)

    def _recalculate_solutions(self, grid: Grid) -> None:
        has_letters = any(c.strip() for row in grid for c in row)
        if not has_letters:
            self.last_latency_ms = 0.0
            self.mini_board.set_grid(grid)
            self._populate_results({})
            return

        t0 = time.perf_counter()
        self.solver.set_grid(grid)
        words_found = self.solver.find_all_dictionary_words(self.dictionary.get_word_list())
        self.last_latency_ms = (time.perf_counter() - t0) * 1000.0

        self.mini_board.set_grid(grid)
        self._populate_results(words_found)

    def _populate_results(self, words_found: Dict[str, Path]) -> None:
        ranked = []
        for word, path in words_found.items():
            score = calculate_word_score(word)
            ranked.append((word, score, len(word), path))

        ranked.sort(key=lambda item: (-item[1], -item[2], item[0]))
        self.current_results = ranked
        self._filter_table()

    def _filter_table(self) -> None:
        query = self.search_box.text().strip().upper()

        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)

            filtered = []
            for word, score, length, path in self.current_results:
                if not query or query in word:
                    filtered.append((word, score, length, path))

            self.table.setRowCount(len(filtered))
            for row_idx, (word, score, length, path) in enumerate(filtered):
                # 0. Rank
                rank_item = QTableWidgetItem(f"{row_idx + 1}")
                rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                rank_item.setFont(QFont("Consolas", 10))
                rank_item.setForeground(QBrush(QColor(Theme.TEXT_MUTED)))

                # 1. Word
                word_item = QTableWidgetItem(word)
                word_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                word_item.setForeground(QBrush(QColor(Theme.TEXT_PRIMARY)))

                # 2. Score Badge
                score_item = QTableWidgetItem(f"+{score}")
                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                score_item.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
                score_item.setForeground(QBrush(QColor(Theme.EMERALD_PRIMARY if score >= 800 else Theme.AMBER_SCORE)))

                # 3. Length Tag
                len_item = QTableWidgetItem(f"{length}L")
                len_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                len_item.setFont(QFont("Consolas", 10))
                len_item.setForeground(QBrush(QColor(Theme.TEXT_SECONDARY)))

                # 4. Path Coordinates Summary
                coords = " -> ".join(f"({r},{c})" for r, c in path[:4])
                if len(path) > 4:
                    coords += f" ... ({len(path)} tiles)"
                trace_item = QTableWidgetItem(coords)
                trace_item.setFont(QFont("Consolas", 9))
                trace_item.setForeground(QBrush(QColor(Theme.TEXT_MUTED)))

                self.table.setItem(row_idx, 0, rank_item)
                self.table.setItem(row_idx, 1, word_item)
                self.table.setItem(row_idx, 2, score_item)
                self.table.setItem(row_idx, 3, len_item)
                self.table.setItem(row_idx, 4, trace_item)
        finally:
            self.table.blockSignals(False)

        self.lbl_results_count.setText(f"DISCOVERED WORDS ({len(filtered):,} / {len(self.current_results):,})")

    def _on_table_row_selected(self) -> None:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self.mini_board.clear_path()
            self.overlay.clear_active_path()
            self.lbl_active_word_info.setText("Hover or click any discovered word to view swipe path.")
            return

        row = self.table.currentRow()
        if row < 0 or row >= self.table.rowCount():
            self.mini_board.clear_path()
            self.overlay.clear_active_path()
            self.lbl_active_word_info.setText("Hover or click any discovered word to view swipe path.")
            return

        word_item = self.table.item(row, 1)
        if not word_item:
            return

        selected_word = word_item.text()
        for word, score, length, path in self.current_results:
            if word == selected_word:
                self.mini_board.set_active_path(word, path)
                self.overlay.set_active_path(word, path)
                trace_str = " → ".join(f"({r},{c})" for r, c in path)
                self.lbl_active_word_info.setText(f"Selected: {word} (+{score} pts)  |  Path: {trace_str}")
                break

    def _clear_board(self) -> None:
        # 1. Concurrency Safety: Pause live scan & cancel in-flight worker tasks
        if self.worker.is_live_mode:
            self.worker.set_live_mode(False)
            self.btn_live_scan.setText("▶ Live Scan")
            self.btn_live_scan.setProperty("class", "secondary")
            self.btn_live_scan.setStyle(self.btn_live_scan.style())

        self.worker.cancel_active_scan()
        self._active_scan_generation = self.worker._scan_generation

        # 2. Signal Flooding Prevention: Batch reset 4x4 input grid with signals suppressed
        for r in range(4):
            for c in range(4):
                self.current_grid[r][c] = " "
                tile = self.tile_inputs[r][c]
                tile.blockSignals(True)
                tile.setText("")
                tile.blockSignals(False)

        # 3. Clean Table & Selection Reset (block signals during row removal)
        self.table.blockSignals(True)
        try:
            self.table.clearSelection()
            self.table.setRowCount(0)
        finally:
            self.table.blockSignals(False)

        self.current_results = []

        # Reset search box filter with signals suppressed
        self.search_box.blockSignals(True)
        self.search_box.setText("")
        self.search_box.blockSignals(False)
        self.lbl_results_count.setText("DISCOVERED WORDS (0 / 0)")

        # 4. Canvas Visualizer & Overlay Clean Reset
        self.mini_board.set_grid(self.current_grid)
        self.mini_board.clear_path()
        self.overlay.clear_active_path()
        self.lbl_active_word_info.setText("Hover or click any discovered word to view swipe path.")

        # 5. Internal Metrics & Status Badge Reset
        self.last_latency_ms = 0.0
        self.badge_status.setText("● READY")
        self.badge_status.setProperty("class", "status-pill-ready")
        self.badge_status.setStyle(self.badge_status.style())
        self._update_status_display("Board cleared")

        # Focus back to top-left tile
        self.tile_inputs[0][0].setFocus()

    def _load_custom_dict(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Word List Text File",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            count = self.dictionary.load_from_file(file_path)
            QMessageBox.information(self, "Dictionary Loaded", f"Loaded {count:,} words from {file_path}")
            self._recalculate_solutions(self.current_grid)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not self.search_box.hasFocus():
            self._toggle_live_scan()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_main_geo()
        if self.worker.isRunning():
            self.worker.stop()
        self.overlay.close()
        super().closeEvent(event)


def launch_app() -> None:
    """Application runner."""
    app = QApplication(sys.argv)
    window = WordHuntApp()
    window.show()
    sys.exit(app.exec())
