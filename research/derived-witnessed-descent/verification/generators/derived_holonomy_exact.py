#!/usr/bin/env python3
"""Exact certificate generator/checker for finite rational derived holonomy.

This is deliberately dependency-free.  Matrices are lists of lists of
fractions.Fraction.  The checker never converts exact inputs to floats.

Conventions
-----------
* d[n] : C_n -> C_{n-1}
* f[n] : C_n -> D_n
* h[n] : C_n -> D_{n+1}
* f-g = d_D h + h d_C

For every submitted pair of chain maps the homotopy equation is flattened to
A x = omega.  Gauss-Jordan elimination tracks row operations.  A solvable
system returns an exact homotopy x.  An inconsistent system returns an exact
Farkas-style witness y satisfying y^T A = 0 and y^T omega != 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


Matrix = List[List[Q]]
Vector = List[Q]


def q(x: int | str | Q) -> Q:
    return x if isinstance(x, Q) else Q(x)


def zeros(rows: int, cols: int) -> Matrix:
    return [[Q(0) for _ in range(cols)] for _ in range(rows)]


def identity(n: int) -> Matrix:
    out = zeros(n, n)
    for i in range(n):
        out[i][i] = Q(1)
    return out


def shape(a: Matrix) -> Tuple[int, int]:
    if not a:
        return (0, 0)
    width = len(a[0])
    assert all(len(row) == width for row in a)
    return len(a), width


def matmul(a: Matrix, b: Matrix) -> Matrix:
    ar, ac = shape(a)
    br, bc = shape(b)
    assert ac == br, (shape(a), shape(b))
    out = zeros(ar, bc)
    for i in range(ar):
        for k in range(ac):
            if a[i][k] != 0:
                for j in range(bc):
                    out[i][j] += a[i][k] * b[k][j]
    return out


def compose_with_dims(a: Matrix, b: Matrix, out_rows: int, middle: int, out_cols: int) -> Matrix:
    """Compose matrices while retaining the dimensions of a zero middle space."""
    if out_rows == 0 or middle == 0 or out_cols == 0:
        return zeros(out_rows, out_cols)
    return matmul(a, b)


def matadd(a: Matrix, b: Matrix) -> Matrix:
    assert shape(a) == shape(b)
    return [[x + y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def matsub(a: Matrix, b: Matrix) -> Matrix:
    assert shape(a) == shape(b)
    return [[x - y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def flatten(a: Matrix) -> Vector:
    return [x for row in a for x in row]


def rank(a: Matrix) -> int:
    if not a:
        return 0
    m = [row[:] for row in a]
    rows, cols = shape(m)
    r = 0
    for c in range(cols):
        pivot = next((i for i in range(r, rows) if m[i][c] != 0), None)
        if pivot is None:
            continue
        m[r], m[pivot] = m[pivot], m[r]
        scale = m[r][c]
        m[r] = [v / scale for v in m[r]]
        for i in range(rows):
            if i != r and m[i][c] != 0:
                factor = m[i][c]
                m[i] = [u - factor * v for u, v in zip(m[i], m[r])]
        r += 1
        if r == rows:
            break
    return r


def transpose(a: Matrix, rows_if_empty: int = 0) -> Matrix:
    if not a:
        return [[] for _ in range(rows_if_empty)]
    rows, cols = shape(a)
    return [[a[i][j] for i in range(rows)] for j in range(cols)]


def columns(a: Matrix) -> List[Vector]:
    rows, cols = shape(a)
    return [[a[i][j] for i in range(rows)] for j in range(cols)]


def from_columns(cols: Sequence[Vector], rows: int) -> Matrix:
    if not cols:
        return zeros(rows, 0)
    assert all(len(c) == rows for c in cols)
    return [[c[i] for c in cols] for i in range(rows)]


def matvec(a: Matrix, x: Vector) -> Vector:
    rows, cols = shape(a)
    assert cols == len(x)
    return [sum((a[i][j] * x[j] for j in range(cols)), Q(0)) for i in range(rows)]


def dot(x: Vector, y: Vector) -> Q:
    assert len(x) == len(y)
    return sum((a * b for a, b in zip(x, y)), Q(0))


def solve_or_separate(a: Matrix, b: Vector, ncols: int | None = None) -> dict:
    """Return exact x with Ax=b, or exact y with y^T A=0, y^T b!=0."""
    rows = len(b)
    if a:
        ar, cols = shape(a)
        assert ar == rows
    else:
        cols = 0 if ncols is None else ncols
        a = zeros(rows, cols)
    aug = [a[i][:] + [b[i]] for i in range(rows)]
    transform = identity(rows)
    pivot_cols: List[int] = []
    r = 0
    for c in range(cols):
        pivot = next((i for i in range(r, rows) if aug[i][c] != 0), None)
        if pivot is None:
            continue
        aug[r], aug[pivot] = aug[pivot], aug[r]
        transform[r], transform[pivot] = transform[pivot], transform[r]
        scale = aug[r][c]
        aug[r] = [v / scale for v in aug[r]]
        transform[r] = [v / scale for v in transform[r]]
        for i in range(rows):
            if i != r and aug[i][c] != 0:
                factor = aug[i][c]
                aug[i] = [u - factor * v for u, v in zip(aug[i], aug[r])]
                transform[i] = [u - factor * v for u, v in zip(transform[i], transform[r])]
        pivot_cols.append(c)
        r += 1
        if r == rows:
            break

    for i in range(rows):
        if all(aug[i][c] == 0 for c in range(cols)) and aug[i][-1] != 0:
            y = transform[i]
            ya = [sum((y[r0] * a[r0][c] for r0 in range(rows)), Q(0)) for c in range(cols)]
            yb = dot(y, b)
            assert all(v == 0 for v in ya)
            assert yb != 0
            return {"status": "fail", "y": y, "yTA": ya, "yTb": yb}

    x = [Q(0) for _ in range(cols)]
    for i, c in enumerate(pivot_cols):
        x[c] = aug[i][-1]
    assert matvec(a, x) == b
    return {"status": "pass", "x": x, "Ax": matvec(a, x)}


def nullspace(a: Matrix, ncols: int | None = None) -> List[Vector]:
    """Exact basis for ker(a), returned as column vectors."""
    if a:
        rows, cols = shape(a)
    else:
        rows, cols = 0, (0 if ncols is None else ncols)
        a = zeros(rows, cols)
    m = [row[:] for row in a]
    pivots: List[int] = []
    r = 0
    for c in range(cols):
        pivot = next((i for i in range(r, rows) if m[i][c] != 0), None)
        if pivot is None:
            continue
        m[r], m[pivot] = m[pivot], m[r]
        scale = m[r][c]
        m[r] = [v / scale for v in m[r]]
        for i in range(rows):
            if i != r and m[i][c] != 0:
                factor = m[i][c]
                m[i] = [u - factor * v for u, v in zip(m[i], m[r])]
        pivots.append(c)
        r += 1
        if r == rows:
            break
    free = [c for c in range(cols) if c not in pivots]
    out: List[Vector] = []
    for f in free:
        x = [Q(0) for _ in range(cols)]
        x[f] = Q(1)
        for i, p in enumerate(pivots):
            x[p] = -m[i][f]
        if rows:
            assert matvec(a, x) == [Q(0) for _ in range(rows)]
        out.append(x)
    return out


def independent_extension(seed: Sequence[Vector], candidates: Iterable[Vector]) -> List[Vector]:
    chosen = [v[:] for v in seed]
    old_rank = rank(from_columns(chosen, len(chosen[0]))) if chosen else 0
    for v in candidates:
        rows = len(v)
        candidate_rank = rank(from_columns(chosen + [v], rows))
        if candidate_rank > old_rank:
            chosen.append(v[:])
            old_rank = candidate_rank
    return chosen


@dataclass(frozen=True)
class Complex:
    dims: Dict[int, int]
    d: Dict[int, Matrix]

    def dim(self, n: int) -> int:
        return self.dims.get(n, 0)

    def differential(self, n: int) -> Matrix:
        return self.d.get(n, zeros(self.dim(n - 1), self.dim(n)))

    def degrees(self) -> List[int]:
        return sorted(self.dims)

    def validate(self) -> None:
        for n in self.degrees():
            rows, cols = self.dim(n - 1), self.dim(n)
            dn = self.differential(n)
            if rows == 0:
                assert dn == []
            else:
                assert shape(dn) == (rows, cols)
            composite = compose_with_dims(
                self.differential(n - 1),
                self.differential(n),
                self.dim(n - 2),
                self.dim(n - 1),
                self.dim(n),
            )
            assert all(x == 0 for x in flatten(composite)), f"d^2 != 0 at degree {n}"


def zero_map(target_rows: int, source_cols: int) -> Matrix:
    return zeros(target_rows, source_cols)


def validate_chain_map(c: Complex, d: Complex, f: Dict[int, Matrix]) -> None:
    for n in sorted(set(c.degrees()) | set(d.degrees())):
        fn = f.get(n, zero_map(d.dim(n), c.dim(n)))
        fnm1 = f.get(n - 1, zero_map(d.dim(n - 1), c.dim(n - 1)))
        if d.dim(n) == 0:
            assert fn == []
        else:
            assert shape(fn) == (d.dim(n), c.dim(n))
        left = compose_with_dims(
            d.differential(n), fn, d.dim(n - 1), d.dim(n), c.dim(n)
        )
        right = compose_with_dims(
            fnm1, c.differential(n), d.dim(n - 1), c.dim(n - 1), c.dim(n)
        )
        assert left == right, f"not a chain map at degree {n}"


def homotopy_system(c: Complex, d: Complex, omega: Dict[int, Matrix]) -> Tuple[Matrix, Vector, list]:
    degrees = sorted(set(c.degrees()) | set(d.degrees()))
    equation_slots = [
        (n, i, j)
        for n in degrees
        for i in range(d.dim(n))
        for j in range(c.dim(n))
    ]
    variable_slots = [
        (n, i, j)
        for n in degrees
        for i in range(d.dim(n + 1))
        for j in range(c.dim(n))
    ]
    row_index = {slot: i for i, slot in enumerate(equation_slots)}
    a = zeros(len(equation_slots), len(variable_slots))

    for col, (hn, hi, hj) in enumerate(variable_slots):
        # Contribution d_D[n+1] h_n to degree n.
        dd = d.differential(hn + 1)
        for out_i in range(d.dim(hn)):
            coeff = dd[out_i][hi]
            if coeff:
                a[row_index[(hn, out_i, hj)]][col] += coeff
        # Contribution h_n d_C[n+1] to degree n+1.
        dc = c.differential(hn + 1)
        for in_j in range(c.dim(hn + 1)):
            coeff = dc[hj][in_j]
            if coeff:
                a[row_index[(hn + 1, hi, in_j)]][col] += coeff

    b = []
    for n, i, j in equation_slots:
        om = omega.get(n, zero_map(d.dim(n), c.dim(n)))
        assert shape(om) == (d.dim(n), c.dim(n))
        b.append(om[i][j])
    return a, b, variable_slots


def homology_data(c: Complex, n: int) -> Tuple[List[Vector], List[Vector]]:
    """Return exact bases (B_n, H_n representatives), with B followed by H independent."""
    cycles = nullspace(c.differential(n), ncols=c.dim(n))
    boundaries = columns(c.differential(n + 1))
    b_basis = independent_extension([], boundaries)
    extended = independent_extension(b_basis, cycles)
    return b_basis, extended[len(b_basis):]


def coordinates_in_basis(v: Vector, basis: Sequence[Vector]) -> Vector:
    a = from_columns(basis, len(v))
    solved = solve_or_separate(a, v, ncols=len(basis))
    assert solved["status"] == "pass", "vector is outside declared span"
    return solved["x"]


def induced_homology_map(c: Complex, d: Complex, f: Dict[int, Matrix], n: int) -> Matrix:
    _, hc = homology_data(c, n)
    bd, hd = homology_data(d, n)
    target_basis = bd + hd
    out = zeros(len(hd), len(hc))
    fn = f.get(n, zero_map(d.dim(n), c.dim(n)))
    for j, representative in enumerate(hc):
        image = matvec(fn, representative)
        coeffs = coordinates_in_basis(image, target_basis)
        for i in range(len(hd)):
            out[i][j] = coeffs[len(bd) + i]
    return out


def qstr(x: Q) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def jsonable(value):
    if isinstance(value, Q):
        return qstr(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def audit_case(name: str, c: Complex, d: Complex, f: Dict[int, Matrix], g: Dict[int, Matrix]) -> dict:
    c.validate()
    d.validate()
    validate_chain_map(c, d, f)
    validate_chain_map(c, d, g)
    degrees = sorted(set(c.degrees()) | set(d.degrees()))
    omega = {
        n: matsub(
            f.get(n, zero_map(d.dim(n), c.dim(n))),
            g.get(n, zero_map(d.dim(n), c.dim(n))),
        )
        for n in degrees
    }
    a, b, variables = homotopy_system(c, d, omega)
    cert = solve_or_separate(a, b, ncols=len(variables))
    induced_equal = all(induced_homology_map(c, d, f, n) == induced_homology_map(c, d, g, n) for n in degrees)
    assert (cert["status"] == "pass") == induced_equal
    strict_equal = all(all(x == 0 for x in flatten(omega[n])) for n in degrees)
    return {
        "name": name,
        "strict_equal": strict_equal,
        "induced_homology_equal": induced_equal,
        "derived_holonomy": cert["status"],
        "homotopy_matrix_A": a,
        "omega": b,
        "variables": variables,
        "certificate": cert,
        "homology_dimensions_C": {n: len(homology_data(c, n)[1]) for n in degrees},
        "homology_dimensions_D": {n: len(homology_data(d, n)[1]) for n in degrees},
    }


def main() -> None:
    # Fixture 1: raw discrepancy is nonzero but it is null-homotopic.
    contractible = Complex(dims={0: 1, 1: 1}, d={1: [[Q(1)]]})
    identity_map = {0: [[Q(1)]], 1: [[Q(1)]]}
    zero_contractible = {0: [[Q(0)]], 1: [[Q(0)]]}
    false_block = audit_case(
        "contractible_strict_false_block",
        contractible,
        contractible,
        identity_map,
        zero_contractible,
    )
    assert not false_block["strict_equal"]
    assert false_block["derived_holonomy"] == "pass"

    # Fixture 2: a genuine homology-visible obstruction and dual certificate.
    h0 = Complex(dims={0: 1}, d={})
    visible_fail = audit_case(
        "homology_visible_failure",
        h0,
        h0,
        {0: [[Q(1)]]},
        {0: [[Q(0)]]},
    )
    assert visible_fail["derived_holonomy"] == "fail"
    assert visible_fail["certificate"]["yTA"] == []
    assert visible_fail["certificate"]["yTb"] != 0

    # Fixture 3: failure before observation, equality after quotienting a null direction.
    source = Complex(dims={0: 1}, d={})
    target = Complex(dims={0: 2}, d={})
    pre_observation = audit_case(
        "observation_hidden_before_quotient",
        source,
        target,
        {0: [[Q(1)], [Q(1)]]},
        {0: [[Q(1)], [Q(0)]]},
    )
    quotient = Complex(dims={0: 1}, d={})
    post_observation = audit_case(
        "observation_hidden_after_quotient",
        source,
        quotient,
        {0: [[Q(1)]]},
        {0: [[Q(1)]]},
    )
    assert pre_observation["derived_holonomy"] == "fail"
    assert post_observation["strict_equal"]
    assert post_observation["derived_holonomy"] == "pass"

    # Exhaust every two-term 1x1 complex and every scalar chain-map pair with
    # entries in {-1,0,1}.  audit_case independently compares the homotopy
    # certificate verdict with the induced maps on exact homology.
    exhaustive_count = 0
    for dc in (-1, 0, 1):
        for dd in (-1, 0, 1):
            ec = Complex(dims={0: 1, 1: 1}, d={1: [[Q(dc)]]})
            ed = Complex(dims={0: 1, 1: 1}, d={1: [[Q(dd)]]})
            maps = []
            for f0 in (-1, 0, 1):
                for f1 in (-1, 0, 1):
                    candidate = {0: [[Q(f0)]], 1: [[Q(f1)]]}
                    try:
                        validate_chain_map(ec, ed, candidate)
                    except AssertionError:
                        continue
                    maps.append(candidate)
            for ef in maps:
                for eg in maps:
                    audit_case("exhaustive_internal", ec, ed, ef, eg)
                    exhaustive_count += 1

    report = {
        "schema": "derived-holonomy-exact-report/v1",
        "arithmetic": "fractions.Fraction only; no floating-point operations",
        "convention": "f-g = d_D h + h d_C",
        "exhaustive_small_model_check": {
            "complexes": "all 1x1 two-term differentials in {-1,0,1}",
            "chain_maps": "all scalar degree maps in {-1,0,1}",
            "map_pairs_checked": exhaustive_count,
            "result": "homotopy-system verdict equals induced-homology-map equality in every case",
        },
        "cases": [false_block, visible_fail, pre_observation, post_observation],
    }
    payload = json.dumps(jsonable(report), sort_keys=True, indent=2) + "\n"
    out = Path(__file__).with_name("derived_holonomy_report.json")
    out.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(f"PASS: 4 exact derived-holonomy fixtures; report_sha256={digest}")


if __name__ == "__main__":
    main()
