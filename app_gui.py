"""Main PyQt6 Desktop Application GUI for Word Hunt / Boggle Solver.

Provides real-time OCR scanning, manual matrix editing, ranked word table,
mini-board path preview, and synchronization with the Sniper Overlay window.
"""

import sys
import os
import time
from typing import List, Dict, Optional, Tuple

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QRect
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSlider, QSpinBox, QFileDialog,
    QMessageBox, QFrame, QSplitter, QStatusBar, QCheckBox
)
from PyQt6.QtGui import (
    QFont, QColor, QBrush, QPen, QPainter, QKeyEvent, QIcon
)

from word_connect.solver import BoggleSolver, Path, Grid
from word_connect.dictionary import WordDictionary, calculate_word_score
from word_connect.vision_engine import VisionEngine
from word_connect.overlay_window import OverlayWindow


# Modern Design System Color Palette (Charcoal / Slate / Emerald / Mint)
STYLESHEET = """
QMainWindow {
    background-color: #0F172A;
}

QWidget {
    color: #F8FAFC;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}

QFrame.card {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 12px;
}

QLabel.title {
    font-size: 18px;
    font-weight: 700;
    color: #34D399;
}

QLabel.subtitle {
    font-size: 12px;
    color: #94A3B8;
}

QLabel.section-header {
    font-size: 14px;
    font-weight: 600;
    color: #E2E8F0;
    letter-spacing: 0.5px;
}

QPushButton.primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px 16px;
    border: none;
}
QPushButton.primary:hover {
    background: #34D399;
}
QPushButton.primary:pressed {
    background: #047857;
}

QPushButton.secondary {
    background-color: #334155;
    color: #E2E8F0;
    font-weight: 600;
    font-size: 12px;
    border-radius: 8px;
    padding: 6px 12px;
    border: 1px solid #475569;
}
QPushButton.secondary:hover {
    background-color: #475569;
}

QPushButton.danger {
    background-color: #EF4444;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px 16px;
    border: none;
}
QPushButton.danger:hover {
    background-color: #F87171;
}

QLineEdit.tile-edit {
    background-color: #0F172A;
    border: 2px solid #334155;
    border-radius: 8px;
    color: #34D399;
    font-size: 22px;
    font-weight: 800;
    qproperty-alignment: AlignCenter;
}
QLineEdit.tile-edit:focus {
    border: 2px solid #10B981;
    background-color: #1E293B;
}

QLineEdit.search-box {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #F8FAFC;
    padding: 6px 10px;
    font-size: 13px;
}
QLineEdit.search-box:focus {
    border: 1px solid #10B981;
}

QTableWidget {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #1E293B;
    selection-background-color: #065F46;
    selection-color: #FFFFFF;
}
QTableWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid #334155;
    padding: 6px;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #334155;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #10B981;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #F8FAFC;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QStatusBar {
    background-color: #0B1120;
    color: #94A3B8;
    border-top: 1px solid #1E293B;
}
"""


