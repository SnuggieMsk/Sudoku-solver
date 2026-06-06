#!/usr/bin/env python3
"""Interactive command-line front end for the Sudoku solver.

Run it and type the puzzle row by row (use 0 or . for blanks), or pipe a
puzzle in on stdin. Then it prints the solved grid.

Examples:
    python3 solve.py                 # enter the 9 rows interactively
    python3 solve.py puzzle.txt      # read the puzzle from a file
    echo "53..7...." | python3 solve.py -   # read from stdin
"""

from __future__ import annotations

import sys
from typing import List

from sudoku_solver import SudokuError, format_grid, parse_grid, solved

PROMPT = (
    "Enter the puzzle, one row at a time (9 rows).\n"
    "Use digits 1-9 for known cells and 0 or . for blanks.\n"
)


def _read_interactive() -> str:
    print(PROMPT)
    rows: List[str] = []
    while len(rows) < 9:
        try:
            line = input(f"row {len(rows) + 1}: ")
        except EOFError:
            break
        cleaned = [ch for ch in line if ch.isdigit() or ch in "._*"]
        if len(cleaned) != 9:
            print(f"  need exactly 9 cells, got {len(cleaned)} - try again")
            continue
        rows.append("".join(cleaned))
    return "\n".join(rows)


def _read_source(args: List[str]) -> str:
    if not args:
        return _read_interactive()
    if args[0] == "-":
        return sys.stdin.read()
    with open(args[0], "r", encoding="utf-8") as handle:
        return handle.read()


def main(argv: List[str]) -> int:
    try:
        text = _read_source(argv)
        grid = parse_grid(text)
    except SudokuError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: cannot read puzzle: {exc}", file=sys.stderr)
        return 2

    print("\nPuzzle:")
    print(format_grid(grid))

    try:
        answer = solved(grid)
    except SudokuError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 1

    print("\nSolution:")
    print(format_grid(answer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
