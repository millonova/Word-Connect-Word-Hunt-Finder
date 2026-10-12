"""Template Matching & Geometric Disambiguation Engine for Word Hunt.

Features:
- Self-bootstrapping 48x48 canonical A-Z template library.
- Multi-scale normalized cross-correlation (cv2.TM_CCOEFF_NORMED).
- Specialized geometric disambiguation:
  - P vs D: Bottom-Right Quadrant (BRQ) pixel density analysis.
  - O vs D: Left-edge vertical stem linearity analysis.
  - E vs F: Lower horizontal bar presence check.
"""

import os
from typing import Dict, Optional, Tuple
import numpy as np
import cv2

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


from .path_utils import get_resource_path


class TemplateMatcher:
    """High-accuracy multi-scale OpenCV template matcher with geometric disambiguation."""

    CONFIDENCE_THRESHOLD: float = 0.72
    CANVAS_SIZE: int = 48
    GLYPH_MAX_DIM: int = 38

    # Multi-scale factors to accommodate minor DPI/scale variations
    SCALES = (0.88, 0.94, 1.0, 1.06, 1.12)

    def __init__(self, templates_dir: Optional[str] = None) -> None:
        if templates_dir is None:
            self.templates_dir = get_resource_path("assets/templates")
        else:
            self.templates_dir = os.path.abspath(templates_dir)

        os.makedirs(self.templates_dir, exist_ok=True)
        self.templates: Dict[str, np.ndarray] = {}
        self._ensure_templates()

    def _ensure_templates(self) -> None:
        """Verify assets/templates/ contains all 26 masks; synthesize if missing."""
        font = self._resolve_system_font()

        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            tmpl_file = os.path.join(self.templates_dir, f"{char}.png")
            loaded = None
            if os.path.exists(tmpl_file):
                loaded = cv2.imread(tmpl_file, cv2.IMREAD_GRAYSCALE)

            if loaded is not None and loaded.shape == (self.CANVAS_SIZE, self.CANVAS_SIZE):
                self.templates[char] = loaded
            else:
                canonical = self._synthesize_glyph(char, font)
                self.templates[char] = canonical
                try:
                    cv2.imwrite(tmpl_file, canonical)
                except Exception:
                    pass

    def _resolve_system_font(self):
        """Find the cleanest bold sans-serif font available on the host system."""
        if not PIL_AVAILABLE:
            return None

        candidates = [
            "arialbd.ttf",   # Arial Bold
            "segoeuib.ttf",  # Segoe UI Bold
            "tahomabd.ttf",  # Tahoma Bold
            "verdana.ttf",   # Verdana
            "arial.ttf",     # Arial Regular
        ]

        windir = os.environ.get("WINDIR", r"C:\Windows")
        for fn in candidates:
            try:
                font_path = os.path.join(windir, "Fonts", fn)
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, 54)
            except Exception:
                continue

        # Non-Windows fallbacks
        unix_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
        ]
        for uf in unix_fonts:
            try:
                if os.path.exists(uf):
                    return ImageFont.truetype(uf, 54)
            except Exception:
                continue

        return None

    def _synthesize_glyph(self, char: str, font) -> np.ndarray:
        """Render character using PIL font and normalize to tightly bound 48x48 mask."""
        if PIL_AVAILABLE and font is not None:
            img = Image.new("L", (80, 80), 0)
            draw = ImageDraw.Draw(img)
            bb = draw.textbbox((0, 0), char, font=font)
            w = bb[2] - bb[0]
            h = bb[3] - bb[1]
            tx = (80 - w) // 2 - bb[0]
            ty = (80 - h) // 2 - bb[1]
            draw.text((tx, ty), char, fill=255, font=font)
            raw_binary = np.array(img, dtype=np.uint8)
        else:
            raw_binary = np.zeros((80, 80), dtype=np.uint8)
            (tw, th), _ = cv2.getTextSize(char, cv2.FONT_HERSHEY_DUPLEX, 1.6, 3)
            cv2.putText(
                raw_binary, char,
                ((80 - tw) // 2, (80 + th) // 2),
                cv2.FONT_HERSHEY_DUPLEX, 1.6, 255, 3, cv2.LINE_AA
            )

        return self.normalize_glyph(raw_binary)

    @classmethod
    def normalize_glyph(cls, binary_mask: np.ndarray) -> np.ndarray:
        """Extract bounding contour and scale into centered 48x48 binary canvas.

        Foreground pixels: 255 (white)
        Background pixels: 0 (black)
        """
        pts = cv2.findNonZero(binary_mask)
        if pts is None:
            return np.zeros((cls.CANVAS_SIZE, cls.CANVAS_SIZE), dtype=np.uint8)

        x, y, gw, gh = cv2.boundingRect(pts)
        glyph = binary_mask[y:y + gh, x:x + gw]

        # Isotropic scale to GLYPH_MAX_DIM (38px)
        scale = float(cls.GLYPH_MAX_DIM) / max(gw, gh)
        nw = max(4, min(cls.CANVAS_SIZE - 4, int(round(gw * scale))))
        nh = max(4, min(cls.CANVAS_SIZE - 4, int(round(gh * scale))))

        scaled = cv2.resize(glyph, (nw, nh), interpolation=cv2.INTER_AREA)
        _, binarized = cv2.threshold(scaled, 127, 255, cv2.THRESH_BINARY)

        canvas = np.zeros((cls.CANVAS_SIZE, cls.CANVAS_SIZE), dtype=np.uint8)
        ox = (cls.CANVAS_SIZE - nw) // 2
        oy = (cls.CANVAS_SIZE - nh) // 2
        canvas[oy:oy + nh, ox:ox + nw] = binarized
        return canvas

    # =========================================================================
    # Phase 4: Geometric Disambiguation Engine
    # =========================================================================

    @staticmethod
    def disambiguate_p_vs_d(glyph_48: np.ndarray) -> str:
        """Disambiguate P vs D using Bottom-Right Quadrant (BRQ) pixel density.

        A 'D' has a closed loop extending into the lower-right area.
        A 'P' has an open stem in the bottom half with no pixels in BRQ.
        """
        # Bottom-right quadrant: y: [24, 44], x: [24, 44]
        brq = glyph_48[24:44, 24:44]
        total_pixels = brq.size
        active_pixels = np.count_nonzero(brq > 127)
        density = active_pixels / float(total_pixels)

        if density < 0.08:
            return "P"
        if density > 0.18:
            return "D"
        # In marginal territory, compare to top-right quadrant
        trq = glyph_48[4:24, 24:44]
        trq_active = np.count_nonzero(trq > 127)
        if trq_active > 0 and (active_pixels / float(trq_active)) < 0.35:
            return "P"
        return "D"

    @staticmethod
    def disambiguate_o_vs_d(glyph_48: np.ndarray) -> str:
        """Disambiguate O vs D using Left-Edge Vertical Stem Linearity.

        A 'D' has a straight vertical left stem (low x-coordinate variance & spread).
        An 'O' has a curved outer left contour (convex bowing outwards).
        """
        # Sample leftmost foreground pixel coordinates along rows y in [8, 40]
        left_coords = []
        for y in range(8, 40):
            xs = np.where(glyph_48[y, :] > 127)[0]
            if len(xs) > 0:
                left_coords.append(xs[0])

        if len(left_coords) < 10:
            return "D"  # Fallback

        left_arr = np.array(left_coords, dtype=np.float32)
        spread = float(np.max(left_arr) - np.min(left_arr))
        variance = float(np.var(left_arr))

        # 'D' vertical stem has nearly constant x (spread <= 1.5, variance < 0.6)
        # 'O' curved contour has x curving inwards at top and bottom (spread >= 2.5, variance >= 0.8)
        if spread <= 1.5 and variance < 0.6:
            return "D"
        if spread >= 2.5 or variance >= 0.8:
            return "O"

        return "D" if variance < 0.7 else "O"

    @staticmethod
    def disambiguate_e_vs_f(glyph_48: np.ndarray) -> str:
        """Disambiguate E vs F by checking for the bottom horizontal bar."""
        # Bottom horizontal strip in right half: y in [36, 44], x in [20, 42]
        bottom_bar = glyph_48[36:44, 20:42]
        active_count = np.count_nonzero(bottom_bar > 127)

        # 'E' has prominent bottom bar pixels (>= 18)
        # 'F' has empty space there (< 8)
        if active_count >= 14:
            return "E"
        return "F"

    def match_glyph(self, binary_glyph: np.ndarray) -> Tuple[str, float]:
        """Perform template matching with structural disambiguation.

        Returns:
            Tuple[best_character, confidence_score]
        """
        norm_test = self.normalize_glyph(binary_glyph)
        if np.count_nonzero(norm_test) < 20:
            return "?", 0.0

        scores: Dict[str, float] = {}

        # 1. Fast Primary Pass: Canonical scale (1.0) against all 26 templates
        for char, tmpl in self.templates.items():
            match_res = cv2.matchTemplate(norm_test, tmpl, cv2.TM_CCOEFF_NORMED)
            scores[char] = float(match_res[0, 0])

        best_char, best_score = max(scores.items(), key=lambda item: item[1])

        # 2. If confidence is lower than threshold, check subtle scale variations
        if best_score < self.CONFIDENCE_THRESHOLD:
            # Pre-generate scaled test variants outside the template loop
            scaled_variants = []
            for scale in (0.92, 1.08):
                nh = int(round(self.CANVAS_SIZE * scale))
                nw = int(round(self.CANVAS_SIZE * scale))
                res = cv2.resize(norm_test, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR)
                _, res = cv2.threshold(res, 127, 255, cv2.THRESH_BINARY)
                if scale > 1.0:
                    cy, cx = (nh - self.CANVAS_SIZE) // 2, (nw - self.CANVAS_SIZE) // 2
                    variant = res[cy:cy + self.CANVAS_SIZE, cx:cx + self.CANVAS_SIZE]
                else:
                    variant = np.zeros((self.CANVAS_SIZE, self.CANVAS_SIZE), dtype=np.uint8)
                    cy, cx = (self.CANVAS_SIZE - nh) // 2, (self.CANVAS_SIZE - nw) // 2
                    variant[cy:cy + nh, cx:cx + nw] = res
                scaled_variants.append(variant)

            for char, tmpl in self.templates.items():
                for variant in scaled_variants:
                    m_res = cv2.matchTemplate(variant, tmpl, cv2.TM_CCOEFF_NORMED)
                    sc = float(m_res[0, 0])
                    if sc > scores[char]:
                        scores[char] = sc

            best_char, best_score = max(scores.items(), key=lambda item: item[1])

        # Rank candidates to find runner-up for disambiguation
        sorted_chars = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        second_char, second_score = sorted_chars[1] if len(sorted_chars) > 1 else ("", 0.0)

        # 3. Geometric disambiguation checks for known close pairs
        top_two = {best_char, second_char}

        if {"P", "D"}.issubset(top_two) or (best_char in ("P", "D") and abs(best_score - second_score) < 0.15):
            resolved = self.disambiguate_p_vs_d(norm_test)
            return resolved, max(best_score, second_score)

        if {"O", "D"}.issubset(top_two) or (best_char in ("O", "D") and abs(best_score - second_score) < 0.15):
            resolved = self.disambiguate_o_vs_d(norm_test)
            return resolved, max(best_score, second_score)

        if {"E", "F"}.issubset(top_two) or (best_char in ("E", "F") and abs(best_score - second_score) < 0.15):
            resolved = self.disambiguate_e_vs_f(norm_test)
            return resolved, max(best_score, second_score)

        return best_char, best_score
