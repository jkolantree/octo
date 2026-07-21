from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence


Scalar = Fraction
MAX_RATIONAL_DIGITS = 256
MAX_RATIONAL_TEXT = 2 * MAX_RATIONAL_DIGITS + 2
MAX_MATRIX_AXIS = 128
MAX_MATRIX_CELLS = MAX_MATRIX_AXIS * MAX_MATRIX_AXIS


def rational(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise TypeError("booleans are not rational scalars")
    if isinstance(value, int):
        if len(str(abs(value))) > MAX_RATIONAL_DIGITS:
            raise ValueError(f"integer scalar exceeds {MAX_RATIONAL_DIGITS} digits")
        return Fraction(value)
    if isinstance(value, str):
        if len(value) > MAX_RATIONAL_TEXT:
            raise ValueError(f"rational string exceeds {MAX_RATIONAL_TEXT} characters")
        unsigned = value[1:] if value.startswith("-") else value
        parts = unsigned.split("/")
        if len(parts) > 2 or any(not part.isdigit() for part in parts):
            raise ValueError("rational strings must use integer or numerator/denominator syntax")
        if any(len(part) > MAX_RATIONAL_DIGITS for part in parts):
            raise ValueError(f"rational component exceeds {MAX_RATIONAL_DIGITS} digits")
        if len(parts) == 2 and int(parts[1]) == 0:
            raise ZeroDivisionError("rational denominator is zero")
        return Fraction(value)
    if isinstance(value, float):
        raise TypeError("floating-point scalars are forbidden; use an integer or rational string")
    raise TypeError(f"unsupported rational scalar: {value!r}")


def scalar_json(value: Fraction) -> int | str:
    if value.denominator == 1:
        return value.numerator
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True)
class Matrix:
    rows: tuple[tuple[Fraction, ...], ...]
    ncols_hint: int = 0

    def __post_init__(self) -> None:
        widths = {len(row) for row in self.rows}
        if len(widths) > 1:
            raise ValueError("matrix rows have inconsistent widths")
        if self.rows and self.ncols_hint not in (0, len(self.rows[0])):
            raise ValueError("ncols_hint disagrees with row width")
        if not self.rows and self.ncols_hint < 0:
            raise ValueError("negative matrix width")

    @classmethod
    def from_nested(cls, values: Sequence[Sequence[object]], ncols: int | None = None) -> "Matrix":
        if len(values) > MAX_MATRIX_AXIS:
            raise ValueError(f"matrix has more than {MAX_MATRIX_AXIS} rows")
        if any(len(row) > MAX_MATRIX_AXIS for row in values):
            raise ValueError(f"matrix has more than {MAX_MATRIX_AXIS} columns")
        if sum(len(row) for row in values) > MAX_MATRIX_CELLS:
            raise ValueError(f"matrix has more than {MAX_MATRIX_CELLS} cells")
        rows = tuple(tuple(rational(value) for value in row) for row in values)
        hint = len(rows[0]) if rows else (0 if ncols is None else ncols)
        return cls(rows, hint)

    @classmethod
    def zero(cls, nrows: int, ncols: int) -> "Matrix":
        if nrows < 0 or ncols < 0 or nrows > MAX_MATRIX_AXIS or ncols > MAX_MATRIX_AXIS:
            raise ValueError(f"matrix axes must lie in [0,{MAX_MATRIX_AXIS}]")
        return cls(tuple(tuple(Fraction(0) for _ in range(ncols)) for _ in range(nrows)), ncols)

    @classmethod
    def identity(cls, size: int) -> "Matrix":
        if size < 0 or size > MAX_MATRIX_AXIS:
            raise ValueError(f"identity size must lie in [0,{MAX_MATRIX_AXIS}]")
        return cls(tuple(tuple(Fraction(int(i == j)) for j in range(size)) for i in range(size)), size)

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.rows), len(self.rows[0]) if self.rows else self.ncols_hint

    def __matmul__(self, other: "Matrix") -> "Matrix":
        m, n = self.shape
        n2, p = other.shape
        if n != n2:
            raise ValueError(f"matrix shape mismatch: {self.shape} @ {other.shape}")
        return Matrix(
            tuple(
                tuple(sum((self.rows[i][k] * other.rows[k][j] for k in range(n)), Fraction(0)) for j in range(p))
                for i in range(m)
            ),
            p,
        )

    def __add__(self, other: "Matrix") -> "Matrix":
        if self.shape != other.shape:
            raise ValueError("matrix addition shape mismatch")
        m, n = self.shape
        return Matrix(tuple(tuple(self.rows[i][j] + other.rows[i][j] for j in range(n)) for i in range(m)), n)

    def __sub__(self, other: "Matrix") -> "Matrix":
        if self.shape != other.shape:
            raise ValueError("matrix subtraction shape mismatch")
        m, n = self.shape
        return Matrix(tuple(tuple(self.rows[i][j] - other.rows[i][j] for j in range(n)) for i in range(m)), n)

    def is_zero(self) -> bool:
        return all(value == 0 for row in self.rows for value in row)

    def column(self, index: int) -> tuple[Fraction, ...]:
        _, n = self.shape
        if index < 0 or index >= n:
            raise IndexError(index)
        return tuple(row[index] for row in self.rows)

    def first_nonzero_column(self) -> tuple[int, tuple[Fraction, ...]] | None:
        _, n = self.shape
        for index in range(n):
            column = self.column(index)
            if any(value != 0 for value in column):
                return index, column
        return None

    def rank(self) -> int:
        m, n = self.shape
        data = [list(row) for row in self.rows]
        pivot_row = 0
        for col in range(n):
            pivot = next((row for row in range(pivot_row, m) if data[row][col] != 0), None)
            if pivot is None:
                continue
            data[pivot_row], data[pivot] = data[pivot], data[pivot_row]
            scale = data[pivot_row][col]
            data[pivot_row] = [value / scale for value in data[pivot_row]]
            for row in range(m):
                if row == pivot_row or data[row][col] == 0:
                    continue
                factor = data[row][col]
                data[row] = [data[row][j] - factor * data[pivot_row][j] for j in range(n)]
            pivot_row += 1
            if pivot_row == m:
                break
        return pivot_row

    def to_nested(self) -> list[list[int | str]]:
        return [[scalar_json(value) for value in row] for row in self.rows]
