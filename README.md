# Auto Sudoku Solver

Enter the numbers you already know, press solve, and the rest of the grid is
filled in. There are two ways to use it:

- **Web UI** – open `index.html` in any browser, type the known numbers into
  the cells, and click **Solve**. No build step, no dependencies.
- **Command line** – `solve.py` reads a puzzle interactively, from a file, or
  from stdin and prints the solution.

The solving engine lives in `sudoku_solver.py` (pure Python, no dependencies);
the web UI carries an identical solver in JavaScript so it runs entirely in the
browser.

## How it solves

The solver works the way you described it: it always attacks the most
constrained spot first, keeps the candidate numbers (with confidence scores)
for that spot together, and backtracks the moment a number leads nowhere.

1. **Find the most constrained cell.** For every empty cell it counts how many
   numbers are still legal there. The cell with the *fewest* legal numbers is
   the one whose best candidate has the *highest confidence*
   (`confidence = 1 / number_of_candidates`, so a cell with one option scores a
   certain `1.0`). Ties are broken exactly as described — prefer the cell in the
   **densest 3×3 box** (the box already holding the most numbers), then the cell
   with the highest **row + column fill density**.
2. **Build the candidate sub-array.** The legal numbers for that cell are
   collected into a small list, each tagged with its confidence.
3. **Try the highest-confidence number first**, then recurse to the next most
   constrained cell and repeat.
4. **Backtrack.** If a later cell ends up with no legal number, the search
   unwinds to the last decision and tries the next-best confidence number
   there.

A cell that already has only one possibility is taken immediately, and a cell
with zero possibilities triggers an instant backtrack — together these prune
the search so even very hard puzzles solve in about a second.

This is a most-constrained-variable (MRV) search with confidence-ordered
candidates and chronological backtracking. It always finds a solution when one
exists, and reports puzzles that are contradictory or unsolvable.

## Command-line usage

```bash
# Type the 9 rows interactively (use 0 or . for blanks)
python3 solve.py

# Solve a puzzle stored in a file
python3 solve.py puzzle.txt

# Pipe a puzzle in (digits 1-9, with 0 or . for blanks)
echo "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79" \
  | python3 solve.py -
```

A puzzle file can be a plain run of 81 characters or a "pretty" grid with
spaces, pipes and dashes — any non-digit that isn't `.`, `_` or `*` is ignored,
so most pasted puzzles just work.

## Using the solver as a library

```python
from sudoku_solver import parse_grid, solved, format_grid

grid = parse_grid("53..7....6..195....98....6.8...6...3"
                  "4..8.3..17...2...6.6....28....419..5....8..79")
print(format_grid(solved(grid)))
```

- `parse_grid(text)` → 9×9 list of ints (`0` = blank)
- `solved(grid)` → a solved copy (raises `SudokuError` if invalid/unsolvable)
- `solve(grid, trace=[])` → solves in place; pass a `trace` list to capture the
  cells and confidence-ranked candidates the solver chose along the way
- `validate(grid)` → raises `SudokuError` if the starting clues conflict

## Running the tests

```bash
python3 -m unittest test_sudoku_solver
```

The suite covers parsing, easy/hard puzzles, an empty grid, the no-mutation
guarantee, the decision trace, duplicate-clue detection, and unsolvable
puzzles.
