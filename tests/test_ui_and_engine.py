"""Exhaustive Automated End-to-End GUI & Engine Test Suite for Word Hunt Solver Pro.

Covers:
1. Interactive UI Event Simulation (QTest clicking, toggling, slider, hovering, resizing).
2. Thread Safety & Concurrency Stress Testing (rapid start/stop cycles, signal/slot safety, always-on-top flags).
3. Vision Pipeline & OCR Disambiguation (P vs D, O vs D, E vs F, zero-character black/white fallbacks).
4. Configuration Integrity & Geometry Persistence (corrupt JSON handling, window geometry auto-save/restore).
"""

import os
import sys
import json
import unittest
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

# Run in headless off-screen mode for headless CI / automated environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtWidgets import QApplication, QTableWidgetItem
from PyQt6.QtTest import QTest

from word_connect.core.solver import BoggleSolver, Path
from word_connect.core.dictionary import WordDictionary, calculate_word_score
from word_connect.core.vision import VisionEngine
from word_connect.core.template_matcher import TemplateMatcher
from word_connect.core.config import AppConfig
from word_connect.ui.main_window import WordHuntApp
from word_connect.ui.overlay import OverlayWindow
from word_connect.ui.settings_dialog import SettingsDialog
from word_connect.ui.mini_board import MiniBoardWidget


# Ensure a shared QApplication instance exists
app = QApplication.instance() or QApplication(sys.argv)


