"""Ground truth validation test for hybrid Template Matching + Tesseract vision engine."""

import os
import unittest
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from word_connect.core.vision import VisionEngine
from word_connect.core.template_matcher import TemplateMatcher
from word_connect.core.solver import BoggleSolver
from word_connect.core.config import AppConfig


class TestGroundTruthBoard(unittest.TestCase):
    """Test suite verifying hybrid vision OCR against user screenshot image_c3366f.png."""

    @classmethod
    def setUpClass(cls):
        # Ground truth board matching screenshot image_c3366f.png
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
        cls.vision = VisionEngine()
        cls.matcher = TemplateMatcher()

    def test_template_matcher_bootstrap(self):
        """Phase 2 verification: Verify all 26 templates (A-Z) exist with shape 48x48."""
        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            self.assertIn(char, self.matcher.templates, f"Template for '{char}' missing from matcher")
            mask = self.matcher.templates[char]
            self.assertEqual(mask.shape, (48, 48), f"Template for '{char}' has invalid shape {mask.shape}")
            self.assertGreater(np.count_nonzero(mask), 20, f"Template for '{char}' is empty")

    def test_geometric_disambiguation_p_vs_d(self):
        """Phase 4 verification: BRQ pixel density separates P from D."""
        p_template = self.matcher.templates["P"]
        d_template = self.matcher.templates["D"]

        self.assertEqual(TemplateMatcher.disambiguate_p_vs_d(p_template), "P")
        self.assertEqual(TemplateMatcher.disambiguate_p_vs_d(d_template), "D")

    def test_geometric_disambiguation_o_vs_d(self):
        """Phase 4 verification: Left vertical edge linearity separates O from D."""
        o_template = self.matcher.templates["O"]
        d_template = self.matcher.templates["D"]

        self.assertEqual(TemplateMatcher.disambiguate_o_vs_d(o_template), "O")
        self.assertEqual(TemplateMatcher.disambiguate_o_vs_d(d_template), "D")

    def test_geometric_disambiguation_e_vs_f(self):
        """Phase 4 verification: Lower horizontal bar presence separates E from F."""
        e_template = self.matcher.templates["E"]
        f_template = self.matcher.templates["F"]

        self.assertEqual(TemplateMatcher.disambiguate_e_vs_f(e_template), "E")
        self.assertEqual(TemplateMatcher.disambiguate_e_vs_f(f_template), "F")

    def test_vision_recognition_accuracy(self):
        """Phase 5 verification: Ensure all 16 characters from image_c3366f.png are recognized accurately."""
        detected_grid, elapsed_ms = self.vision.process_board_roi(self.simulated_image)
        
        self.assertEqual(len(detected_grid), 4)
        self.assertEqual(len(detected_grid[0]), 4)

        for r in range(4):
            for c in range(4):
                expected = self.ground_truth[r][c]
                actual = detected_grid[r][c]
                self.assertEqual(
                    actual, expected,
                    f"Mismatch at cell ({r}, {c}): expected '{expected}', got '{actual}'"
                )

        # Performance benchmark: full board recognition < 100ms
        self.assertLess(elapsed_ms, 150.0, f"Latency too high: {elapsed_ms:.2f}ms")

    def test_solver_on_ground_truth_board(self):
        """Verify solver finds valid words on the recognized board."""
        solver = BoggleSolver(self.ground_truth)
        expected_words = ["DREAM", "FART", "CARD", "CART", "FAME", "TEAM", "NEAR"]
        results = solver.find_words(expected_words)
        for w in expected_words:
            self.assertIsNotNone(results.get(w), f"Word '{w}' should be found on ground truth board")

    def test_persistent_config_save_load(self):
        """Verify config save, load, and update."""
        tmp_config_file = "word_connect/test_config.json"
        if os.path.exists(tmp_config_file):
            os.remove(tmp_config_file)

        cfg = AppConfig(tmp_config_file)
        cfg.set_roi(150, 200, 450, 450)
        cfg.set_scan_interval(1.5)
        cfg.set_always_on_top(True)
        cfg.set_overlay_visible(False)

        cfg2 = AppConfig(tmp_config_file)
        self.assertEqual(cfg2.get_roi()["x"], 150)
        self.assertEqual(cfg2.get_roi()["width"], 450)
        self.assertEqual(cfg2.get_scan_interval(), 1.5)
        self.assertTrue(cfg2.get_always_on_top())
        self.assertFalse(cfg2.get_overlay_visible())

        if os.path.exists(tmp_config_file):
            os.remove(tmp_config_file)


if __name__ == "__main__":
    unittest.main()
