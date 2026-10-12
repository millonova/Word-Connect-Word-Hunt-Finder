"""Visualizer module for formatting console outputs and rendering OpenCV overlays.

Renders terminal path steps and draws translucent game-authentic highlight lines
and active tile glow onto board screenshots.
"""

from typing import List, Tuple, Dict, Optional, Union
import numpy as np
import cv2

Coordinate = Tuple[int, int]
Path = List[Coordinate]
Grid = List[List[str]]


class Visualizer:
    """Provides ASCII console formatting and OpenCV image path drawing."""

    # Colors for OpenCV (BGR)
    COLOR_TILE_ACTIVE_BG = (136, 217, 152)      # Soft mint green
    COLOR_GLOW_LINE = (220, 245, 230)           # Translucent glowing white-mint line
    COLOR_CORE_LINE = (180, 235, 195)           # Inner glow line
    COLOR_START_NODE = (80, 200, 100)           # Start point green
    COLOR_END_NODE = (60, 170, 230)             # End point accent (orange/gold or cyan)
    COLOR_TEXT = (45, 65, 45)                   # Dark green text

    @staticmethod
    def format_console_solution(
        grid: Grid,
        word: str,
        path: Optional[Path]
    ) -> str:
        """Format a single word solution for clear, beautiful console output."""
        lines = []
        lines.append(f"+----------------------------------------+")
        lines.append(f"| Target Word: {word:<26}|")
        if not path:
            lines.append(f"| Status:      NOT FOUND ON BOARD        |")
            lines.append(f"+----------------------------------------+")
            return "\n".join(lines)

        lines.append(f"| Status:      FOUND ({len(path)} steps)               |")
        lines.append(f"+----------------------------------------+")

        # Step-by-step path trace
        trace_parts = []
        for step, (r, c) in enumerate(path, start=1):
            letter = grid[r][c]
            trace_parts.append(f"Step {step}: ({r}, {c}) '{letter}'")
        
        lines.append("  Path Steps: " + " -> ".join(trace_parts))

        # Grid view showing visit sequence numbers
        step_grid = [[" . " for _ in range(len(grid[0]))] for _ in range(len(grid))]
        for step, (r, c) in enumerate(path, start=1):
            step_grid[r][c] = f"[{step:^2}]"

        lines.append("\n  Board Letters:            Step Sequence:")
        for r in range(len(grid)):
            letters_str = "  ".join(f" {grid[r][c]} " for c in range(len(grid[r])))
            steps_str = " ".join(step_grid[r])
            lines.append(f"  {letters_str}       {steps_str}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def print_all_results(
        grid: Grid,
        results: Dict[str, Optional[Path]]
    ) -> None:
        """Print complete batch results for all target words."""
        print("=" * 60)
        print("         4x4 WORD SEARCH PUZZLE SOLVER RESULTS          ")
        print("=" * 60)

        # Print base grid
        print("\nBoard Matrix:")
        print("    " + "   ".join(f"C{c}" for c in range(len(grid[0]))))
        for r in range(len(grid)):
            row_str = " | ".join(grid[r])
            print(f"R{r}: [ {row_str} ]")
        print("\n" + "-" * 60)

        found_count = sum(1 for p in results.values() if p is not None)
        print(f"Target Words: {len(results)} | Matched: {found_count}\n")

        for word, path in results.items():
            print(Visualizer.format_console_solution(grid, word, path))

    @classmethod
    def draw_solution_overlay(
        cls,
        image: np.ndarray,
        tile_grid: List[List[Dict]],
        word: str,
        path: Path,
        draw_title: bool = True
    ) -> np.ndarray:
        """Draw translucent highlight lines and active tile glow onto image.

        Args:
            image: Original input OpenCV BGR image.
            tile_grid: 4x4 list of tile metadata with 'center' and 'bbox'.
            word: Matched word name.
            path: List of (r, c) coordinates in visiting order.
            draw_title: If True, draws the word title at the top.

        Returns:
            Annotated OpenCV image with glowing path lines.
        """
        output = image.copy()
        overlay = image.copy()

        if not path:
            return output

        # 1. Highlight active tiles with translucent mint glow
        for step, (r, c) in enumerate(path):
            tile_data = tile_grid[r][c]
            tx, ty, tw, th = tile_data["bbox"]
            # Draw rounded rectangular highlight on overlay
            radius = int(min(tw, th) * 0.25)
            cv2.rectangle(
                overlay,
                (tx, ty),
                (tx + tw, ty + th),
                cls.COLOR_TILE_ACTIVE_BG,
                -1
            )

        # Blend tile highlight with 45% opacity
        cv2.addWeighted(overlay, 0.45, output, 0.55, 0, output)

        # 2. Draw glowing connecting lines
        overlay_lines = output.copy()
        points = [tile_grid[r][c]["center"] for r, c in path]

        for i in range(len(points) - 1):
            pt1 = points[i]
            pt2 = points[i + 1]

            # Outer wide translucent glow
            cv2.line(overlay_lines, pt1, pt2, cls.COLOR_GLOW_LINE, thickness=18, lineType=cv2.LINE_AA)
            # Mid glow
            cv2.line(overlay_lines, pt1, pt2, cls.COLOR_CORE_LINE, thickness=10, lineType=cv2.LINE_AA)
            # Core bright white line
            cv2.line(overlay_lines, pt1, pt2, (255, 255, 255), thickness=4, lineType=cv2.LINE_AA)

        # Blend lines with 70% opacity
        cv2.addWeighted(overlay_lines, 0.70, output, 0.30, 0, output)

        # 3. Draw step sequence badges on tile centers
        for step, (r, c) in enumerate(path, start=1):
            cx, cy = tile_grid[r][c]["center"]

            # Small node circle at joint
            cv2.circle(output, (cx, cy), 14, (255, 255, 255), -1, lineType=cv2.LINE_AA)
            cv2.circle(output, (cx, cy), 14, (34, 139, 34), 2, lineType=cv2.LINE_AA)

            # Step number text
            step_txt = str(step)
            (tw, th), _ = cv2.getTextSize(step_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.putText(
                output,
                step_txt,
                (cx - tw // 2, cy + th // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (20, 20, 20),
                1,
                cv2.LINE_AA
            )

        # 4. Optional Top Banner Word Title
        if draw_title:
            title_text = f"FOUND: {word} ({len(path)} letters)"
            h, w = output.shape[:2]
            cv2.putText(
                output,
                title_text,
                (int(w * 0.35), 35),
                cv2.FONT_HERSHEY_DUPLEX,
                1.0,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

        return output

    @classmethod
    def save_solution_image(
        cls,
        image: np.ndarray,
        output_path: str
    ) -> None:
        """Save the annotated solution image to disk."""
        cv2.imwrite(output_path, image)