class TestInteractiveUIEvents(unittest.TestCase):
    """Step 1: Automated Interactive UI Event Simulation with QTest."""

    def setUp(self):
        self.window = WordHuntApp()
        self.window.show()

    def tearDown(self):
        if self.window.worker.isRunning():
            self.window.worker.stop()
        self.window.overlay.close()
        self.window.close()
        app.processEvents()

    def test_button_clicking_and_toggling(self):
        """Test clicking & rapid double-toggle of action controls."""
        # 1. Snap & Solve
        QTest.mouseClick(self.window.btn_snap_solve, Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertIn("SCANNING", self.window.badge_status.text())

        # 2. Live Scan Toggle
        # Start Live Scan
        QTest.mouseClick(self.window.btn_live_scan, Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertTrue(self.window.worker.is_live_mode)
        self.assertIn("Stop", self.window.btn_live_scan.text())

        # Stop Live Scan
        QTest.mouseClick(self.window.btn_live_scan, Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertFalse(self.window.worker.is_live_mode)
        self.assertIn("Live Scan", self.window.btn_live_scan.text())

        # Rapid multi-toggling (race condition resilience)
        for _ in range(6):
            QTest.mouseClick(self.window.btn_live_scan, Qt.MouseButton.LeftButton)
            app.processEvents()
        if self.window.worker.is_live_mode:
            QTest.mouseClick(self.window.btn_live_scan, Qt.MouseButton.LeftButton)
            app.processEvents()
        self.assertFalse(self.window.worker.is_live_mode)

        # 3. Sniper Overlay Toggle
        initial_visible = self.window.overlay.isVisible()
        QTest.mouseClick(self.window.btn_toggle_sniper, Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertNotEqual(self.window.overlay.isVisible(), initial_visible)

        # Toggle back
        QTest.mouseClick(self.window.btn_toggle_sniper, Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertEqual(self.window.overlay.isVisible(), initial_visible)

    def test_hover_and_path_preview_rendering(self):
        """Populate mock word results, select rows, and verify MiniBoardWidget redraws without QPainter errors."""
        mock_results = {
            "TEST": [(0, 0), (0, 1), (1, 1), (1, 2)],
            "ROBOT": [(2, 0), (2, 1), (3, 1), (3, 2), (2, 2)],
        }
        self.window._populate_results(mock_results)
        app.processEvents()

        self.assertGreaterEqual(self.window.table.rowCount(), 2)

        # Select first word ("ROBOT" or "TEST")
        self.window.table.selectRow(0)
        app.processEvents()

        active_path = self.window.mini_board.active_path
        self.assertIsNotNone(active_path)
        self.assertGreater(len(active_path), 0)

        # Force synchronous repaint of MiniBoardWidget to verify QPainter execution
        self.window.mini_board.repaint()

        # Select second word
        self.window.table.selectRow(1)
        app.processEvents()
        self.assertIsNotNone(self.window.mini_board.active_path)
        self.window.mini_board.repaint()

        # Clear selection
        self.window.table.clearSelection()
        app.processEvents()
        self.assertIsNone(self.window.mini_board.active_path)
        self.window.mini_board.repaint()

    def test_slider_speed_interaction(self):
        """Slide scan interval slider across values and verify worker interval dynamically updates."""
        slider = self.window.slider_speed
        
        # Set to min (0.2s)
        slider.setValue(2)
        app.processEvents()
        self.assertAlmostEqual(self.window.worker.interval_sec, 0.2, places=1)
        self.assertIn("0.2s", self.window.lbl_speed_val.text())

        # Set to middle (1.5s)
        slider.setValue(15)
        app.processEvents()
        self.assertAlmostEqual(self.window.worker.interval_sec, 1.5, places=1)
        self.assertIn("1.5s", self.window.lbl_speed_val.text())

        # Set to max (5.0s)
        slider.setValue(50)
        app.processEvents()
        self.assertAlmostEqual(self.window.worker.interval_sec, 5.0, places=1)
        self.assertIn("5.0s", self.window.lbl_speed_val.text())

    def test_dynamic_window_resizing(self):
        """Resize MainWindow across standard, ultrawide, and compact resolutions."""
        resolutions = [
            (600, 500),    # Compact
            (1080, 760),   # Standard Desktop
            (1920, 1080),  # Full HD Ultrawide
            (800, 1000),   # Tall Vertical
        ]
        for w, h in resolutions:
            self.window.resize(w, h)
            app.processEvents()

            # Confirm 4x4 grid tiles remain valid
            for r in range(4):
                for c in range(4):
                    tile = self.window.tile_inputs[r][c]
                    self.assertTrue(tile.isVisible())
                    self.assertGreater(tile.width(), 0)
                    self.assertGreater(tile.height(), 0)


class TestThreadSafetyAndConcurrency(unittest.TestCase):
    """Step 2: Concurrency, Thread Safety & Window Flags."""

    def setUp(self):
        self.window = WordHuntApp()
        self.window.show()

    def tearDown(self):
        if self.window.worker.isRunning():
            self.window.worker.stop()
        self.window.overlay.close()
        self.window.close()
        app.processEvents()

    def test_worker_thread_lifecycle_stress(self):
        """Repeatedly start and stop scanner thread to ensure no deadlocks or orphaned threads."""
        worker = self.window.worker

        for cycle in range(5):
            worker.set_live_mode(True)
            app.processEvents()
            self.assertTrue(worker.isRunning())

            worker.set_live_mode(False)
            worker.wait(500)
            app.processEvents()
            self.assertFalse(worker.isRunning())

    def test_always_on_top_flag_toggling(self):
        """Toggle Always-on-Top flag repeatedly without losing window state or input data."""
        initial_char = self.window.tile_inputs[0][0].text()

        for state in [True, False, True, False]:
            self.window.set_always_on_top(state)
            app.processEvents()

            # Verify flag is applied
            has_flag = bool(self.window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            self.assertEqual(has_flag, state)

            # Verify input matrix is not wiped
            self.assertEqual(self.window.tile_inputs[0][0].text(), initial_char)


class TestVisionPipelineAndOCRDisambiguation(unittest.TestCase):
    """Step 3: Vision Pipeline & OCR Disambiguation Verification."""

    @classmethod
    def setUpClass(cls):
        cls.vision = VisionEngine()
        cls.matcher = TemplateMatcher()

        # Build Ground Truth Board (CDFE / NEAM / ARTG / DCON)
        cls.board_size = 930
        cls.ground_truth = [
            ["C", "D", "F", "E"],
            ["N", "E", "A", "M"],
            ["A", "R", "T", "G"],
            ["D", "C", "O", "N"]
        ]

        board = np.full((cls.board_size, cls.board_size, 3), (45, 100, 50), dtype=np.uint8)
        font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
        font = ImageFont.truetype(font_path, 80) if os.path.exists(font_path) else None

        pil_img = Image.fromarray(cv2.cvtColor(board, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        cell_size = cls.board_size / 4.0

        for r in range(4):
            for c in range(4):
                cx1 = int(c * cell_size + 15)
                cy1 = int(r * cell_size + 15)
                cx2 = int((c + 1) * cell_size - 15)
                cy2 = int((r + 1) * cell_size - 15)
                draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=40, fill=(235, 245, 224))
                char = cls.ground_truth[r][c]
                if font is not None:
                    bb = draw.textbbox((0, 0), char, font=font)
                    tw = bb[2] - bb[0]
                    th = bb[3] - bb[1]
                    tx = (cx1 + cx2 - tw) // 2 - bb[0]
                    ty = (cy1 + cy2 - th) // 2 - bb[1]
                    draw.text((tx, ty), char, fill=(46, 56, 48), font=font)

        cls.simulated_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def test_p_vs_d_disambiguation(self):
        """Assert BRQ pixel density separates D from P."""
        # Check D in simulated board at (0, 1) and (3, 0)
        cell_size = self.board_size // 4
        d1_crop = self.simulated_image[0:cell_size, cell_size:2*cell_size]
        d2_crop = self.simulated_image[3*cell_size:4*cell_size, 0:cell_size]

        _, g1 = self.vision.preprocess_tile(d1_crop)
        _, g2 = self.vision.preprocess_tile(d2_crop)

        self.assertEqual(TemplateMatcher.disambiguate_p_vs_d(g1), "D")
        self.assertEqual(TemplateMatcher.disambiguate_p_vs_d(g2), "D")

        # Synthetic P check
        p_mask = self.matcher.templates["P"]
        self.assertEqual(TemplateMatcher.disambiguate_p_vs_d(p_mask), "P")

    def test_o_vs_d_disambiguation(self):
        """Assert column linearity separates O in (3, 2) from straight stem D."""
        cell_size = self.board_size // 4
        o_crop = self.simulated_image[3*cell_size:4*cell_size, 2*cell_size:3*cell_size]
        d_crop = self.simulated_image[0:cell_size, cell_size:2*cell_size]

        _, o_glyph = self.vision.preprocess_tile(o_crop)
        _, d_glyph = self.vision.preprocess_tile(d_crop)

        self.assertEqual(TemplateMatcher.disambiguate_o_vs_d(o_glyph), "O")
        self.assertEqual(TemplateMatcher.disambiguate_o_vs_d(d_glyph), "D")

    def test_e_vs_f_disambiguation(self):
        """Assert lower horizontal bar checks separate F in (0, 2) from E in (0, 3) and (1, 1)."""
        cell_size = self.board_size // 4
        f_crop = self.simulated_image[0:cell_size, 2*cell_size:3*cell_size]
        e1_crop = self.simulated_image[0:cell_size, 3*cell_size:4*cell_size]
        e2_crop = self.simulated_image[cell_size:2*cell_size, cell_size:2*cell_size]

        _, f_glyph = self.vision.preprocess_tile(f_crop)
        _, e1_glyph = self.vision.preprocess_tile(e1_crop)
        _, e2_glyph = self.vision.preprocess_tile(e2_crop)

        self.assertEqual(TemplateMatcher.disambiguate_e_vs_f(f_glyph), "F")
        self.assertEqual(TemplateMatcher.disambiguate_e_vs_f(e1_glyph), "E")
        self.assertEqual(TemplateMatcher.disambiguate_e_vs_f(e2_glyph), "E")

    def test_zero_character_fallback_on_blank_tiles(self):
        """Feed solid black and solid white blank tiles to ensure sanitized fallback without throwing unhandled exceptions."""
        black_tile = np.zeros((120, 120, 3), dtype=np.uint8)
        white_tile = np.full((120, 120, 3), 255, dtype=np.uint8)

        # Must not raise an exception
        res_black = self.vision.recognize_tile_letter(black_tile)
        res_white = self.vision.recognize_tile_letter(white_tile)

        # Must return a sanitized single character string
        self.assertIsInstance(res_black, str)
        self.assertEqual(len(res_black), 1)
        self.assertTrue(res_black.isupper() or res_black == "?")

        self.assertIsInstance(res_white, str)
        self.assertEqual(len(res_white), 1)
        self.assertTrue(res_white.isupper() or res_white == "?")


class TestConfigurationIntegrityAndPersistence(unittest.TestCase):
    """Step 4: Configuration Integrity & Geometry Persistence."""

    def setUp(self):
        self.test_cfg_path = os.path.join(os.path.dirname(__file__), "test_temp_config.json")
        if os.path.exists(self.test_cfg_path):
            os.remove(self.test_cfg_path)

    def tearDown(self):
        if os.path.exists(self.test_cfg_path):
            os.remove(self.test_cfg_path)

    def test_corrupt_config_loads_defaults(self):
        """Verify that writing invalid/corrupt data to config.json safely recovers with default values."""
        # 1. Empty file
        with open(self.test_cfg_path, "w", encoding="utf-8") as f:
            f.write("")

        cfg = AppConfig(self.test_cfg_path)
        self.assertEqual(cfg.get_scan_interval(), 1.0)
        self.assertIn("width", cfg.get_sniper_overlay_geometry())

        # 2. Corrupt syntax JSON
        with open(self.test_cfg_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json text ::: ")

        cfg2 = AppConfig(self.test_cfg_path)
        self.assertIsInstance(cfg2.get_always_on_top(), bool)
        self.assertGreaterEqual(cfg2.get_scan_interval(), 0.2)

    def test_geometry_save_and_restore(self):
        """Move and resize windows, trigger save, and verify accurate reload."""
        cfg = AppConfig(self.test_cfg_path)
        
        # Save custom window and sniper geometries
        cfg.set_main_window_geometry(140, 160, 1150, 820)
        cfg.set_sniper_overlay_geometry(250, 320, 850, 850)
        cfg.set_scan_interval(2.2)
        cfg.set_always_on_top(True)
        cfg.set_overlay_visible(False)

        # Instantiate second instance targeting same file
        cfg_loaded = AppConfig(self.test_cfg_path)

        main_geo = cfg_loaded.get_main_window_geometry()
        self.assertEqual(main_geo["x"], 140)
        self.assertEqual(main_geo["y"], 160)
        self.assertEqual(main_geo["width"], 1150)
        self.assertEqual(main_geo["height"], 820)

        sniper_geo = cfg_loaded.get_sniper_overlay_geometry()
        self.assertEqual(sniper_geo["x"], 250)
        self.assertEqual(sniper_geo["y"], 320)
        self.assertEqual(sniper_geo["width"], 850)
        self.assertEqual(sniper_geo["height"], 850)

        self.assertAlmostEqual(cfg_loaded.get_scan_interval(), 2.2, places=1)
        self.assertTrue(cfg_loaded.get_always_on_top())
        self.assertFalse(cfg_loaded.get_overlay_visible())


class TestClearBoardRobustness(unittest.TestCase):
    """Exhaustive tests for Clear Board routine under concurrency, load, and rapid UI events."""

    def setUp(self):
        self.window = WordHuntApp()
        self.window.show()
        app.processEvents()

    def tearDown(self):
        if self.window.worker.isRunning():
            self.window.worker.stop()
        self.window.overlay.close()
        self.window.close()
        app.processEvents()

    def test_clear_board_suppresses_signals_and_resets_cleanly(self):
        """Verify that batch-clearing 16 input tiles suppresses signal flooding."""
        # Populate board with mock values
        test_letters = [
            ["W", "O", "R", "D"],
            ["H", "U", "N", "T"],
            ["G", "A", "M", "E"],
            ["T", "E", "S", "T"]
        ]
        for r in range(4):
            for c in range(4):
                self.window.tile_inputs[r][c].setText(test_letters[r][c])
        app.processEvents()

        # Track number of times _recalculate_solutions is called during clear
        recalc_calls = []
        original_recalc = self.window._recalculate_solutions

        def instrumented_recalc(grid):
            recalc_calls.append(grid)
            return original_recalc(grid)

        self.window._recalculate_solutions = instrumented_recalc

        # Click Clear button
        QTest.mouseClick(self.window.btn_clear, Qt.MouseButton.LeftButton)
        app.processEvents()

        # Signal suppression must mean 0 cascading calls from tile_inputs during clear
        self.assertEqual(len(recalc_calls), 0, "Signals were not suppressed during cell clearing!")

        # Verify all 16 tiles are blank
        for r in range(4):
            for c in range(4):
                self.assertEqual(self.window.tile_inputs[r][c].text(), "")
                self.assertEqual(self.window.current_grid[r][c], " ")

        # Verify table and visualizer state
        self.assertEqual(self.window.table.rowCount(), 0)
        self.assertEqual(len(self.window.current_results), 0)
        self.assertIsNone(self.window.mini_board.active_path)
        self.assertIsNone(self.window.overlay._active_path)

    def test_clear_board_stops_live_scan_and_cancels_worker(self):
        """Verify that clicking Clear safely stops live scan and cancels active worker jobs."""
        # Start live scan
        QTest.mouseClick(self.window.btn_live_scan, Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertTrue(self.window.worker.is_live_mode)
        initial_generation = self.window.worker._scan_generation

        # Click Clear while live scan is running
        QTest.mouseClick(self.window.btn_clear, Qt.MouseButton.LeftButton)
        app.processEvents()

        # Live scan must be stopped and worker canceled
        self.assertFalse(self.window.worker.is_live_mode)
        self.assertIn("Live Scan", self.window.btn_live_scan.text())
        self.assertGreater(self.window.worker._scan_generation, initial_generation)
        self.assertEqual(self.window._active_scan_generation, self.window.worker._scan_generation)

    def test_clear_board_under_rapid_load_and_active_selection(self):
        """Stress test: populate results, select row, filter search, and spam Clear 20 times."""
        mock_results = {
            "WORDS": [(0, 0), (0, 1), (0, 2), (0, 3), (1, 3)],
            "HUNT": [(1, 0), (1, 1), (1, 2), (1, 3)],
            "GAME": [(2, 0), (2, 1), (2, 2), (2, 3)],
        }

        # Populate and select row
        self.window._populate_results(mock_results)
        app.processEvents()
        self.window.table.selectRow(0)
        app.processEvents()
        self.assertIsNotNone(self.window.mini_board.active_path)

        # Rapidly click Clear 20 times to simulate spam/race conditions
        for _ in range(20):
            QTest.mouseClick(self.window.btn_clear, Qt.MouseButton.LeftButton)
            app.processEvents()

        # Ensure complete stability
        self.assertEqual(self.window.table.rowCount(), 0)
        self.assertEqual(len(self.window.current_results), 0)
        self.assertIsNone(self.window.mini_board.active_path)
        self.assertIsNone(self.window.overlay._active_path)
        self.assertIn("READY", self.window.badge_status.text())

    def test_stale_scan_completed_emission_is_dropped_after_clear(self):
        """Ensure delayed scan_completed signals from earlier generations are ignored after Clear."""
        stale_gen = self.window._active_scan_generation
        
        # Click Clear to advance generation
        QTest.mouseClick(self.window.btn_clear, Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertGreater(self.window._active_scan_generation, stale_gen)

        # Simulate delayed scan_completed emission with stale generation id
        stale_grid = [["A"] * 4 for _ in range(4)]
        stale_words = {"AAAA": [(0, 0), (0, 1), (0, 2), (0, 3)]}
        self.window._on_scan_completed(stale_grid, stale_words, 25.0, scan_id=stale_gen)
        app.processEvents()

        # Stale results must be rejected, board stays cleared
        for r in range(4):
            for c in range(4):
                self.assertEqual(self.window.current_grid[r][c], " ")
                self.assertEqual(self.window.tile_inputs[r][c].text(), "")
        self.assertEqual(self.window.table.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
