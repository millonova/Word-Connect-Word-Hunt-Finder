"""Image processing and OCR module for Word Connect boards.

Uses OpenCV for grid/tile detection and Tesseract/pytesseract for reading
tile letters and target word lists from game screenshots.
"""

import os
from typing import List, Tuple, Dict, Optional, Union, TypedDict


class TileData(TypedDict):
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
import numpy as np
import cv2

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


class BoardDetector:
    """Detects 4x4 letter tiles and words from game screenshots."""

    def __init__(self, tesseract_cmd: Optional[str] = None) -> None:
        r"""Initialize the BoardDetector.

        Args:
            tesseract_cmd: Optional path to the tesseract executable
                           (e.g., r"C:\Program Files\Tesseract-OCR\tesseract.exe").
        """
        if tesseract_cmd and PYTESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    @staticmethod
    def load_image(image_input: Union[str, np.ndarray]) -> np.ndarray:
        """Load an image from a filepath or return the array if already loaded."""
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found at path: {image_input}")
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"Could not decode image at: {image_input}")
            return img
        elif isinstance(image_input, np.ndarray):
            return image_input.copy()
        else:
            raise TypeError("Expected image path or numpy ndarray.")

    def find_board_region(self, img: np.ndarray) -> Tuple[int, int, int, int]:
        """Find the bounding box (x, y, w, h) of the dark green 4x4 game board."""
        h, w = img.shape[:2]
        # In typical screenshots, the board is on the right 60-70% of the image
        # Let's search for large dark green contours or use proportional slicing
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Dark green board mask (HSV range for dark forest green)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 180])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_box = None
        max_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > (h * w * 0.15):  # Must be substantial
                bx, by, bw, bh = cv2.boundingRect(cnt)
                aspect = bw / float(bh)
                # Board is roughly square (0.8 - 1.2)
                if 0.75 <= aspect <= 1.25 and area > max_area:
                    max_area = area
                    best_box = (bx, by, bw, bh)

        if best_box is not None:
            return best_box

        # Fallback to estimated right-side area
        bx = int(w * 0.31)
        by = int(h * 0.04)
        bw = int(w * 0.66)
        bh = int(h * 0.92)
        return (bx, by, bw, bh)

    def detect_tiles(self, img: np.ndarray) -> List[List[TileData]]:
        """Detect the 4x4 grid tiles and compute their center points and bounding boxes.

        Returns:
            4x4 matrix of TileData containing:
                - 'center': (x, y) pixel coordinates of the tile center
                - 'bbox': (x, y, w, h) bounding box of the tile
        """
        bx, by, bw, bh = self.find_board_region(img)
        board_roi = img[by:by+bh, bx:bx+bw]

        # Light tile detection inside the board ROI (ivory/light green tiles)
        hsv_roi = cv2.cvtColor(board_roi, cv2.COLOR_BGR2HSV)
        # Ivory and light green tiles have high Value / brightness
        gray_roi = cv2.cvtColor(board_roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray_roi, 160, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        tile_candidates = []
        roi_area = bw * bh
        min_tile_area = roi_area * 0.01
        max_tile_area = roi_area * 0.08

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_tile_area <= area <= max_tile_area:
                tx, ty, tw, th = cv2.boundingRect(cnt)
                aspect = tw / float(th)
                if 0.75 <= aspect <= 1.3:
                    tile_candidates.append((tx + bx, ty + by, tw, th))

        # If exactly or roughly 16 tiles detected, sort them into 4x4 grid
        if len(tile_candidates) >= 16:
            # Sort by y first, group into rows of 4, then sort each row by x
            tile_candidates.sort(key=lambda b: b[1])
            rows = []
            for i in range(4):
                row_candidates = tile_candidates[i*4 : (i+1)*4]
                row_candidates.sort(key=lambda b: b[0])
                rows.append(row_candidates)
            
            grid_tiles: List[List[TileData]] = []
            for r in range(4):
                grid_row: List[TileData] = []
                for c in range(4):
                    tx, ty, tw, th = rows[r][c]
                    cx = tx + tw // 2
                    cy = ty + th // 2
                    grid_row.append({
                        "center": (cx, cy),
                        "bbox": (tx, ty, tw, th)
                    })
                grid_tiles.append(grid_row)
            return grid_tiles

        # Geometric Grid Division Fallback (super robust for any resolution)
        grid_tiles = []
        cell_w = bw / 4.0
        cell_h = bh / 4.0
        # Tile margin / padding inside cell
        margin_x = int(cell_w * 0.12)
        margin_y = int(cell_h * 0.12)

        for r in range(4):
            grid_row = []
            for c in range(4):
                tx = int(bx + c * cell_w + margin_x)
                ty = int(by + r * cell_h + margin_y)
                tw = int(cell_w - 2 * margin_x)
                th = int(cell_h - 2 * margin_y)
                cx = tx + tw // 2
                cy = ty + th // 2
                grid_row.append({
                    "center": (cx, cy),
                    "bbox": (tx, ty, tw, th)
                })
            grid_tiles.append(grid_row)

        return grid_tiles

    def extract_letter_from_tile(self, tile_img: np.ndarray) -> str:
        """Preprocess tile crop and run single-character OCR."""
        if not PYTESSERACT_AVAILABLE or tile_img is None or tile_img.size == 0:
            return "?"

        # Center crop to isolate the letter glyph
        th, tw = tile_img.shape[:2]
        if th < 10 or tw < 10:
            return "?"

        crop_margin = int(min(th, tw) * 0.18)
        char_crop = tile_img[crop_margin:th-crop_margin, crop_margin:tw-crop_margin]
        if char_crop.size == 0:
            char_crop = tile_img

        # Grayscale & threshold
        gray = cv2.cvtColor(char_crop, cv2.COLOR_BGR2GRAY)
        # Upscale for high OCR accuracy
        gray = cv2.resize(gray, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        
        # Letters are dark grey/green on ivory background
        # Adaptive or Otsu thresholding
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Pad with white border
        padded = cv2.copyMakeBorder(binary, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=0)

        # OCR configuration: single character, uppercase only
        custom_config = r"--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        try:
            text = pytesseract.image_to_string(padded, config=custom_config).strip().upper()
            if text and text[0].isalpha():
                return text[0]
        except Exception:
            pass

        return "?"

    def recognize_grid(self, img_input: Union[str, np.ndarray]) -> Tuple[List[List[str]], List[List[TileData]]]:
        """Detect the 4x4 grid and recognize all 16 letters.

        Returns:
            Tuple of (4x4 letter grid, 4x4 tile metadata with centers and bboxes).
        """
        img = self.load_image(img_input)
        img_h, img_w = img.shape[:2]
        tile_grid = self.detect_tiles(img)
        letter_grid: List[List[str]] = []

        for r in range(4):
            row_letters: List[str] = []
            for c in range(4):
                bbox = tile_grid[r][c]["bbox"]
                tx, ty, tw, th = bbox
                
                # Clamp coordinates to image boundaries
                x1 = max(0, min(tx, img_w - 1))
                y1 = max(0, min(ty, img_h - 1))
                x2 = max(x1 + 1, min(tx + tw, img_w))
                y2 = max(y1 + 1, min(ty + th, img_h))

                tile_crop = img[y1:y2, x1:x2]
                letter = self.extract_letter_from_tile(tile_crop)
                row_letters.append(letter)
            letter_grid.append(row_letters)

        return letter_grid, tile_grid

    def extract_target_words_from_image(self, img_input: Union[str, np.ndarray]) -> List[str]:
        """Extract the target word list from the left-side panel.

        Returns:
            List of detected target words.
        """
        if not PYTESSERACT_AVAILABLE:
            return []

        img = self.load_image(img_input)
        h, w = img.shape[:2]

        # Crop the left white card panel (approx 0 to 30% width, 10% to 90% height)
        panel_w = int(w * 0.32)
        panel_y1 = int(h * 0.08)
        panel_y2 = int(h * 0.90)
        panel_crop = img[panel_y1:panel_y2, 0:panel_w]

        gray = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

        config = r"--psm 6"
        try:
            raw_text = pytesseract.image_to_string(binary, config=config)
        except Exception:
            return []

        target_words = []
        for line in raw_text.splitlines():
            line_clean = line.strip().upper()
            # Extract alphabetic parts (ignore point values like +200, +400, 'WORDS: 4')
            words_in_line = [
                "".join(c for c in token if c.isalpha())
                for token in line_clean.split()
            ]
            for word in words_in_line:
                if len(word) >= 3 and word not in ("WORDS", "WORD", "POINT", "POINTS", "BONUS"):
                    if word not in target_words:
                        target_words.append(word)

        return target_words
