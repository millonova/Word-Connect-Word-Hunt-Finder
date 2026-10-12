"""Modern design system, theme tokens, and stylesheets for Word Hunt Solver Pro.

Design Direction:
- Slate & Obsidian Dark Surface (#0B0F17, #131B26, #1C2636)
- Radiant Emerald Primary Accent (#22C55E, hover #3FB950, deep #166534)
- High-contrast typography hierarchy (Segoe UI / Inter + Consolas / JetBrains Mono)
- Tactile hover, active, pressed, and focus-ring micro-states
"""

class Theme:
    # 1. Surface & Background Tokens
    BG_OBSIDIAN = "#090D14"      # Deep window canvas
    BG_SURFACE = "#111722"       # Card / panel background
    BG_SURFACE_HOVER = "#182130" # Card hover
    BG_SURFACE_ACTIVE = "#1E2A3C"# Active card surface
    BG_INPUT = "#0B0F17"         # Inputs & matrix tiles
    BG_INPUT_FOCUS = "#131B26"   # Focused tile
    
    # 2. Border & Divider Tokens
    BORDER_SUBTLE = "#1E293B"    # Subtle dividers
    BORDER_DEFAULT = "#2D3B4F"   # Standard container outline
    BORDER_HOVER = "#3B4D66"     # Hover outline
    BORDER_FOCUS = "#22C55E"     # Active emerald focus ring
    
    # 3. Emerald Accent Tokens
    EMERALD_GLOW = "#10B981"
    EMERALD_PRIMARY = "#22C55E"
    EMERALD_HOVER = "#4ADE80"
    EMERALD_PRESSED = "#15803D"
    EMERALD_BG_SUBTLE = "rgba(34, 197, 94, 0.12)"
    EMERALD_BADGE_BG = "#064E3B"
    EMERALD_BADGE_TXT = "#34D399"
    
    # 4. State & Utility Accents
    AMBER_SCORE = "#FBBF24"      # Score badges
    AMBER_BG = "#451A03"
    DANGER_RED = "#EF4444"       # Stop live scan / errors
    DANGER_HOVER = "#F87171"
    DANGER_PRESSED = "#B91C1C"
    
    # 5. Text & Typography Tokens
    TEXT_PRIMARY = "#F8FAFC"     # Primary text / Headings
    TEXT_SECONDARY = "#94A3B8"   # Subtitles / Secondary labels
    TEXT_MUTED = "#64748B"       # Placeholders / Disabled
    TEXT_ACCENT = "#34D399"      # Green highlights


