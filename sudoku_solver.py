"""Auto Sudoku solver.

Solving strategy (as requested):

1. Pick the densest 3x3 sub-grid (the box that already holds the most numbers
   but still has at least one empty cell).
2. Within that box, pick the empty cell with the highest "row-column fill
   density" - i.e. the cell whose row and column are already the most filled.
   Such a cell is the most constrained, so it has the fewest possibilities.
3. Work out which numbers are legal for that cell and attach a confidence to
   each one. Fewer candidates -> higher confidence per candidate. These are
   kept together in a small list (the "candidate sub array").
4. Try the candidates in order of confidence (highest first), recursing into
   the next densest cell each time.
5. If a number leads to a dead end (some later cell has no legal candidate),
   backtrack and try the next-best confidence number at the last decision
   point.

This is a most-constrained-variable (MRV) search with confidence ordering and
backtracking. It is fast and always finds a solution when one exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

Grid = List[List[int]]

SIZE = 9
BOX = 3
EMPTY = 0


class SudokuError(ValueError):
    """Raised when a puzzle is malformed or has no solution."""


@dataclass
class Candidate:
    """A possible number for a cell, with a confidence score in [0, 1]."""

    value: int
    confidence: float


@dataclass
class Choice:
    """A cell we picked and the candidates we considered for it."""

    row: int
    col: int
    candidates: List[Candidate]


def parse_grid(text: str) -> Grid:
    """Parse a grid from text.

    Accepts digits 1-9 for filled cells and any of ``0 . _ *`` for blanks.
    All other characters (spaces, newlines, pipes, dashes) are ignored, so
    most "pretty printed" puzzles paste in cleanly.
    """
    digits: List[int] = []
    for ch in text:
        if ch.isdigit():
            digits.append(int(ch))
        elif ch in "._*":
            digits.append(EMPTY)
    if len(digits) != SIZE * SIZE:
        raise SudokuError(
            f"expected {SIZE * SIZE} cells, found {len(digits)}"
        )
    return [digits[i * SIZE:(i + 1) * SIZE] for i in range(SIZE)]


def format_grid(grid: Grid) -> str:
    """Render a grid as a human-friendly string with box separators."""
    lines: List[str] = []
    for r in range(SIZE):
        if r % BOX == 0 and r != 0:
            lines.append("------+-------+------")
        cells: List[str] = []
        for c in range(SIZE):
            if c % BOX == 0 and c != 0:
                cells.append("|")
            cells.append(str(grid[r][c]) if grid[r][c] != EMPTY else ".")
        lines.append(" ".join(cells))
    return "\n".join(lines)


def _is_legal(grid: Grid, row: int, col: int, value: int) -> bool:
    """True if placing ``value`` at (row, col) breaks no Sudoku rule."""
    for i in range(SIZE):
        if grid[row][i] == value or grid[i][col] == value:
            return False
    box_r, box_c = (row // BOX) * BOX, (col // BOX) * BOX
    for r in range(box_r, box_r + BOX):
        for c in range(box_c, box_c + BOX):
            if grid[r][c] == value:
                return False
    return True


def validate(grid: Grid) -> None:
    """Check the starting grid has no duplicate clues. Raises SudokuError."""
    if len(grid) != SIZE or any(len(row) != SIZE for row in grid):
        raise SudokuError("grid must be 9x9")
    for r in range(SIZE):
        for c in range(SIZE):
            v = grid[r][c]
            if v == EMPTY:
                continue
            if not (1 <= v <= 9):
                raise SudokuError(f"bad value {v} at ({r}, {c})")
            grid[r][c] = EMPTY
            ok = _is_legal(grid, r, c, v)
            grid[r][c] = v
            if not ok:
                raise SudokuError(f"clue {v} at ({r}, {c}) conflicts")


def _candidates(grid: Grid, row: int, col: int) -> List[Candidate]:
    """Legal numbers for an empty cell, each with a confidence score.

    Confidence is ``1 / number_of_candidates`` for every candidate: a cell
    with a single possibility yields confidence 1.0 (a certainty), while a
    cell with several possibilities spreads the confidence thinly across them.
    """
    legal = [v for v in range(1, SIZE + 1) if _is_legal(grid, row, col, v)]
    if not legal:
        return []
    confidence = 1.0 / len(legal)
    return [Candidate(value=v, confidence=confidence) for v in legal]


def _box_fill(grid: Grid, box_r: int, box_c: int) -> int:
    """Count filled cells in the 3x3 box anchored at (box_r, box_c)."""
    return sum(
        1
        for r in range(box_r, box_r + BOX)
        for c in range(box_c, box_c + BOX)
        if grid[r][c] != EMPTY
    )


def _row_col_density(grid: Grid, row: int, col: int) -> int:
    """How filled the cell's row and column already are (higher = more so)."""
    filled_row = sum(1 for c in range(SIZE) if grid[row][c] != EMPTY)
    filled_col = sum(1 for r in range(SIZE) if grid[r][col] != EMPTY)
    return filled_row + filled_col


