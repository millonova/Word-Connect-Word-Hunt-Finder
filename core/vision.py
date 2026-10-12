"""High-accuracy Computer Vision & Tile OCR Engine for Word Hunt.

Hybrid Architecture:
- Primary Engine: Multi-scale Template Matching via OpenCV with geometric disambiguation.
- Secondary Fallback: Tesseract single-character OCR (--psm 10) when template confidence is low.
- Vision Preprocessing: 20% border inset crop, Otsu binarization, and contour-bound 48x48 normalization.
"""

import os
import shutil
import time
from typing import List, Tuple, Dict, Optional, Union
import numpy as np
import cv2

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    from PIL import ImageGrab, Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

from .template_matcher import TemplateMatcher
from .path_utils import get_resource_path


def auto_detect_tesseract_path() -> Optional[str]:
    """Search for bundled portable Tesseract or system locations."""
    # 1. Check bundled portable distribution (zero-dependency release)
    bundled = get_resource_path("assets/tesseract/tesseract.exe")
    if os.path.exists(bundled):
        tessdata = os.path.join(os.path.dirname(bundled), "tessdata")
        if os.path.exists(tessdata):
            os.environ["TESSDATA_PREFIX"] = os.path.dirname(bundled)
        return bundled

    # 2. System PATH
    which_path = shutil.which("tesseract")
    if which_path:
        return which_path

    # 3. Standard Windows installation paths
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), r"Tesseract-OCR\tesseract.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), r"Tesseract-OCR\tesseract.exe"),
    ]

    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


