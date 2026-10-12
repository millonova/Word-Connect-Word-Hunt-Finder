"""Interactive 4x4 Mini Board Visualizer with Antialiased Glowing Swipe Paths.

Features:
- Dual-layer neon emerald glow swipe line.
- Start and End node indicators with sequence order numbering.
- Smooth rounded tile matrix reflecting live board letters.
"""

from typing import Optional, List, Tuple
from PyQt6.QtCore import Qt, QRect, QPointF
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QLinearGradient, QRadialGradient
)

from word_connect.core.solver import Path, Grid
from .styles import Theme


class MiniBoardWidget(QWidget):
    """High-fidelity 4x4 board visualizer with glowing swipe trajectory."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(240, 240)
        self.grid: Grid = [[" "] * 4 for _ in range(4)]
        self.active_path: Optional[Path] = None
        self.active_word: str = ""

    def set_grid(self, grid: Grid) -> None:
        self.grid = grid
        self.update()

    def set_active_path(self, word: str, path: Optional[Path]) -> None:
        self.active_word = word
        self.active_path = path
        self.update()

    def clear_path(self) -> None:
        self.active_path = None
        self.active_word = ""
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h) - 12
        offset_x = (w - side) // 2
        offset_y = (h - side) // 2

        cell_size = side / 4.0
        margin = 4.0

        path_set = set(self.active_path) if self.active_path else set()
        step_order = {pt: idx + 1 for idx, pt in enumerate(self.active_path)} if self.active_path else {}
        total_steps = len(self.active_path) if self.active_path else 0

        tile_centers: List[Tuple[float, float]] = []

        # -------------------------------------------------------------
        # 1. Render 16 Tiles
        # -------------------------------------------------------------
        for r in range(4):
            for c in range(4):
                tx = offset_x + c * cell_size + margin
                ty = offset_y + r * cell_size + margin
                tw = cell_size - margin * 2
                th = cell_size - margin * 2

                is_in_path = (r, c) in path_set
                step = step_order.get((r, c), 0)

                # Tile Background & Border
                if is_in_path:
                    if step == 1:
                        # Start node: radial emerald glow
                        painter.setBrush(QBrush(QColor(16, 185, 129, 70)))
                        painter.setPen(QPen(QColor(34, 197, 94), 2))
                    elif step == total_steps:
                        # End node: amber/emerald finish
                        painter.setBrush(QBrush(QColor(251, 191, 36, 60)))
                        painter.setPen(QPen(QColor(251, 191, 36), 2))
                    else:
                        painter.setBrush(QBrush(QColor(16, 185, 129, 35)))
                        painter.setPen(QPen(QColor(34, 197, 94, 200), 1.5))
                else:
                    painter.setBrush(QBrush(QColor(17, 23, 34)))
                    painter.setPen(QPen(QColor(45, 59, 79), 1))

                painter.drawRoundedRect(int(tx), int(ty), int(tw), int(th), 10, 10)

                # Tile Letter
                char = self.grid[r][c] if r < len(self.grid) and c < len(self.grid[r]) else " "
                painter.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
                
                if is_in_path:
                    painter.setPen(QColor(255, 255, 255))
                else:
                    painter.setPen(QColor(203, 213, 225))
                
                painter.drawText(QRect(int(tx), int(ty), int(tw), int(th)), Qt.AlignmentFlag.AlignCenter, char)

                # Step Sequence Order Badge
                if is_in_path:
                    badge_dia = 16
                    bx = int(tx + tw - badge_dia - 2)
                    by = int(ty + 2)

                    if step == 1:
                        painter.setBrush(QBrush(QColor(34, 197, 94)))
                        painter.setPen(Qt.PenStyle.NoPen)
                    elif step == total_steps:
                        painter.setBrush(QBrush(QColor(251, 191, 36)))
                        painter.setPen(Qt.PenStyle.NoPen)
                    else:
                        painter.setBrush(QBrush(QColor(9, 13, 20, 220)))
                        painter.setPen(QPen(QColor(34, 197, 94), 1))

                    painter.drawEllipse(bx, by, badge_dia, badge_dia)

                    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    painter.setPen(QColor(0, 0, 0) if (step == 1 or step == total_steps) else QColor(255, 255, 255))
                    painter.drawText(QRect(bx, by, badge_dia, badge_dia), Qt.AlignmentFlag.AlignCenter, str(step))

        # -------------------------------------------------------------
        # 2. Render Glowing Antialiased Swipe Trajectory
        # -------------------------------------------------------------
        if self.active_path and len(self.active_path) > 1:
            pts: List[QPointF] = []
            for r, c in self.active_path:
                cx = offset_x + (c + 0.5) * cell_size
                cy = offset_y + (r + 0.5) * cell_size
                pts.append(QPointF(cx, cy))

            # Pass 1: Outer Neon Aura (Glow)
            glow_pen = QPen(QColor(34, 197, 94, 55), 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(glow_pen)
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])

            # Pass 2: Inner Laser Core
            core_pen = QPen(QColor(74, 222, 128, 230), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(core_pen)
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])

            # Pass 3: Glowing Center Points on Each Node
            for idx, pt in enumerate(pts):
                if idx == 0:
                    # Start node halo
                    painter.setBrush(QBrush(QColor(34, 197, 94)))
                    painter.setPen(QPen(QColor(255, 255, 255), 2))
                    painter.drawEllipse(pt, 5, 5)
                elif idx == len(pts) - 1:
                    # End node target
                    painter.setBrush(QBrush(QColor(251, 191, 36)))
                    painter.setPen(QPen(QColor(255, 255, 255), 2))
                    painter.drawEllipse(pt, 5, 5)
                else:
                    painter.setBrush(QBrush(QColor(255, 255, 255)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(pt, 2.5, 2.5)