def _select_cell(grid: Grid) -> Optional[Tuple[int, int]]:
    """Pick the next empty cell to fill, following the density strategy.

    The most constrained cell is the one whose candidate list is shortest -
    that is, the cell whose best candidate carries the highest confidence
    (confidence = 1 / number_of_candidates). Picking it first keeps the search
    shallow and lets forced cells (a single candidate) fall in immediately.

    Ties are broken exactly the way the strategy describes: prefer the cell in
    the densest 3x3 box (the box already holding the most numbers), and within
    that prefer the cell with the highest row-column fill density. The result
    is the cell that the original "densest box, then densest row/column"
    description points at, sharpened so it never wanders into a cell that still
    has many possibilities while a near-certain one is waiting.

    Returns ``None`` when the grid is full, or the first cell found to have no
    legal candidate at all (so the caller can backtrack right away).
    """
    best_cell: Optional[Tuple[int, int]] = None
    best_key: Optional[Tuple[int, int, int]] = None

    for r in range(SIZE):
        for c in range(SIZE):
            if grid[r][c] != EMPTY:
                continue
            count = sum(
                1 for v in range(1, SIZE + 1) if _is_legal(grid, r, c, v)
            )
            if count == 0:
                return (r, c)  # dead end - backtrack immediately
            # Smaller candidate count wins (higher confidence); then denser
            # box; then denser row/column. Negate the densities so that
            # "smaller tuple is better" holds for every component.
            box_fill = _box_fill(grid, (r // BOX) * BOX, (c // BOX) * BOX)
            key = (count, -box_fill, -_row_col_density(grid, r, c))
            if best_key is None or key < best_key:
                best_key = key
                best_cell = (r, c)
                if count == 1:
                    return best_cell  # forced cell - take it now

    return best_cell  # None when the grid is full


def solve(grid: Grid, trace: Optional[List[Choice]] = None) -> bool:
    """Solve ``grid`` in place. Returns True on success.

    If ``trace`` is provided, every decision (cell + ordered candidates) is
    appended to it, giving a record of the path the solver took.
    """
    cell = _select_cell(grid)
    if cell is None:
        return True  # filled every cell

    row, col = cell
    candidates = _candidates(grid, row, col)
    if not candidates:
        return False  # dead end -> caller backtracks

    # Highest confidence first.
    candidates.sort(key=lambda cand: cand.confidence, reverse=True)
    if trace is not None:
        trace.append(Choice(row=row, col=col, candidates=candidates))

    for cand in candidates:
        grid[row][col] = cand.value
        if solve(grid, trace):
            return True
        grid[row][col] = EMPTY  # backtrack and try next confidence number

    return False


def solved(grid: Grid) -> Grid:
    """Return a solved copy of ``grid`` without mutating the input."""
    validate(grid)
    work = [row[:] for row in grid]
    if not solve(work):
        raise SudokuError("puzzle has no solution")
    return work