class MiniBoardWidget(QWidget):
    """Custom canvas showing 4x4 letter tiles and path line animations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.grid: Grid = [[" "]*4 for _ in range(4)]
        self.active_path: Optional[Path] = None

    def set_grid(self, grid: Grid) -> None:
        self.grid = grid
        self.update()

    def set_active_path(self, path: Optional[Path]) -> None:
        self.active_path = path
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        offset_x = (w - side) // 2
        offset_y = (h - side) // 2

        cell_size = side / 4.0
        margin = 4

        path_set = set(self.active_path) if self.active_path else set()
        step_order = {pt: idx + 1 for idx, pt in enumerate(self.active_path)} if self.active_path else {}

        # 1. Draw 16 Tiles
        for r in range(4):
            for c in range(4):
                tx = offset_x + c * cell_size + margin
                ty = offset_y + r * cell_size + margin
                tw = cell_size - margin * 2
                th = cell_size - margin * 2

                # Tile background
                if (r, c) in path_set:
                    painter.setBrush(QBrush(QColor(16, 185, 129, 210)))
                    painter.setPen(QPen(QColor(52, 211, 153), 2))
                else:
                    painter.setBrush(QBrush(QColor(30, 41, 59)))
                    painter.setPen(QPen(QColor(51, 65, 85), 1))

                painter.drawRoundedRect(int(tx), int(ty), int(tw), int(th), 8, 8)

                # Letter text
                char = self.grid[r][c] if r < len(self.grid) and c < len(self.grid[r]) else " "
                painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
                painter.setPen(QColor(255, 255, 255) if (r, c) in path_set else QColor(226, 232, 240))
                painter.drawText(QRect(int(tx), int(ty), int(tw), int(th)), Qt.AlignmentFlag.AlignCenter, char)

                # Step badge
                if (r, c) in step_order:
                    step_num = str(step_order[(r, c)])
                    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
                    painter.setPen(QPen(QColor(255, 255, 255), 1))
                    badge_size = 16
                    bx = int(tx + tw - badge_size)
                    by = int(ty)
                    painter.drawEllipse(bx, by, badge_size, badge_size)
                    painter.drawText(QRect(bx, by, badge_size, badge_size), Qt.AlignmentFlag.AlignCenter, step_num)

        # 2. Draw connecting arrows/lines for path
        if self.active_path and len(self.active_path) > 1:
            pts = []
            for r, c in self.active_path:
                cx = int(offset_x + (c + 0.5) * cell_size)
                cy = int(offset_y + (r + 0.5) * cell_size)
                pts.append((cx, cy))

            line_pen = QPen(QColor(255, 255, 255, 220), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(line_pen)
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])


class ScanWorker(QThread):
    """Background thread continuously grabbing screen ROI and running OCR."""

    scan_completed = pyqtSignal(list, dict, float)  # grid, words_found, elapsed_ms
    status_updated = pyqtSignal(str)

    def __init__(self, vision_engine: VisionEngine, dictionary: WordDictionary) -> None:
        super().__init__()
        self.vision = vision_engine
        self.dictionary = dictionary
        self.running = False
        self.single_shot_requested = False
        self.roi: Tuple[int, int, int, int] = (100, 100, 380, 380)
        self.interval_sec = 1.0
        self.last_grid: Optional[Grid] = None

    def update_roi(self, x: int, y: int, w: int, h: int) -> None:
        self.roi = (x, y, w, h)

    def trigger_single_scan(self) -> None:
        self.single_shot_requested = True

    def stop(self) -> None:
        self.running = False
        self.wait(1000)

    def run(self) -> None:
        self.running = True
        solver = BoggleSolver()

        while self.running:
            should_scan = self.running and (self.single_shot_requested or self.interval_sec > 0)
            if should_scan:
                self.single_shot_requested = False
                x, y, w, h = self.roi

                # 1. Grab Frame
                frame = self.vision.capture_roi(x, y, w, h)
                if frame is not None and frame.size > 0:
                    # 2. OCR Grid
                    grid, ocr_time = self.vision.process_board_roi(frame)
                    
                    # 3. Solve if grid contains valid chars
                    has_letters = any(c != "?" and c.isalpha() for row in grid for c in row)
                    if has_letters:
                        solver.set_grid(grid)
                        all_words = solver.find_all_dictionary_words(self.dictionary.get_word_list())
                        self.scan_completed.emit(grid, all_words, ocr_time)
                        self.status_updated.emit(f"OCR: {ocr_time:.0f}ms | Found {len(all_words)} words")
                    else:
                        self.status_updated.emit("No letters detected in ROI.")
                else:
                    self.status_updated.emit("Failed to capture screen ROI.")

            # Sleep interval
            time.sleep(max(0.1, self.interval_sec))


class WordHuntApp(QMainWindow):
    """Main Application Window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Word Hunt / Boggle Sniper Solver Pro")
        self.resize(1050, 720)
        self.setStyleSheet(STYLESHEET)

        # Initialize engines
        self.dictionary = WordDictionary()
        self.vision = VisionEngine()
        self.solver = BoggleSolver()

        # Word results cache: List of tuples (word, score, length, path)
        self.current_results: List[Tuple[str, int, int, Path]] = []
        self.current_grid: Grid = [
            ["W", "I", "T", "K"],
            ["A", "N", "E", "S"],
            ["R", "S", "O", "A"],
            ["I", "E", "P", "A"]
        ]

        # Sniper Overlay Window
        self.overlay = OverlayWindow()
        self.overlay.roi_changed.connect(self._on_roi_changed)
        self.overlay.show()

        # Worker Thread
        self.worker = ScanWorker(self.vision, self.dictionary)
        self.worker.scan_completed.connect(self._on_scan_completed)
        self.worker.status_updated.connect(self._on_status_updated)
        self.worker.update_roi(*self.overlay.get_roi_rect())

        self._build_ui()
        self._recalculate_solutions(self.current_grid)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------
        # Left Panel: 4x4 Grid Matrix + Mini Preview + Controls
        # -------------------------------------------------------------
        left_panel = QFrame()
        left_panel.setProperty("class", "card")
        left_panel.setFixedWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)

        # Header Title
        title_box = QVBoxLayout()
        lbl_title = QLabel("WORD HUNT SNIPER")
        lbl_title.setProperty("class", "title")
        lbl_sub = QLabel(f"Dictionary: {len(self.dictionary.words):,} words loaded")
        lbl_sub.setProperty("class", "subtitle")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        left_layout.addLayout(title_box)

        # Scanning Controls Box
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet("background-color: #0F172A; border-radius: 8px; padding: 8px;")
        ctrl_layout = QVBoxLayout(ctrl_card)

        btn_row = QHBoxLayout()
        self.btn_toggle_scan = QPushButton("Start Scanner")
        self.btn_toggle_scan.setProperty("class", "primary")
        self.btn_toggle_scan.clicked.connect(self._toggle_scanner)

        self.btn_single_scan = QPushButton("Scan Now (F8)")
        self.btn_single_scan.setProperty("class", "secondary")
        self.btn_single_scan.clicked.connect(self._single_scan)

        btn_row.addWidget(self.btn_toggle_scan)
        btn_row.addWidget(self.btn_single_scan)
        ctrl_layout.addLayout(btn_row)

        # Interval slider
        slider_row = QHBoxLayout()
        lbl_speed = QLabel("Interval:")
        lbl_speed.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(2, 30)  # 0.2s to 3.0s
        self.slider_speed.setValue(10)      # 1.0s
        self.lbl_speed_val = QLabel("1.0s")
        self.lbl_speed_val.setStyleSheet("font-size: 11px; font-weight: bold; color: #34D399;")
        self.slider_speed.valueChanged.connect(self._on_speed_changed)

        slider_row.addWidget(lbl_speed)
        slider_row.addWidget(self.slider_speed)
        slider_row.addWidget(self.lbl_speed_val)
        ctrl_layout.addLayout(slider_row)

        # Overlay Visibility Toggle
        self.chk_overlay = QCheckBox("Show Sniper Overlay Window")
        self.chk_overlay.setChecked(True)
        self.chk_overlay.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        self.chk_overlay.toggled.connect(self._toggle_overlay_visibility)
        ctrl_layout.addWidget(self.chk_overlay)

        left_layout.addWidget(ctrl_card)

        # 4x4 Editable Letter Grid
        grid_lbl = QLabel("4x4 BOARD MATRIX (EDITABLE)")
        grid_lbl.setProperty("class", "section-header")
        left_layout.addWidget(grid_lbl)

        matrix_frame = QWidget()
        self.grid_layout = QGridLayout(matrix_frame)
        self.grid_layout.setSpacing(6)
        self.tile_inputs: List[List[QLineEdit]] = []

        for r in range(4):
            row_inputs = []
            for c in range(4):
                edit = QLineEdit()
                edit.setMaxLength(1)
                edit.setFixedSize(54, 54)
                edit.setProperty("class", "tile-edit")
                edit.setText(self.current_grid[r][c])
                edit.textChanged.connect(lambda text, row=r, col=c: self._on_tile_text_changed(row, col, text))
                self.grid_layout.addWidget(edit, r, c)
                row_inputs.append(edit)
            self.tile_inputs.append(row_inputs)
        left_layout.addWidget(matrix_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Mini Board Path Preview
        preview_lbl = QLabel("LIVE PATH STROKE PREVIEW")
        preview_lbl.setProperty("class", "section-header")
        left_layout.addWidget(preview_lbl)

        self.mini_board = MiniBoardWidget()
        self.mini_board.set_grid(self.current_grid)
        left_layout.addWidget(self.mini_board, alignment=Qt.AlignmentFlag.AlignCenter)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # -------------------------------------------------------------
        # Right Panel: Ranked Word Results Table & Filter
        # -------------------------------------------------------------
        right_panel = QFrame()
        right_panel.setProperty("class", "card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(12)

        # Table Header & Search Row
        top_bar = QHBoxLayout()
        self.lbl_table_header = QLabel("FOUND WORDS (RANKED BY SCORE)")
        self.lbl_table_header.setProperty("class", "section-header")
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter words (e.g. 'TEA', min 4 chars)...")
        self.search_box.setProperty("class", "search-box")
        self.search_box.textChanged.connect(self._filter_table)

        top_bar.addWidget(self.lbl_table_header)
        top_bar.addStretch()
        top_bar.addWidget(self.search_box)
        right_layout.addLayout(top_bar)

        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "WORD", "SCORE", "LENGTH", "PATH TRACE"])
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

        # Bottom Bar: Tesseract Configuration button & Clear
        btn_bar = QHBoxLayout()
        self.btn_set_tess = QPushButton("Set Tesseract Path")
        self.btn_set_tess.setProperty("class", "secondary")
        self.btn_set_tess.clicked.connect(self._pick_tesseract_path)

        self.btn_load_dict = QPushButton("Load Custom Dictionary")
        self.btn_load_dict.setProperty("class", "secondary")
        self.btn_load_dict.clicked.connect(self._load_custom_dict)

        self.btn_clear = QPushButton("Clear Board")
        self.btn_clear.setProperty("class", "secondary")
        self.btn_clear.clicked.connect(self._clear_board)

        btn_bar.addWidget(self.btn_set_tess)
        btn_bar.addWidget(self.btn_load_dict)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_clear)
        right_layout.addLayout(btn_bar)

        main_layout.addWidget(right_panel)

        # Status Bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready. Position the Sniper Overlay window over your game board.")

    # -------------------------------------------------------------------------
    # Event Handlers & Slots
    # -------------------------------------------------------------------------

    def _on_roi_changed(self, x: int, y: int, w: int, h: int) -> None:
        self.worker.update_roi(x, y, w, h)

    def _toggle_overlay_visibility(self, visible: bool) -> None:
        if visible:
            self.overlay.show()
        else:
            self.overlay.hide()

    def _on_speed_changed(self, val: int) -> None:
        sec = val / 10.0
        self.lbl_speed_val.setText(f"{sec:.1f}s")
        self.worker.interval_sec = sec

    def _toggle_scanner(self) -> None:
        if self.worker.isRunning():
            self.worker.stop()
            self.btn_toggle_scan.setText("▶ Start Scanner")
            self.btn_toggle_scan.setProperty("class", "primary")
            self.btn_toggle_scan.setStyle(self.btn_toggle_scan.style())
            self.status.showMessage("Scanner paused.")
        else:
            self.worker.start()
            self.btn_toggle_scan.setText("⏹ Stop Scanner")
            self.btn_toggle_scan.setProperty("class", "danger")
            self.btn_toggle_scan.setStyle(self.btn_toggle_scan.style())
            self.status.showMessage("Scanner running in background...")

    def _single_scan(self) -> None:
        if not self.worker.isRunning():
            self.worker.start()
        self.worker.trigger_single_scan()
        self.status.showMessage("Scanning single frame...")

    def _on_scan_completed(self, grid: Grid, words_found: Dict[str, Path], elapsed_ms: float) -> None:
        self.current_grid = grid
        # Update 4x4 matrix inputs without triggering recursion
        for r in range(4):
            for c in range(4):
                self.tile_inputs[r][c].blockSignals(True)
                self.tile_inputs[r][c].setText(grid[r][c])
                self.tile_inputs[r][c].blockSignals(False)

        self.mini_board.set_grid(grid)
        self._populate_results(words_found)

    def _on_status_updated(self, msg: str) -> None:
        self.status.showMessage(msg)

    def _on_tile_text_changed(self, row: int, col: int, text: str) -> None:
        upper_char = text.strip().upper()
        char = upper_char[0] if upper_char else " "
        self.current_grid[row][col] = char
        self.tile_inputs[row][col].blockSignals(True)
        self.tile_inputs[row][col].setText(char)
        self.tile_inputs[row][col].blockSignals(False)

        # Auto advance focus to next tile
        if char != " ":
            next_col = (col + 1) % 4
            next_row = row + 1 if col == 3 else row
            if next_row < 4:
                self.tile_inputs[next_row][next_col].setFocus()
                self.tile_inputs[next_row][next_col].selectAll()

        self._recalculate_solutions(self.current_grid)

    def _recalculate_solutions(self, grid: Grid) -> None:
        """Solve board using BoggleSolver + Trie."""
        self.solver.set_grid(grid)
        words_found = self.solver.find_all_dictionary_words(self.dictionary.get_word_list())
        self.mini_board.set_grid(grid)
        self._populate_results(words_found)

    def _populate_results(self, words_found: Dict[str, Path]) -> None:
        # Build ranked word tuples
        ranked = []
        for word, path in words_found.items():
            score = calculate_word_score(word)
            ranked.append((word, score, len(word), path))

        # Sort descending by score, then length, then alphabetical
        ranked.sort(key=lambda item: (-item[1], -item[2], item[0]))
        self.current_results = ranked
        self._filter_table()

    def _filter_table(self) -> None:
        query = self.search_box.text().strip().upper()
        self.table.setRowCount(0)

        filtered = []
        for word, score, length, path in self.current_results:
            if not query or query in word:
                filtered.append((word, score, length, path))

        self.table.setRowCount(len(filtered))
        for row_idx, (word, score, length, path) in enumerate(filtered):
            # Rank
            rank_item = QTableWidgetItem(f"{row_idx + 1}")
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Word
            word_item = QTableWidgetItem(word)
            word_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            word_item.setForeground(QBrush(QColor(52, 211, 153)))

            # Score badge
            score_item = QTableWidgetItem(f"+{score}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            score_item.setForeground(QBrush(QColor(251, 191, 36)))

            # Length
            len_item = QTableWidgetItem(f"{length}L")
            len_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Path Trace Summary (e.g. (0,0) -> (1,1) ...)
            coords_summary = " -> ".join(f"({r},{c})" for r, c in path[:4])
            if len(path) > 4:
                coords_summary += "..."
            trace_item = QTableWidgetItem(coords_summary)

            self.table.setItem(row_idx, 0, rank_item)
            self.table.setItem(row_idx, 1, word_item)
            self.table.setItem(row_idx, 2, score_item)
            self.table.setItem(row_idx, 3, len_item)
            self.table.setItem(row_idx, 4, trace_item)

        self.lbl_table_header.setText(f"FOUND WORDS ({len(filtered)} / {len(self.current_results)})")

    def _on_table_row_selected(self) -> None:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self.mini_board.set_active_path(None)
            self.overlay.clear_active_path()
            return

        row = self.table.currentRow()
        word_item = self.table.item(row, 1)
        if not word_item:
            return

        selected_word = word_item.text()
        for word, score, length, path in self.current_results:
            if word == selected_word:
                self.mini_board.set_active_path(path)
                self.overlay.set_active_path(word, path)
                break

    def _clear_board(self) -> None:
        for r in range(4):
            for c in range(4):
                self.tile_inputs[r][c].setText("")
                self.current_grid[r][c] = " "
        self._recalculate_solutions(self.current_grid)

    def _pick_tesseract_path(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Tesseract Executable",
            r"C:\Program Files\Tesseract-OCR",
            "Executable (*.exe);;All Files (*)"
        )
        if file_path:
            if self.vision.set_tesseract_path(file_path):
                QMessageBox.information(self, "Tesseract Config", f"Tesseract path updated:\n{file_path}")
            else:
                QMessageBox.warning(self, "Error", "Invalid Tesseract executable.")

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
        if event.key() == Qt.Key.Key_F8:
            self._single_scan()
        elif event.key() == Qt.Key.Key_Space and not self.search_box.hasFocus():
            self._toggle_scanner()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        if self.worker.isRunning():
            self.worker.stop()
        self.overlay.close()
        event.accept()


def launch_app() -> None:
    """Launch the PyQt6 application."""
    app = QApplication(sys.argv)
    window = WordHuntApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_app()
