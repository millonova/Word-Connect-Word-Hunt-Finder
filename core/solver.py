"""Prefix Trie and 8-Directional DFS Backtracking Pathfinder Engine.

Solves 4x4 Word Hunt / Boggle boards without tile reuse per word.
"""

from typing import List, Tuple, Dict, Set, Optional, Union
import unittest

Coordinate = Tuple[int, int]
Path = List[Coordinate]
Grid = List[List[str]]


class TrieNode:
    """Node in a Prefix Trie."""
    __slots__ = ("children", "word", "is_end")

    def __init__(self) -> None:
        self.children: Dict[str, "TrieNode"] = {}
        self.word: Optional[str] = None
        self.is_end: bool = False


class Trie:
    """Prefix Trie with branch pruning for rapid word search."""

    def __init__(self, words: Optional[List[str]] = None) -> None:
        self.root = TrieNode()
        if words:
            for word in words:
                self.insert(word)

    def insert(self, word: str) -> None:
        """Insert uppercase word into Trie."""
        node = self.root
        for char in word.upper():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.word = word.upper()


class BoggleSolver:
    """4x4 Grid Pathfinder using Trie-guided DFS backtracking."""

    # 8-Directional neighbor offsets: (dr, dc)
    DIRECTIONS: List[Tuple[int, int]] = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]

    def __init__(self, grid: Optional[Union[Grid, List[str], str]] = None) -> None:
        self.grid: Grid = []
        self.rows: int = 0
        self.cols: int = 0
        if grid is not None:
            self.set_grid(grid)

    def set_grid(self, grid: Union[Grid, List[str], str]) -> None:
        """Set or update the board grid from 2D list, list of strings, or 16-char string."""
        if isinstance(grid, str):
            clean_str = "".join(grid.split()).upper()
            if len(clean_str) == 16:
                formatted = [
                    [clean_str[r * 4 + c] for c in range(4)]
                    for r in range(4)
                ]
            else:
                lines = [line.strip().upper() for line in grid.strip().splitlines() if line.strip()]
                formatted = [[c for c in line] for line in lines]
        elif isinstance(grid, list):
            if all(isinstance(row, str) for row in grid):
                formatted = [[c.upper() for c in row] for row in grid]
            elif all(isinstance(row, list) for row in grid):
                formatted = [[str(c).upper() for c in row] for row in grid]
            else:
                raise ValueError("Unsupported grid format.")
        else:
            raise ValueError("Unsupported grid type.")

        self.grid = formatted
        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.rows > 0 else 0

    def find_words(self, target_words: List[str]) -> Dict[str, Optional[Path]]:
        """Search for a specific list of target words on the board."""
        clean_targets = [w.strip().upper() for w in target_words if w.strip()]
        trie = Trie(clean_targets)
        found_map: Dict[str, Path] = {}

        for r in range(self.rows):
            for c in range(self.cols):
                first_char = self.grid[r][c]
                if first_char in trie.root.children:
                    self._dfs_trie(
                        r, c,
                        trie.root.children[first_char],
                        [(r, c)],
                        {(r, c)},
                        found_map
                    )

        return {w: found_map.get(w, None) for w in clean_targets}

    def find_word(self, word: str) -> Optional[Path]:
        """Find the first valid path for a single word."""
        target = word.strip().upper()
        if not target:
            return None

        first_char = target[0]
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == first_char:
                    visited = {(r, c)}
                    path = self._dfs_single_word(r, c, target, 1, [(r, c)], visited)
                    if path:
                        return path
        return None

    def find_all_dictionary_words(self, dictionary: List[str], min_length: int = 3) -> Dict[str, Path]:
        """Find all valid dictionary words present on the board."""
        filtered = [w.strip().upper() for w in dictionary if len(w.strip()) >= min_length]
        trie = Trie(filtered)
        found_map: Dict[str, Path] = {}

        for r in range(self.rows):
            for c in range(self.cols):
                first_char = self.grid[r][c]
                if first_char in trie.root.children:
                    self._dfs_trie(
                        r, c,
                        trie.root.children[first_char],
                        [(r, c)],
                        {(r, c)},
                        found_map
                    )
        return found_map

    def _dfs_trie(
        self,
        r: int,
        c: int,
        node: TrieNode,
        current_path: Path,
        visited: Set[Coordinate],
        found_map: Dict[str, Path]
    ) -> None:
        """Recursive DFS guided by prefix Trie."""
        if node.is_end and node.word:
            if node.word not in found_map:
                found_map[node.word] = list(current_path)

        for dr, dc in self.DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if (nr, nc) not in visited:
                    next_char = self.grid[nr][nc]
                    if next_char in node.children:
                        visited.add((nr, nc))
                        current_path.append((nr, nc))
                        self._dfs_trie(
                            nr, nc,
                            node.children[next_char],
                            current_path,
                            visited,
                            found_map
                        )
                        current_path.pop()
                        visited.remove((nr, nc))

    def _dfs_single_word(
        self,
        r: int,
        c: int,
        target: str,
        index: int,
        current_path: Path,
        visited: Set[Coordinate]
    ) -> Optional[Path]:
        """Search for single word match."""
        if index == len(target):
            return list(current_path)

        next_char = target[index]
        for dr, dc in self.DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if (nr, nc) not in visited and self.grid[nr][nc] == next_char:
                    visited.add((nr, nc))
                    current_path.append((nr, nc))
                    result = self._dfs_single_word(nr, nc, target, index + 1, current_path, visited)
                    if result is not None:
                        return result
                    current_path.pop()
                    visited.remove((nr, nc))
        return None


