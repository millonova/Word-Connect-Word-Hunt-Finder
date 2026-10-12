"""Unit tests for BoggleSolver and pathfinding algorithms."""

import unittest
from word_connect.solver import BoggleSolver, Trie


class TestBoggleSolver(unittest.TestCase):
    """Test suite for 4x4 Boggle/Word-Connect Solver."""

    def setUp(self):
        self.board1 = [
            ["W", "I", "T", "K"],
            ["A", "N", "E", "S"],
            ["R", "S", "O", "A"],
            ["I", "E", "P", "A"]
        ]
        self.board2 = [
            ["R", "E", "D", "A"],
            ["Y", "G", "S", "T"],
            ["S", "E", "A", "Y"],
            ["I", "R", "T", "R"]
        ]

    def _verify_path_validity(self, grid, word, path):
        """Helper to assert that a coordinate path is completely valid."""
        self.assertIsNotNone(path, f"Path for '{word}' should not be None.")
        self.assertEqual(len(path), len(word), f"Path length should match word length for '{word}'.")
        
        # Check no duplicate coordinates
        self.assertEqual(len(path), len(set(path)), f"Cells must not be reused for '{word}'.")

        # Check characters match
        for step, (r, c) in enumerate(path):
            self.assertTrue(0 <= r < len(grid), f"Row {r} out of bounds.")
            self.assertTrue(0 <= c < len(grid[0]), f"Col {c} out of bounds.")
            self.assertEqual(
                grid[r][c], word[step],
                f"Mismatch at step {step}: expected '{word[step]}', found '{grid[r][c]}' at ({r}, {c})"
            )

        # Check adjacency between consecutive steps
        for i in range(len(path) - 1):
            r1, c1 = path[i]
            r2, c2 = path[i + 1]
            dr = abs(r1 - r2)
            dc = abs(c1 - c2)
            self.assertTrue(
                max(dr, dc) == 1 and (dr + dc) > 0,
                f"Steps {path[i]} and {path[i+1]} are not adjacent."
            )

    def test_board_1_targets(self):
        """Verify Board 1 test case with target words."""
        targets = ["WANS", "RISE", "TEA", "WARE", "WINE"]
        solver = BoggleSolver(self.board1)
        results = solver.find_words(targets)

        for target in targets:
            path = results.get(target)
            self.assertIsNotNone(path, f"Word '{target}' should be found on Board 1.")
            self._verify_path_validity(self.board1, target, path)

        # Specifically check path for WANS: W(0,0) -> A(1,0) -> N(1,1) -> S(2,1)
        wans_path = results["WANS"]
        self.assertEqual(wans_path, [(0, 0), (1, 0), (1, 1), (2, 1)])

    def test_board_2_targets(self):
        """Verify Board 2 test case with target words."""
        targets = ["REST", "SEAS", "SEAT", "SEATS", "RED"]
        solver = BoggleSolver(self.board2)
        results = solver.find_words(targets)

        for target in targets:
            path = results.get(target)
            self.assertIsNotNone(path, f"Word '{target}' should be found on Board 2.")
            self._verify_path_validity(self.board2, target, path)

        # Specifically check REST: R(0,0) -> E(0,1) -> S(1,2) -> T(1,3)
        rest_path = results["REST"]
        self.assertEqual(rest_path, [(0, 0), (0, 1), (1, 2), (1, 3)])

    def test_no_cell_reuse(self):
        """Ensure a cell cannot be used twice in the same word."""
        # Board with only one 'A', should not be able to form "AA"
        grid = [
            ["A", "B", "C", "D"],
            ["E", "F", "G", "H"],
            ["I", "J", "K", "L"],
            ["M", "N", "O", "P"]
        ]
        solver = BoggleSolver(grid)
        self.assertIsNone(solver.find_word("AA"))
        self.assertIsNone(solver.find_word("ABA"))
        self.assertIsNotNone(solver.find_word("ABFE"))

    def test_diagonal_moves(self):
        """Verify diagonal steps are correctly identified."""
        grid = [
            ["A", "X", "X", "X"],
            ["X", "B", "X", "X"],
            ["X", "X", "C", "X"],
            ["X", "X", "X", "D"]
        ]
        solver = BoggleSolver(grid)
        path = solver.find_word("ABCD")
        self.assertEqual(path, [(0, 0), (1, 1), (2, 2), (3, 3)])

    def test_all_paths_collection(self):
        """Test finding multiple valid paths for ambiguous words."""
        grid = [
            ["A", "B", "C", "D"],
            ["B", "A", "C", "D"],
            ["C", "C", "C", "D"],
            ["D", "D", "D", "D"]
        ]
        solver = BoggleSolver(grid)
        paths = solver.find_all_paths_for_word("AB")
        self.assertGreaterEqual(len(paths), 2)
        for p in paths:
            self._verify_path_validity(grid, "AB", p)

    def test_string_initialization(self):
        """Verify initialization via 16-char string and newline string."""
        solver = BoggleSolver("WITKANESRSOAIEPA")
        self.assertEqual(solver.rows, 4)
        self.assertEqual(solver.cols, 4)
        self.assertEqual(solver.grid[0], ["W", "I", "T", "K"])
        self.assertEqual(solver.grid[3], ["I", "E", "P", "A"])


if __name__ == "__main__":
    unittest.main()
