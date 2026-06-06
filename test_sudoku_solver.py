"""Tests for the Sudoku solver."""

import unittest

from sudoku_solver import (
    SIZE,
    SudokuError,
    Choice,
    parse_grid,
    solve,
    solved,
    validate,
)


EASY = (
    "53..7...."
    "6..195..."
    ".98....6."
    "8...6...3"
    "4..8.3..1"
    "7...2...6"
    ".6....28."
    "...419..5"
    "....8..79"
)

EASY_SOLUTION = (
    "534678912"
    "672195348"
    "198342567"
    "859761423"
    "426853791"
    "713924856"
    "961537284"
    "287419635"
    "345286179"
)

# A famously hard puzzle that forces deep backtracking.
HARD = (
    "8........"
    "..36....."
    ".7..9.2.."
    ".5...7..."
    "....457.."
    "...1...3."
    "..1....68"
    "..85...1."
    ".9....4.."
)


def to_string(grid):
    return "".join(str(grid[r][c]) for r in range(SIZE) for c in range(SIZE))


def is_valid_solution(grid):
    full = set(range(1, 10))
    for r in range(SIZE):
        if set(grid[r]) != full:
            return False
    for c in range(SIZE):
        if {grid[r][c] for r in range(SIZE)} != full:
            return False
    for br in range(0, SIZE, 3):
        for bc in range(0, SIZE, 3):
            box = {grid[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3)}
            if box != full:
                return False
    return True


class ParseTests(unittest.TestCase):
    def test_parse_accepts_dots_and_zeros(self):
        grid = parse_grid(EASY)
        self.assertEqual(grid[0][0], 5)
        self.assertEqual(grid[0][2], 0)

    def test_parse_ignores_formatting(self):
        pretty = """
            5 3 . | . 7 . | . . .
            6 . . | 1 9 5 | . . .
            . 9 8 | . . . | . 6 .
            ------+-------+------
            8 . . | . 6 . | . . 3
            4 . . | 8 . 3 | . . 1
            7 . . | . 2 . | . . 6
            ------+-------+------
            . 6 . | . . . | 2 8 .
            . . . | 4 1 9 | . . 5
            . . . | . 8 . | . 7 9
        """
        self.assertEqual(parse_grid(pretty), parse_grid(EASY))

    def test_parse_rejects_wrong_size(self):
        with self.assertRaises(SudokuError):
            parse_grid("123")


class SolveTests(unittest.TestCase):
    def test_solves_easy(self):
        grid = parse_grid(EASY)
        answer = solved(grid)
        self.assertEqual(to_string(answer), EASY_SOLUTION)

    def test_solves_hard(self):
        grid = parse_grid(HARD)
        answer = solved(grid)
        self.assertTrue(is_valid_solution(answer))

    def test_does_not_mutate_input(self):
        grid = parse_grid(EASY)
        before = [row[:] for row in grid]
        solved(grid)
        self.assertEqual(grid, before)

    def test_already_solved(self):
        grid = parse_grid(EASY_SOLUTION)
        self.assertEqual(to_string(solved(grid)), EASY_SOLUTION)

    def test_empty_grid_gets_filled(self):
        grid = [[0] * 9 for _ in range(9)]
        self.assertTrue(is_valid_solution(solved(grid)))

    def test_trace_records_choices(self):
        grid = parse_grid(EASY)
        trace = []
        solve(grid, trace)
        self.assertTrue(trace)
        self.assertIsInstance(trace[0], Choice)
        # Every recorded candidate carries a confidence in (0, 1].
        for choice in trace:
            for cand in choice.candidates:
                self.assertGreater(cand.confidence, 0)
                self.assertLessEqual(cand.confidence, 1)


class ValidationTests(unittest.TestCase):
    def test_detects_duplicate_clue(self):
        grid = parse_grid(EASY)
        grid[0][1] = 5  # duplicate 5 in the first row
        with self.assertRaises(SudokuError):
            validate(grid)

    def test_unsolvable_raises(self):
        # Valid clues (no duplicates) but no completion exists: the only blank
        # in the top row must be a 9, yet a 9 already sits in its column/box.
        grid = parse_grid(
            "12345678."
            "........."
            "........9"
            "........."
            "........."
            "........."
            "........."
            "........."
            "........."
        )
        validate(grid)  # the clues themselves are consistent
        with self.assertRaises(SudokuError):
            solved(grid)


if __name__ == "__main__":
    unittest.main()
