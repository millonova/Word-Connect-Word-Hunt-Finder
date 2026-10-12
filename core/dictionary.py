"""Dictionary loader and scoring manager for Word Hunt / Boggle."""

import os
from typing import Set, List, Optional
from .path_utils import get_resource_path

# Standard Word Hunt / Boggle Scoring Model
WORD_HUNT_SCORES = {
    3: 100,
    4: 400,
    5: 800,
    6: 1400,
    7: 2000,
    8: 3000,
}


def calculate_word_score(word: str) -> int:
    """Calculate Word Hunt score based on word length."""
    length = len(word)
    if length <= 2:
        return 0
    if length in WORD_HUNT_SCORES:
        return WORD_HUNT_SCORES[length]
    return 3000 + (length - 8) * 1000


class WordDictionary:
    """Manages loaded vocabulary words with fast memory lookup."""

    def __init__(self, dict_path: Optional[str] = None) -> None:
        self.words: Set[str] = set()
        
        # Look for words.txt / dictionary.txt in package and frozen assets directories
        candidates = [
            dict_path if dict_path else "",
            get_resource_path("assets/words.txt"),
            get_resource_path("assets/dictionary.txt"),
            get_resource_path("dictionary.txt"),
            os.path.join(os.path.dirname(__file__), "..", "dictionary.txt"),
            os.path.abspath("dictionary.txt"),
        ]
        
        loaded = False
        for path in candidates:
            if path and os.path.exists(path):
                self.load_from_file(path)
                loaded = True
                break
        
        if not loaded or len(self.words) == 0:
            self._load_built_in_fallback()

    def load_from_file(self, filepath: str) -> int:
        """Load dictionary words from text file (one per line)."""
        loaded = set()
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    w = line.strip().upper()
                    if len(w) >= 3 and w.isalpha():
                        loaded.add(w)
            if loaded:
                self.words = loaded
        except Exception:
            self._load_built_in_fallback()
        return len(self.words)

    def _load_built_in_fallback(self) -> None:
        """Emergency fallback dictionary."""
        fallback = [
            "REST", "SEAS", "SEAT", "SEATS", "RED", "WANS", "RISE", "TEA",
            "WARE", "WINE", "EAST", "NEST", "STAR", "RATE", "RATES", "STARE",
            "TEAR", "TEARS", "TIRE", "TIRES", "SIRE", "SIRES", "SINE", "SINES",
            "ROSE", "ROSES", "SOAR", "SOARS", "SORE", "SORES", "PAIR", "PAIRS",
            "PEAR", "PEARS", "PEAS", "PORE", "PORES", "POSE", "POSER", "TRIP",
            "TRIPS", "TRAP", "TRAPS", "PART", "PARTS", "PAST", "PASTE", "DIED",
            "TIDE", "DIET", "SIDE", "BIDE", "MINT", "BEAT", "FART", "FEAT",
            "SLATE", "ASTER", "COAST", "TOAST", "ROAST", "DISCO", "SOLAR"
        ]
        self.words = set(fallback)

    def get_word_list(self, min_len: int = 3) -> List[str]:
        """Return words filtered by minimum length."""
        return [w for w in self.words if len(w) >= min_len]