# -----------------------------------------------------------------------------
# Built-in Verification Tests for Prompt Game Boards
# -----------------------------------------------------------------------------

class TestPromptGameBoards(unittest.TestCase):
    """Unit test cases validating the 4 game boards from the screenshots."""

    def test_board_1(self):
        """Board 1: ADAS / CTER / DISO / CSAL"""
        grid = [
            ["A", "D", "A", "S"],
            ["C", "T", "E", "R"],
            ["D", "I", "S", "O"],
            ["C", "S", "A", "L"]
        ]
        solver = BoggleSolver(grid)
        sample_words = ["DISASTER", "ASTER", "DATES", "ACTED", "ACID", "REST"]
        results = solver.find_words(sample_words)
        for w in sample_words:
            self.assertIsNotNone(results.get(w), f"Word '{w}' should exist on Board 1")

    def test_board_2(self):
        """Board 2: ETDA / ESOI / DREG / CNAR"""
        grid = [
            ["E", "T", "D", "A"],
            ["E", "S", "O", "I"],
            ["D", "R", "E", "G"],
            ["C", "N", "A", "R"]
        ]
        solver = BoggleSolver(grid)
        sample_words = ["STORE", "CRANE", "DREG", "TERSE", "GRANDEES", "GRANDEST"]
        results = solver.find_words(sample_words)
        for w in sample_words:
            self.assertIsNotNone(results.get(w), f"Word '{w}' should exist on Board 2")

    def test_board_3(self):
        """Board 3: DIED / WTSN / BAEI / CMPG"""
        grid = [
            ["D", "I", "E", "D"],
            ["W", "T", "S", "N"],
            ["B", "A", "E", "I"],
            ["C", "M", "P", "G"]
        ]
        solver = BoggleSolver(grid)
        sample_words = ["DIED", "DISTEND", "DIET", "DIETS", "STEAM", "BAWDIES"]
        results = solver.find_words(sample_words)
        for w in sample_words:
            self.assertIsNotNone(results.get(w), f"Word '{w}' should exist on Board 3")

    def test_board_4(self):
        """Board 4: IRSR / SEFE / RTLN / PAII"""
        grid = [
            ["I", "R", "S", "R"],
            ["S", "E", "F", "E"],
            ["R", "T", "L", "N"],
            ["P", "A", "I", "I"]
        ]
        solver = BoggleSolver(grid)
        sample_words = ["RESTRAIN", "PRALINES", "RISE", "SIRE", "PART", "RISES"]
        results = solver.find_words(sample_words)
        for w in sample_words:
            self.assertIsNotNone(results.get(w), f"Word '{w}' should exist on Board 4")


if __name__ == "__main__":
    unittest.main()
