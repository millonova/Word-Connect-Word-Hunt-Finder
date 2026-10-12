"""Core pathfinding and search engine for 4x4 grid word puzzles.

Implements Trie-based prefix pruning and DFS backtracking across 8 directions.
"""

from typing import List, Tuple, Dict, Set, Optional, Union


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
    """Prefix Trie for efficient word and prefix matching."""

    def __init__(self, words: Optional[List[str]] = None) -> None:
        self.root = TrieNode()
        if words:
            for word in words:
                self.insert(word)

    def insert(self, word: str) -> None:
        """Insert an uppercase word into the Trie."""
        node = self.root
        for char in word.upper():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.word = word.upper()

    def search_prefix(self, prefix: str) -> Optional[TrieNode]:
        """Return the TrieNode matching prefix if it exists, else None."""
        node = self.root
        for char in prefix.upper():
            if char not in node.children:
                return None
            node = node.children[char]
        return node


class BoggleSolver:
    """4x4 (or arbitrary NxM) Grid Word-Search Solver.

    Connects adjacent tiles in any of the 8 directions (Horizontal,
    Vertical, Diagonal) where each grid cell can only be used at most once
    per word.
    """

    # 8-Directional neighbor offsets: (dr, dc)
    DIRECTIONS: List[Tuple[int, int]] = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]

    def __init__(self, grid: Optional[Grid] = None) -> None:
        """Initialize the solver with an optional grid.

        Args:
            grid: 2D list of characters (e.g. 4x4 matrix).
        """
        self.grid: Grid = []
        self.rows: int = 0
        self.cols: int = 0
        if grid is not None:
            self.set_grid(grid)

    def set_grid(self, grid: Union[Grid, List[str], str]) -> None:
        """Set or update the board grid.

        Accepts:
          - 2D list: [['W', 'I', 'T', 'K'], ...]
          - List of 4-char strings: ['WITK', 'ANES', 'RSOA', 'IEPA']
          - Single 16-char string or newline-separated string
        """
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
        """Find the coordinate path for each target word in target_words.

        Args:
            target_words: List of words to locate on the grid.

        Returns:
            Dict mapping word -> list of (row, col) coordinates, or None if not found.
        """
        clean_targets = [w.strip().upper() for w in target_words if w.strip()]
        trie = Trie(clean_targets)
        found_map: Dict[str, Path] = {}

        # Search for all target words using Trie-pruned DFS
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

        # Build output preserving input order
        results: Dict[str, Optional[Path]] = {}
        for tw in clean_targets:
            results[tw] = found_map.get(tw, None)

        return results

    def find_word(self, word: str) -> Optional[Path]:
        """Find the first valid path for a single target word.

        Args:
            word: Target word to search.

        Returns:
            List of (r, c) coordinates or None if not found.
        """
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

    def find_all_paths_for_word(self, word: str) -> List[Path]:
        """Find all distinct valid coordinate paths for a single word."""
        target = word.strip().upper()
        if not target:
            return []

        all_paths: List[Path] = []
        first_char = target[0]
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == first_char:
                    self._dfs_all_paths(
                        r, c, target, 1,
                        [(r, c)], {(r, c)},
                        all_paths
                    )
        return all_paths

    def find_all_dictionary_words(self, dictionary: List[str], min_length: int = 3) -> Dict[str, Path]:
        """Find all valid dictionary words present on the board.

        Args:
            dictionary: List of English dictionary words.
            min_length: Minimum word length to match.

        Returns:
            Dict mapping found word -> coordinate path.
        """
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

    # -------------------------------------------------------------------------
    # Internal DFS / Backtracking methods
    # -------------------------------------------------------------------------

    def _dfs_trie(
        self,
        r: int,
        c: int,
        node: TrieNode,
        current_path: Path,
        visited: Set[Coordinate],
        found_map: Dict[str, Path]
    ) -> None:
        """DFS traversal guided by Trie prefix tree."""
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
        """DFS search for a single target word returning the first match."""
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

    def _dfs_all_paths(
        self,
        r: int,
        c: int,
        target: str,
        index: int,
        current_path: Path,
        visited: Set[Coordinate],
        all_paths: List[Path]
    ) -> None:
        """DFS collecting all valid paths for a single word."""
        if index == len(target):
            all_paths.append(list(current_path))
            return

        next_char = target[index]
        for dr, dc in self.DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if (nr, nc) not in visited and self.grid[nr][nc] == next_char:
                    visited.add((nr, nc))
                    current_path.append((nr, nc))
                    self._dfs_all_paths(nr, nc, target, index + 1, current_path, visited, all_paths)
                    current_path.pop()
                    visited.remove((nr, nc))

    def get_path_letters(self, path: Path) -> str:
        """Convert a path to the concatenated string of letters."""
        return "".join(self.grid[r][c] for r, c in path)
