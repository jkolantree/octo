from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .exact import scalar_json


MAX_LINEAR_EQUATIONS = 128
MAX_LINEAR_VARIABLES = 128
MAX_LINEAR_CELLS = MAX_LINEAR_EQUATIONS * MAX_LINEAR_VARIABLES
MAX_INTERMEDIATE_BITS = 8192


def _bounded(value: Fraction) -> Fraction:
    if value.numerator.bit_length() > MAX_INTERMEDIATE_BITS or value.denominator.bit_length() > MAX_INTERMEDIATE_BITS:
        raise ValueError(f"exact linear-algebra intermediate exceeds {MAX_INTERMEDIATE_BITS} bits")
    return value


def _validate_system(matrix: Sequence[Sequence[Fraction]], rhs: Sequence[Fraction], columns_hint: int | None = None) -> tuple[int, int]:
    rows = len(matrix)
    if rows != len(rhs):
        raise ValueError("linear system row count disagrees with right-hand side")
    columns = len(matrix[0]) if matrix else (0 if columns_hint is None else columns_hint)
    if columns < 0:
        raise ValueError("linear system column count must be nonnegative")
    if columns_hint is not None and columns != columns_hint:
        raise ValueError("linear system column count disagrees with its declared width")
    if any(len(row) != columns for row in matrix):
        raise ValueError("linear system rows have inconsistent widths")
    if rows > MAX_LINEAR_EQUATIONS:
        raise ValueError(f"linear system exceeds {MAX_LINEAR_EQUATIONS} equations")
    if columns > MAX_LINEAR_VARIABLES:
        raise ValueError(f"linear system exceeds {MAX_LINEAR_VARIABLES} variables")
    if rows * columns > MAX_LINEAR_CELLS:
        raise ValueError(f"linear system exceeds {MAX_LINEAR_CELLS} coefficient cells")
    for row in matrix:
        for value in row:
            _bounded(value)
    for value in rhs:
        _bounded(value)
    return rows, columns


def _matvec(matrix: Sequence[Sequence[Fraction]], vector: Sequence[Fraction]) -> list[Fraction]:
    return [sum((value * vector[index] for index, value in enumerate(row)), Fraction(0)) for row in matrix]


def _transpose_matvec(matrix: Sequence[Sequence[Fraction]], vector: Sequence[Fraction], columns: int) -> list[Fraction]:
    return [sum((matrix[row][column] * vector[row] for row in range(len(matrix))), Fraction(0)) for column in range(columns)]


@dataclass(frozen=True)
class LinearCertificate:
    consistent: bool
    solution: tuple[Fraction, ...] | None
    dual: tuple[Fraction, ...] | None
    pairing: Fraction | None
    least_squares_solution: tuple[Fraction, ...] | None
    residual: tuple[Fraction, ...]
    eta_squared: Fraction

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": "exact_solution" if self.consistent else "dual_obstruction",
            "field": "Q",
            "residual": [scalar_json(value) for value in self.residual],
            "eta_squared": scalar_json(self.eta_squared),
        }
        if self.solution is not None:
            payload["solution"] = [scalar_json(value) for value in self.solution]
        if self.dual is not None:
            payload["dual"] = [scalar_json(value) for value in self.dual]
        if self.pairing is not None:
            payload["pairing"] = scalar_json(self.pairing)
        if self.least_squares_solution is not None:
            payload["least_squares_solution"] = [scalar_json(value) for value in self.least_squares_solution]
        return payload


def solve_exact(matrix: Sequence[Sequence[Fraction]], rhs: Sequence[Fraction], *, ncols: int | None = None) -> LinearCertificate:
    """Solve ``A x = b`` over Q and return a replayable primal or dual certificate.

    Free variables are deterministically set to zero.  For an inconsistent
    system, the returned row-operation vector ``y`` satisfies ``y^T A = 0``
    and ``y^T b != 0``.  The residual is the exact least-squares residual.
    """

    rows, columns = _validate_system(matrix, rhs, ncols)
    data = [[Fraction(value) for value in row] + [Fraction(rhs[index])] for index, row in enumerate(matrix)]
    operations = [[Fraction(int(i == j)) for j in range(rows)] for i in range(rows)]
    pivots: list[tuple[int, int]] = []
    pivot_row = 0
    for column in range(columns):
        pivot = next((row for row in range(pivot_row, rows) if data[row][column] != 0), None)
        if pivot is None:
            continue
        data[pivot_row], data[pivot] = data[pivot], data[pivot_row]
        operations[pivot_row], operations[pivot] = operations[pivot], operations[pivot_row]
        scale = data[pivot_row][column]
        data[pivot_row] = [_bounded(value / scale) for value in data[pivot_row]]
        operations[pivot_row] = [_bounded(value / scale) for value in operations[pivot_row]]
        for row in range(rows):
            if row == pivot_row or data[row][column] == 0:
                continue
            factor = data[row][column]
            data[row] = [_bounded(data[row][j] - factor * data[pivot_row][j]) for j in range(columns + 1)]
            operations[row] = [_bounded(operations[row][j] - factor * operations[pivot_row][j]) for j in range(rows)]
        pivots.append((pivot_row, column))
        pivot_row += 1
        if pivot_row == rows:
            break

    inconsistent_row = next(
        (row for row in range(rows) if all(data[row][column] == 0 for column in range(columns)) and data[row][columns] != 0),
        None,
    )
    if inconsistent_row is None:
        solution = [Fraction(0) for _ in range(columns)]
        for row, column in pivots:
            solution[column] = data[row][columns]
        replay = _matvec(matrix, solution)
        if replay != list(rhs):
            raise ArithmeticError("internal exact-solution replay failed")
        return LinearCertificate(True, tuple(solution), None, None, None, tuple(Fraction(0) for _ in range(rows)), Fraction(0))

    dual = operations[inconsistent_row]
    if _transpose_matvec(matrix, dual, columns) != [Fraction(0) for _ in range(columns)]:
        raise ArithmeticError("internal dual-certificate annihilation replay failed")
    pairing = sum((dual[row] * rhs[row] for row in range(rows)), Fraction(0))
    if pairing == 0:
        raise ArithmeticError("internal dual-certificate pairing replay failed")

    normal = [
        [sum((matrix[row][i] * matrix[row][j] for row in range(rows)), Fraction(0)) for j in range(columns)]
        for i in range(columns)
    ]
    normal_rhs = _transpose_matvec(matrix, rhs, columns)
    least_squares = solve_exact(normal, normal_rhs) if columns else LinearCertificate(True, tuple(), None, None, None, tuple(), Fraction(0))
    if not least_squares.consistent or least_squares.solution is None:
        raise ArithmeticError("normal equations unexpectedly inconsistent over Q")
    approximation = _matvec(matrix, least_squares.solution)
    residual = tuple(_bounded(rhs[row] - approximation[row]) for row in range(rows))
    if _transpose_matvec(matrix, residual, columns) != [Fraction(0) for _ in range(columns)]:
        raise ArithmeticError("internal least-squares orthogonality replay failed")
    eta_squared = _bounded(sum((value * value for value in residual), Fraction(0)))
    if eta_squared == 0:
        raise ArithmeticError("inconsistent system has zero residual")
    return LinearCertificate(False, None, tuple(dual), pairing, least_squares.solution, residual, eta_squared)