class VisionEngine:
    """Screen Grabber, Tile Preprocessor, and Hybrid Template Matcher + Tesseract Engine."""

    # Disambiguation mapping for common OCR digit/symbol confusions
    DISAMBIGUATION_MAP: Dict[str, str] = {
        "0": "O",
        "1": "I",
        "8": "B",
        "5": "S",
        "|": "I",
        "l": "I",
        "6": "G",
        "$": "S",
        "3": "E",
        "2": "Z",
        "9": "G",
    }

    def __init__(self, tesseract_cmd: Optional[str] = None) -> None:
        self.tesseract_path: Optional[str] = tesseract_cmd or auto_detect_tesseract_path()
        if self.tesseract_path and PYTESSERACT_AVAILABLE:
            try:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
                tessdata_dir = os.path.join(os.path.dirname(self.tesseract_path), "tessdata")
                if os.path.exists(tessdata_dir) and "TESSDATA_PREFIX" not in os.environ:
                    os.environ["TESSDATA_PREFIX"] = os.path.dirname(self.tesseract_path)
            except Exception:
                pass

        if MSS_AVAILABLE:
            try:
                mss_cls = getattr(mss, "MSS", mss.mss)
                self.sct = mss_cls()
            except Exception:
                self.sct = None
        else:
            self.sct = None

        self.matcher = TemplateMatcher()

    def is_ocr_ready(self) -> bool:
        """Check if Tesseract binary is available."""
        return PYTESSERACT_AVAILABLE and bool(self.tesseract_path) and os.path.exists(self.tesseract_path)

    def set_tesseract_path(self, path: str) -> bool:
        """Configure Tesseract executable path."""
        if os.path.exists(path) and PYTESSERACT_AVAILABLE:
            self.tesseract_path = path
            pytesseract.pytesseract.tesseract_cmd = path
            return True
        return False

    def capture_roi(self, x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
        """Capture screen ROI and return OpenCV BGR image."""
        if w <= 10 or h <= 10:
            return None

        # 1. Fast MSS screen capture (<10ms)
        if self.sct:
            try:
                monitor = {"top": int(y), "left": int(x), "width": int(w), "height": int(h)}
                sct_img = self.sct.grab(monitor)
                frame = np.array(sct_img)
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            except Exception:
                pass

        # 2. PIL ImageGrab fallback
        if PIL_AVAILABLE:
            try:
                bbox = (int(x), int(y), int(x + w), int(y + h))
                pil_img = ImageGrab.grab(bbox=bbox)
                frame = np.array(pil_img)
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            except Exception:
                pass

        return None

    def preprocess_tile(self, tile_cell: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Phase 3: Smart tile inset crop, Otsu binarization, and contour-bound normalization.

        Returns:
            Tuple of:
              - ocr_img: Clean Black text on White background with 25px border (for Tesseract).
              - glyph_binary: White text on Black background 48x48 normalized mask (for Template Matcher).
        """
        th, tw = tile_cell.shape[:2]

        # 1. Dynamic cell slicing with 20% border inset
        # Eliminates rounded tile corners, drop shadows, and dark green margins
        y1 = int(round(th * 0.20))
        y2 = int(round(th * 0.80))
        x1 = int(round(tw * 0.20))
        x2 = int(round(tw * 0.80))

        center_crop = tile_cell[y1:y2, x1:x2]
        if center_crop.size == 0:
            center_crop = tile_cell

        # 2. Convert to Grayscale & Upscale 2.5x with bicubic interpolation
        gray = cv2.cvtColor(center_crop, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, (0, 0), fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

        # 3. Gaussian Blur (3x3)
        blurred = cv2.GaussianBlur(scaled, (3, 3), 0)

        # 4. Otsu Binarization (dark game font -> 0 black, light cream tile -> 255 white)
        _, tesseract_binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 5. Inverse Binary (glyph = 255, background = 0)
        glyph_raw = 255 - tesseract_binary

        # 6. Extract contour bounding box and normalize to 48x48 canvas
        glyph_48 = self.matcher.normalize_glyph(glyph_raw)

        # 7. Add 25px solid white border for Tesseract single-char mode
        ocr_img = cv2.copyMakeBorder(
            tesseract_binary, 25, 25, 25, 25,
            cv2.BORDER_CONSTANT, value=255
        )

        return ocr_img, glyph_48

    def recognize_tile_letter(self, tile_cell: np.ndarray) -> str:
        """Execute hybrid letter recognition pipeline:

        1. Primary: Multi-scale Template Matching + Geometric Disambiguation.
        2. Confidence Evaluation: Check if match score >= 0.72.
        3. Fallback: Tesseract single-character mode (--psm 10) if confidence < 0.72.
        """
        ocr_img, glyph_48 = self.preprocess_tile(tile_cell)

        # 1. Primary Check: Multi-scale Template Matching with Geometric Disambiguation
        tmpl_char, confidence = self.matcher.match_glyph(glyph_48)

        # 2. Confidence Evaluation: threshold >= 0.72
        if confidence >= self.matcher.CONFIDENCE_THRESHOLD and tmpl_char.isalpha() and tmpl_char != "?":
            return tmpl_char

        # 3. Fallback Execution: Tesseract single-character mode (--psm 10)
        if self.is_ocr_ready():
            try:
                cfg_psm10 = r"--oem 3 --psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                text = pytesseract.image_to_string(ocr_img, config=cfg_psm10).strip()
                if text:
                    candidate = text[0].upper()
                    char = self.DISAMBIGUATION_MAP.get(candidate, candidate)
                    if char.isalpha() and char.isupper():
                        return char
            except Exception:
                pass

        # If Tesseract is unavailable or returned empty, return best template match
        clean_char = self.DISAMBIGUATION_MAP.get(tmpl_char.upper(), tmpl_char.upper())
        return clean_char if (clean_char.isalpha() and clean_char.isupper()) else "E"

    def process_board_roi(self, img: np.ndarray) -> Tuple[List[List[str]], float]:
        """Slice 4x4 ROI into 16 cells and recognize all 16 letters.

        Returns:
            Tuple of (4x4 letter grid, elapsed milliseconds).
        """
        start_time = time.perf_counter()
        h, w = img.shape[:2]
        cell_h = h / 4.0
        cell_w = w / 4.0

        grid: List[List[str]] = []
        for r in range(4):
            row_chars: List[str] = []
            for c in range(4):
                y1 = int(round(r * cell_h))
                y2 = int(round((r + 1) * cell_h))
                x1 = int(round(c * cell_w))
                x2 = int(round((c + 1) * cell_w))

                tile_cell = img[y1:y2, x1:x2]
                char = self.recognize_tile_letter(tile_cell)
                row_chars.append(char)
            grid.append(row_chars)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return grid, elapsed_ms
