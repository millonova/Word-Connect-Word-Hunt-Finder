"""Word Connect / Word Hunt Solver Package.

A complete, modular desktop application and algorithm package for 4x4 grid word-search games.
"""

from .core.solver import BoggleSolver, Trie, TrieNode
from .core.dictionary import WordDictionary, calculate_word_score
from .core.vision import VisionEngine
from .ui.overlay import OverlayWindow
from .ui.main_window import WordHuntApp, launch_app

__all__ = [
    "BoggleSolver",
    "Trie",
    "TrieNode",
    "WordDictionary",
    "calculate_word_score",
    "VisionEngine",
    "OverlayWindow",
    "WordHuntApp",
    "launch_app"
]
