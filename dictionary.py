"""Dictionary loader and word scoring manager for Word Hunt / Boggle."""

import os
from typing import Set, List, Optional

# Standard Boggle / Word Hunt Scoring Rules
WORD_HUNT_SCORES = {
    3: 100,
    4: 400,
    5: 800,
    6: 1400,
    7: 2000,
    8: 3000,
}


def calculate_word_score(word: str) -> int:
    """Calculate the Word Hunt game score for a given word."""
    length = len(word)
    if length <= 2:
        return 0
    if length in WORD_HUNT_SCORES:
        return WORD_HUNT_SCORES[length]
    return 3000 + (length - 8) * 1000


class WordDictionary:
    """Manages loaded dictionary words for instant lookup and Trie generation."""

    def __init__(self, dict_path: Optional[str] = None) -> None:
        self.words: Set[str] = set()
        default_path = os.path.join(os.path.dirname(__file__), "dictionary.txt")
        target_path = dict_path if dict_path and os.path.exists(dict_path) else default_path

        if os.path.exists(target_path):
            self.load_from_file(target_path)
        else:
            self._load_built_in_fallback()

    def load_from_file(self, filepath: str) -> int:
        """Load dictionary from text file (one word per line)."""
        loaded = set()
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    w = line.strip().upper()
                    if len(w) >= 3 and w.isalpha():
                        loaded.add(w)
            self.words = loaded
        except Exception:
            self._load_built_in_fallback()
        return len(self.words)

    def _load_built_in_fallback(self) -> None:
        """Fallback list of common English words if file is missing."""
        fallback = [
            "REST", "SEAS", "SEAT", "SEATS", "RED", "WANS", "RISE", "TEA",
            "WARE", "WINE", "EAST", "NEST", "STAR", "RATE", "RATES", "STARE",
            "TEAR", "TEARS", "TIRE", "TIRES", "SIRE", "SIRES", "SINE", "SINES",
            "WINE", "WINES", "WANE", "WANES", "WARS", "WEAR", "WEARS", "WIRE",
            "WIRES", "ROSE", "ROSES", "SOAR", "SOARS", "SORE", "SORES", "PAIR",
            "PAIRS", "PEAR", "PEARS", "PEAS", "PORE", "PORES", "POSE", "POSER",
            "TRIP", "TRIPS", "TRAP", "TRAPS", "PART", "PARTS", "PAST", "PASTE"
        ]
        self.words = set(fallback)

    def get_word_list(self, min_len: int = 3) -> List[str]:
        """Return list of uppercase words with minimum length."""
        return [w for w in self.words if len(w) >= min_len]
