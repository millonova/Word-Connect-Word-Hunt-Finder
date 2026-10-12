"""High-performance Screen Capture and Grid Vision Engine for Word Hunt.

Supports mss fast screen-grabbing, OpenCV tile preprocessing, and Tesseract OCR.
"""

import os
import shutil
import time
from typing import List, Tuple, Dict, Optional, Union
import numpy as np
import cv2
from PIL import Image

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    from PIL import ImageGrab
    IMAGEGRAB_AVAILABLE = True
except ImportError:
    IMAGEGRAB_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


def auto_detect_tesseract_path() -> Optional[str]:
    """Search common Windows and system locations for Tesseract binary."""
    # Check if already in PATH
    which_path = shutil.which("tesseract")
    if which_path:
        return which_path

    # Common Windows installation directories
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
    """Captures and processes screen ROI to extract 4x4 letter tiles."""

    def __init__(self, tesseract_cmd: Optional[str] = None) -> None:
        self.tesseract_path: Optional[str] = tesseract_cmd or auto_detect_tesseract_path()
        if self.tesseract_path and PYTESSERACT_AVAILABLE:
            try:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            except Exception:
                pass
        
        self.sct = mss.mss() if MSS_AVAILABLE else None

    def set_tesseract_path(self, path: str) -> bool:
        """Update and verify tesseract executable path."""
        if os.path.exists(path) and PYTESSERACT_AVAILABLE:
            self.tesseract_path = path
            pytesseract.pytesseract.tesseract_cmd = path
            return True
        return False

    def is_ocr_ready(self) -> bool:
        """Check if pytesseract and binary are available."""
        return PYTESSERACT_AVAILABLE and bool(self.tesseract_path) and os.path.exists(self.tesseract_path)

    def capture_roi(self, x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
        """Capture screen region of interest (ROI) and return BGR image."""
        if w <= 10 or h <= 10:
            return None

        # 1. Fast MSS screen capture
        if self.sct:
            try:
                monitor = {"top": int(y), "left": int(x), "width": int(w), "height": int(h)}
                sct_img = self.sct.grab(monitor)
                frame = np.array(sct_img)
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            except Exception:
                pass

        # 2. PIL ImageGrab fallback
        if IMAGEGRAB_AVAILABLE:
            try:
                bbox = (int(x), int(y), int(x + w), int(y + h))
                pil_img = ImageGrab.grab(bbox=bbox)
                frame = np.array(pil_img)
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            except Exception:
                pass

        return None

    def preprocess_tile(self, tile_crop: np.ndarray) -> np.ndarray:
        """Clean and binarize tile crop for high-accuracy single-letter OCR."""
        th, tw = tile_crop.shape[:2]
        
        # Center crop 65% to ignore tile borders and drop shadows
        margin_y = int(th * 0.16)
        margin_x = int(tw * 0.16)
        cropped = tile_crop[margin_y:th - margin_y, margin_x:tw - margin_x]
        if cropped.size == 0:
            cropped = tile_crop

        # Upscale for OCR clarity
        scaled = cv2.resize(cropped, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)

        # Contrast enhancement using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)

        # Otsu thresholding (invert so dark letters are black on white)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Morphological close to connect broken strokes if any
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Add generous white padding around letter
        padded = cv2.copyMakeBorder(cleaned, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=0)
        return padded

    def ocr_single_tile(self, tile_crop: np.ndarray) -> str:
        """Run single-character Tesseract OCR on a tile crop."""
        if not self.is_ocr_ready():
            return "?"

        try:
            processed = self.preprocess_tile(tile_crop)
            config = r"--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            text = pytesseract.image_to_string(processed, config=config).strip().upper()
            
            # Common OCR confusion fixes
            if text:
                char = text[0]
                if char == "0": char = "O"
                elif char == "1": char = "I"
                elif char == "5": char = "S"
                elif char == "8": char = "B"
                if char.isalpha():
                    return char
        except Exception:
            pass

        return "?"

    def process_board_roi(self, img: np.ndarray) -> Tuple[List[List[str]], float]:
        """Slice the captured ROI into a 4x4 grid and recognize all 16 letters.

        Returns:
            Tuple of (4x4 letter grid, elapsed processing time in ms).
        """
        start_time = time.perf_counter()
        h, w = img.shape[:2]
        cell_h = h / 4.0
        cell_w = w / 4.0

        grid: List[List[str]] = []
        for r in range(4):
            row_chars: List[str] = []
            for c in range(4):
                y1 = int(r * cell_h)
                y2 = int((r + 1) * cell_h)
                x1 = int(c * cell_w)
                x2 = int((c + 1) * cell_w)
                
                tile_crop = img[y1:y2, x1:x2]
                char = self.ocr_single_tile(tile_crop)
                row_chars.append(char)
            grid.append(row_chars)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return grid, elapsed_ms