MAIN_STYLESHEET = f"""
QMainWindow {{
    background-color: {Theme.BG_OBSIDIAN};
}}

QWidget {{
    color: {Theme.TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
    outline: none;
}}

/* Surface Panels / Cards */
QFrame.card {{
    background-color: {Theme.BG_SURFACE};
    border: 1px solid {Theme.BORDER_SUBTLE};
    border-radius: 12px;
}}

QFrame.card:hover {{
    border-color: {Theme.BORDER_DEFAULT};
}}

QFrame.sub-card {{
    background-color: {Theme.BG_INPUT};
    border: 1px solid {Theme.BORDER_SUBTLE};
    border-radius: 8px;
}}

/* Headings & Typography */
QLabel.app-title {{
    font-size: 16px;
    font-weight: 800;
    color: {Theme.TEXT_PRIMARY};
    letter-spacing: 0.5px;
}}

QLabel.card-title {{
    font-size: 12px;
    font-weight: 700;
    color: {Theme.TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 0.75px;
}}

QLabel.metric-value {{
    font-size: 13px;
    font-weight: 700;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    color: {Theme.EMERALD_PRIMARY};
}}

/* Pill Status Badges */
QLabel.status-pill-ready {{
    background-color: {Theme.EMERALD_BADGE_BG};
    color: {Theme.EMERALD_BADGE_TXT};
    font-size: 11px;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 10px;
    border: 1px solid rgba(34, 197, 94, 0.4);
}}

QLabel.status-pill-busy {{
    background-color: #701A75;
    color: #F472B6;
    font-size: 11px;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 10px;
    border: 1px solid rgba(244, 114, 182, 0.4);
}}

/* Buttons */
QPushButton.primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Theme.EMERALD_PRIMARY}, stop:1 #15803D);
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
    border-radius: 8px;
    padding: 8px 16px;
    border: 1px solid rgba(255, 255, 255, 0.15);
}}
QPushButton.primary:hover {{
    background: {Theme.EMERALD_HOVER};
    color: #090D14;
}}
QPushButton.primary:pressed {{
    background: {Theme.EMERALD_PRESSED};
    color: #FFFFFF;
}}

QPushButton.secondary {{
    background-color: {Theme.BG_SURFACE};
    color: {Theme.TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 600;
    border-radius: 8px;
    padding: 7px 14px;
    border: 1px solid {Theme.BORDER_DEFAULT};
}}
QPushButton.secondary:hover {{
    background-color: {Theme.BG_SURFACE_ACTIVE};
    border-color: {Theme.BORDER_HOVER};
}}
QPushButton.secondary:pressed {{
    background-color: {Theme.BG_INPUT};
}}

QPushButton.danger {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Theme.DANGER_RED}, stop:1 {Theme.DANGER_PRESSED});
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
    border-radius: 8px;
    padding: 8px 16px;
    border: none;
}}
QPushButton.danger:hover {{
    background: {Theme.DANGER_HOVER};
}}
QPushButton.danger:pressed {{
    background: {Theme.DANGER_PRESSED};
}}

QPushButton.icon-button {{
    background-color: {Theme.BG_SURFACE};
    color: {Theme.TEXT_SECONDARY};
    border-radius: 8px;
    border: 1px solid {Theme.BORDER_SUBTLE};
    padding: 6px 10px;
    font-size: 14px;
}}
QPushButton.icon-button:hover {{
    color: {Theme.TEXT_PRIMARY};
    border-color: {Theme.BORDER_DEFAULT};
    background-color: {Theme.BG_SURFACE_HOVER};
}}

/* 4x4 Grid Matrix Tile Inputs */
QLineEdit.board-tile {{
    background-color: {Theme.BG_INPUT};
    border: 2px solid {Theme.BORDER_DEFAULT};
    border-radius: 10px;
    color: {Theme.TEXT_PRIMARY};
    font-size: 24px;
    font-weight: 800;
    qproperty-alignment: AlignCenter;
}}
QLineEdit.board-tile:focus {{
    border: 2px solid {Theme.EMERALD_PRIMARY};
    background-color: {Theme.BG_INPUT_FOCUS};
    color: {Theme.EMERALD_HOVER};
}}
QLineEdit.board-tile:hover {{
    border-color: {Theme.BORDER_HOVER};
}}

/* Search & Filter Input */
QLineEdit.search-input {{
    background-color: {Theme.BG_INPUT};
    border: 1px solid {Theme.BORDER_DEFAULT};
    border-radius: 8px;
    color: {Theme.TEXT_PRIMARY};
    padding: 6px 12px;
    font-size: 12px;
}}
QLineEdit.search-input:focus {{
    border-color: {Theme.EMERALD_PRIMARY};
    background-color: {Theme.BG_INPUT_FOCUS};
}}

/* Results Word Table */
QTableWidget {{
    background-color: {Theme.BG_SURFACE};
    border: 1px solid {Theme.BORDER_SUBTLE};
    border-radius: 10px;
    gridline-color: transparent;
    selection-background-color: rgba(34, 197, 94, 0.2);
    selection-color: {Theme.TEXT_PRIMARY};
}}

QTableWidget::item {{
    padding: 6px 8px;
    border-bottom: 1px solid rgba(30, 41, 59, 0.4);
}}

QTableWidget::item:selected {{
    background-color: rgba(34, 197, 94, 0.18);
    border-left: 3px solid {Theme.EMERALD_PRIMARY};
}}

QHeaderView::section {{
    background-color: {Theme.BG_SURFACE};
    color: {Theme.TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    border: none;
    border-bottom: 1px solid {Theme.BORDER_SUBTLE};
    padding: 8px;
}}

/* Modern Sliders */
QSlider::groove:horizontal {{
    height: 4px;
    background: {Theme.BORDER_DEFAULT};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {Theme.EMERALD_PRIMARY};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {Theme.EMERALD_PRIMARY};
    width: 14px;
    height: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {Theme.EMERALD_HOVER};
}}

/* Checkboxes */
QCheckBox {{
    color: {Theme.TEXT_SECONDARY};
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox:hover {{
    color: {Theme.TEXT_PRIMARY};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {Theme.BORDER_DEFAULT};
    background-color: {Theme.BG_INPUT};
}}
QCheckBox::indicator:hover {{
    border-color: {Theme.BORDER_HOVER};
}}
QCheckBox::indicator:checked {{
    background-color: {Theme.EMERALD_PRIMARY};
    border-color: {Theme.EMERALD_PRIMARY};
}}

/* Status Bar */
QStatusBar {{
    background-color: {Theme.BG_OBSIDIAN};
    color: {Theme.TEXT_MUTED};
    font-size: 11px;
    border-top: 1px solid {Theme.BORDER_SUBTLE};
    padding: 4px 10px;
}}
"""
