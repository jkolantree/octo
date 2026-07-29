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
    result: list[Fraction] = []
    for row in matrix:
        total = Fraction(0)
        for index, value in enumerate(row):
            total = _bounded(total + _bounded(value * vector[index]))
        result.append(total)
    return result


def _transpose_matvec(matrix: Sequence[Sequence[Fraction]], vector: Sequence[Fraction], columns: int) -> list[Fraction]:
    result: list[Fraction] = []
    for column in range(columns):
        total = Fraction(0)
        for row in range(len(matrix)):
            total = _bounded(total + _bounded(matrix[row][column] * vector[row]))
        result.append(total)
    return result


def _dot(left: Sequence[Fraction], right: Sequence[Fraction]) -> Fraction:
    if len(left) != len(right):
        raise ValueError("exact vectors have different lengths")
    total = Fraction(0)
    for left_value, right_value in zip(left, right):
        total = _bounded(total + _bounded(left_value * right_value))
    return total


@dataclass(frozen=True)
class LinearCertificate:
    consistent: bool
    solution: tuple[Fraction, ...] | None
    dual: tuple[Fraction, ...] | None
    pairing: Fraction | None
    residual: tuple[Fraction, ...] | None = None
    eta_squared: Fraction | None = None

    def __post_init__(self) -> None:
        if type(self.consistent) is not bool:
            raise TypeError("linear certificate consistency tag must be boolean")
        primal_shape = (
            self.solution is not None
            and self.dual is None
            and self.pairing is None
            and self.residual is not None
            and self.eta_squared is not None
        )
        dual_shape = (
            self.solution is None
            and self.dual is not None
            and self.pairing is not None
            and self.residual is None
            and self.eta_squared is None
        )
        if (self.consistent and not primal_shape) or (
            not self.consistent and not dual_shape
        ):
            raise ValueError("linear certificate variant has an invalid witness shape")

    def to_json(
        self,
        matrix: Sequence[Sequence[Fraction]],
        rhs: Sequence[Fraction],
        *,
        ncols: int | None = None,
    ) -> dict[str, object]:
        """Serialize only after replay against the exact system being claimed."""

        replay_linear_certificate(matrix, rhs, self, ncols=ncols)
        if self.consistent:
            assert self.solution is not None
            assert self.residual is not None
            assert self.eta_squared is not None
            return {
                "kind": "exact_solution",
                "field": "Q",
                "solution": [scalar_json(value) for value in self.solution],
                "residual": [scalar_json(value) for value in self.residual],
                "eta_squared": scalar_json(self.eta_squared),
            }
        assert self.dual is not None
        assert self.pairing is not None
        return {
            "kind": "dual_obstruction",
            "field": "Q",
            "dual": [scalar_json(value) for value in self.dual],
            "pairing": scalar_json(self.pairing),
        }


def replay_linear_certificate(
    matrix: Sequence[Sequence[Fraction]],
    rhs: Sequence[Fraction],
    certificate: LinearCertificate,
    *,
    ncols: int | None = None,
) -> None:
    """Replay a primal or dual exact certificate without solving the system."""

    rows, columns = _validate_system(matrix, rhs, ncols)
    if certificate.consistent:
        if (
            certificate.solution is None
            or certificate.dual is not None
            or certificate.pairing is not None
            or certificate.residual is None
            or certificate.eta_squared is None
            or len(certificate.solution) != columns
            or len(certificate.residual) != rows
        ):
            raise ValueError("consistent certificate has an invalid witness shape")
        solution = tuple(_bounded(value) for value in certificate.solution)
        residual = tuple(_bounded(value) for value in certificate.residual)
        computed_residual = tuple(
            _bounded(left - right)
            for left, right in zip(_matvec(matrix, solution), rhs)
        )
        if residual != computed_residual:
            raise ValueError("exact-solution certificate has an invalid residual")
        if any(residual):
            raise ValueError("exact-solution certificate does not replay")
        eta_squared = _bounded(certificate.eta_squared)
        if eta_squared != _dot(residual, residual):
            raise ValueError("exact-solution certificate has an invalid eta_squared")
        return

    if (
        certificate.solution is not None
        or certificate.dual is None
        or certificate.pairing is None
        or certificate.residual is not None
        or certificate.eta_squared is not None
        or len(certificate.dual) != rows
    ):
        raise ValueError("inconsistent certificate has an invalid witness shape")
    dual = tuple(_bounded(value) for value in certificate.dual)
    if _transpose_matvec(matrix, dual, columns) != [
        Fraction(0) for _ in range(columns)
    ]:
        raise ValueError("dual certificate does not annihilate the system matrix")
    pairing = _dot(dual, rhs)
    if pairing == 0 or pairing != certificate.pairing:
        raise ValueError("dual certificate has an invalid right-hand-side pairing")


def solve_exact(matrix: Sequence[Sequence[Fraction]], rhs: Sequence[Fraction], *, ncols: int | None = None) -> LinearCertificate:
    """Solve ``A x = b`` over Q and return a replayable primal or dual certificate.

    Free variables are deterministically set to zero.  For an inconsistent
    system, the returned row-operation vector ``y`` satisfies ``y^T A = 0``
    and ``y^T b != 0``.  Coordinate-dependent least-squares diagnostics are
    deliberately not required to establish that decisive obstruction.
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
        certificate = LinearCertificate(
            True,
            tuple(solution),
            None,
            None,
            residual=tuple(Fraction(0) for _ in range(rows)),
            eta_squared=Fraction(0),
        )
        try:
            replay_linear_certificate(matrix, rhs, certificate, ncols=columns)
        except ValueError as exc:  # pragma: no cover - internal invariant
            raise ArithmeticError("internal exact-solution replay failed") from exc
        return certificate

    dual = operations[inconsistent_row]
    pairing = _dot(dual, rhs)
    certificate = LinearCertificate(False, None, tuple(dual), pairing)
    try:
        replay_linear_certificate(matrix, rhs, certificate, ncols=columns)
    except ValueError as exc:  # pragma: no cover - internal invariant
        raise ArithmeticError("internal dual-certificate replay failed") from exc
    return certificate
