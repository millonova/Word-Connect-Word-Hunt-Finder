"""Main application entry point for Word Connect / Word Hunt.

Supports interactive PyQt6 GUI with Sniper Overlay, CLI mode, and test verification.
"""

import sys
import os
import argparse
from typing import List

# Ensure package root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from word_connect.core.solver import BoggleSolver
from word_connect.core.dictionary import WordDictionary, calculate_word_score
from word_connect.ui.main_window import launch_app


DEMO_BOARDS = [
    {
        "name": "Board 1 (ADAS / CTER / DISO / CSAL)",
        "grid": [
            ["A", "D", "A", "S"],
            ["C", "T", "E", "R"],
            ["D", "I", "S", "O"],
            ["C", "S", "A", "L"]
        ],
        "targets": ["DISASTER", "ASTER", "DATES", "ACTED", "ACID", "REST"]
    },
    {
        "name": "Board 2 (ETDA / ESOI / DREG / CNAR)",
        "grid": [
            ["E", "T", "D", "A"],
            ["E", "S", "O", "I"],
            ["D", "R", "E", "G"],
            ["C", "N", "A", "R"]
        ],
        "targets": ["STORE", "CRANE", "DREG", "TERSE", "GRANDEES", "GRANDEST"]
    },
    {
        "name": "Board 3 (DIED / WTSN / BAEI / CMPG)",
        "grid": [
            ["D", "I", "E", "D"],
            ["W", "T", "S", "N"],
            ["B", "A", "E", "I"],
            ["C", "M", "P", "G"]
        ],
        "targets": ["DIED", "DISTEND", "DIET", "DIETS", "STEAM", "BAWDIES"]
    },
    {
        "name": "Board 4 (IRSR / SEFE / RTLN / PAII)",
        "grid": [
            ["I", "R", "S", "R"],
            ["S", "E", "F", "E"],
            ["R", "T", "L", "N"],
            ["P", "A", "I", "I"]
        ],
        "targets": ["RESTRAIN", "PRALINES", "RISE", "SIRE", "PART", "RISES"]
    }
]


def run_cli_solver(grid: List[List[str]], targets: List[str], board_name: str = "Custom Board") -> None:
    """Print CLI formatted solution."""
    print(f"\n{'='*60}")
    print(f" SOLVING: {board_name}")
    print(f"{'='*60}")
    
    print("\nBoard:")
    for r in range(4):
        print("  [ " + " | ".join(grid[r]) + " ]")
    print("-" * 60)

    solver = BoggleSolver(grid)
    results = solver.find_words(targets)

    for word, path in results.items():
        score = calculate_word_score(word)
        if path:
            trace = " -> ".join(f"({r},{c})" for r, c in path)
            print(f"  [FOUND] {word:<10} (+{score:>4} pts) : {trace}")
        else:
            print(f"  [MISS ] {word:<10} : Not on board")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Word Hunt / Boggle Sniper Solver with Vision & Overlay"
    )
    parser.add_argument(
        "--gui", "-g",
        action="store_true",
        help="Launch the interactive PyQt6 Desktop GUI with Sniper Overlay."
    )
    parser.add_argument(
        "--grid",
        type=str,
        help="16-character string representing the 4x4 grid (e.g. 'ADASCTERDISOCSAL')."
    )
    parser.add_argument(
        "--targets", "-t",
        nargs="+",
        help="Target words to search for."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run verification test cases on all 4 game boards."
    )

    args = parser.parse_args()

    if args.gui or (not args.grid and not args.demo and len(sys.argv) == 1):
        launch_app()
    elif args.grid:
        targets = args.targets if args.targets else ["WORD", "GAME"]
        solver = BoggleSolver(args.grid)
        run_cli_solver(solver.grid, targets, "Custom Input Grid")
    else:
        print("Running verification test cases on the 4 game boards...")
        for board in DEMO_BOARDS:
            run_cli_solver(board["grid"], board["targets"], board["name"])


if __name__ == "__main__":
    main()
