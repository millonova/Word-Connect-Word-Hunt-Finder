"""Resizable, movable, semi-translucent Sniper Overlay Window.

Sits directly over the 4x4 puzzle grid on screen with a #2D7D46 green frame.
Auto-saves geometry to AppConfig on move/resize/close.
"""

from typing import List, Tuple, Optional
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent, QPaintEvent, QMoveEvent, QResizeEvent, QCloseEvent

from word_connect.core.config import AppConfig

Coordinate = Tuple[int, int]
Path = List[Coordinate]


class OverlayWindow(QWidget):
    """Semi-translucent Frameless Sniper Window sitting over the game board."""

    roi_changed = pyqtSignal(int, int, int, int)

    def __init__(self, parent=None, initial_rect: Optional[QRect] = None) -> None:
        super().__init__(parent)
        self.config = AppConfig()

        # Window flags
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config.get_overlay_always_on_top():
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Restore geometry from parameter or config
        if initial_rect and initial_rect.width() >= 100 and initial_rect.height() >= 100:
            self.setGeometry(initial_rect)
        else:
            saved = self.config.get_sniper_overlay_geometry()
            self.setGeometry(
                saved.get("x", 300),
                saved.get("y", 200),
                saved.get("width", 930),
                saved.get("height", 930)
            )

        self.setMinimumSize(150, 150)

        # Interaction states
        self._dragging = False
        self._resizing = False
        self._drag_start_pos = QPoint()
        self._resize_margin = 16

        # Active path highlighting
        self._active_path: Optional[Path] = None
        self._active_word: str = ""

    def set_always_on_top(self, enable: bool) -> None:
        """Dynamically toggle WindowStaysOnTopHint on overlay."""
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enable)
        if self.isVisible():
            self.show()

    def set_active_path(self, word: str, path: Optional[Path]) -> None:
        """Update active path to draw directly over the game grid."""
        self._active_word = word
        self._active_path = path
        self.update()

    def clear_active_path(self) -> None:
        """Clear active highlighted path."""
        self._active_path = None
        self._active_word = ""
        self.update()

    def get_roi_rect(self) -> Tuple[int, int, int, int]:
        """Return global screen coordinates (x, y, w, h)."""
        geo = self.geometry()
        return geo.x(), geo.y(), geo.width(), geo.height()

    def set_geometry_rect(self, x: int, y: int, w: int, h: int) -> None:
        """Directly update overlay geometry and emit roi_changed."""
        self.setGeometry(x, y, w, h)
        self.roi_changed.emit(x, y, w, h)
        self.config.set_sniper_overlay_geometry(x, y, w, h)
        self.update()

    # -------------------------------------------------------------------------
    # Auto-Save Window Geometry Hooks
    # -------------------------------------------------------------------------

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        x, y, w, h = self.get_roi_rect()
        self.config.set_sniper_overlay_geometry(x, y, w, h)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        x, y, w, h = self.get_roi_rect()
        self.config.set_sniper_overlay_geometry(x, y, w, h)

    def closeEvent(self, event: QCloseEvent) -> None:
        x, y, w, h = self.get_roi_rect()
        self.config.set_sniper_overlay_geometry(x, y, w, h)
        super().closeEvent(event)

    # -------------------------------------------------------------------------
    # Mouse Events for Dragging and Corner Resizing
    # -------------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            w, h = self.width(), self.height()
            
            if pos.x() >= w - self._resize_margin and pos.y() >= h - self._resize_margin:
                self._resizing = True
            else:
                self._dragging = True
                self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.pos()
        w, h = self.width(), self.height()

        if pos.x() >= w - self._resize_margin and pos.y() >= h - self._resize_margin:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self._dragging:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            self.roi_changed.emit(*self.get_roi_rect())
            event.accept()
        elif self._resizing:
            new_w = max(self.minimumWidth(), pos.x())
            new_h = max(self.minimumHeight(), pos.y())
            self.resize(new_w, new_h)
            self.roi_changed.emit(*self.get_roi_rect())
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self._resizing = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.roi_changed.emit(*self.get_roi_rect())
        event.accept()

    # -------------------------------------------------------------------------
    # Paint Event: #2D7D46 Green Frame HUD & Glowing Paths
    # -------------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Subtle semi-translucent backdrop
        bg_brush = QBrush(QColor(15, 23, 42, 35))
        painter.fillRect(0, 0, w, h, bg_brush)

        # 2. 4x4 Grid Guideline Lines
        grid_pen = QPen(QColor(45, 125, 70, 80), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)

        cell_w = w / 4.0
        cell_h = h / 4.0

        for i in range(1, 4):
            x = int(i * cell_w)
            painter.drawLine(x, 0, x, h)
            y = int(i * cell_h)
            painter.drawLine(0, y, w, y)

        # 3. Outer #2D7D46 Green Border
        frame_pen = QPen(QColor(45, 125, 70, 230), 2)
        painter.setPen(frame_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)

        # 4. Corner Accent Brackets
        bracket_pen = QPen(QColor(52, 211, 153, 255), 4)
        painter.setPen(bracket_pen)
        c_len = min(22, int(cell_w * 0.35))
        
        # Top-Left
        painter.drawLine(1, 1, 1 + c_len, 1)
        painter.drawLine(1, 1, 1, 1 + c_len)
        # Top-Right
        painter.drawLine(w - 1, 1, w - 1 - c_len, 1)
        painter.drawLine(w - 1, 1, w - 1, 1 + c_len)
        # Bottom-Left
        painter.drawLine(1, h - 1, 1 + c_len, h - 1)
        painter.drawLine(1, h - 1, 1, h - 1 - c_len)
        # Bottom-Right
        painter.drawLine(w - 1, h - 1, w - 1 - c_len, h - 1)
        painter.drawLine(w - 1, h - 1, w - 1, h - 1 - c_len)

        # 5. Top Info Badge
        info_text = f"SNIPER ROI: {w}x{h}"
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255, 230))
        painter.fillRect(6, 6, 130, 20, QColor(15, 23, 42, 190))
        painter.drawText(12, 21, info_text)

        # 6. Active Word Stroke Path Visualization
        if self._active_path and len(self._active_path) > 1:
            self._draw_path_stroke(painter, cell_w, cell_h)

    def _draw_path_stroke(self, painter: QPainter, cell_w: float, cell_h: float) -> None:
        """Render glowing connecting path lines and step nodes."""
        points = []
        for r, c in self._active_path:
            cx = int((c + 0.5) * cell_w)
            cy = int((r + 0.5) * cell_h)
            points.append((cx, cy))

        # Glowing Outer Line
        outer_pen = QPen(QColor(52, 211, 153, 160), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(outer_pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])

        # Bright Inner Line
        inner_pen = QPen(QColor(255, 255, 255, 240), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(inner_pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])

        # Step Nodes
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        for idx, (cx, cy) in enumerate(points, start=1):
            painter.setPen(QPen(QColor(45, 125, 70, 255), 2))
            painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
            painter.drawEllipse(cx - 11, cy - 11, 22, 22)
            
            painter.setPen(QColor(255, 255, 255, 255))
            txt = str(idx)
            painter.drawText(cx - 4 if len(txt) == 1 else cx - 7, cy + 4, txt)
