#!/usr/bin/env python3
"""Mechanical reproduction of the shifted-ladder counterexample.

The algebraic coefficient identity at z=i is checked exactly over Q(i).
Trace-norm and Gaussian distributional-pairing convergence are then evaluated
with 80-digit Decimal arithmetic.  Those decimals are numerical corroboration;
the accompanying research note contains the analytic convergence proof.
"""

from __future__ import annotations

from decimal import Decimal, getcontext
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path


getcontext().prec = 80
D = Decimal
PI = D("3.141592653589793238462643383279502884197169399375105820974944592307816406286")
ALPHA_Q = Q(1, 2)
ALPHA = D(1) / D(2)
SIGMA = D(2)


def cadd(x: tuple[Q, Q], y: tuple[Q, Q]) -> tuple[Q, Q]:
    return (x[0] + y[0], x[1] + y[1])


def csub(x: tuple[Q, Q], y: tuple[Q, Q]) -> tuple[Q, Q]:
    return (x[0] - y[0], x[1] - y[1])


def cmul(x: tuple[Q, Q], y: tuple[Q, Q]) -> tuple[Q, Q]:
    return (x[0] * y[0] - x[1] * y[1], x[0] * y[1] + x[1] * y[0])


def cinv(x: tuple[Q, Q]) -> tuple[Q, Q]:
    den = x[0] * x[0] + x[1] * x[1]
    assert den != 0
    return (x[0] / den, -x[1] / den)


def cdiv(x: tuple[Q, Q], y: tuple[Q, Q]) -> tuple[Q, Q]:
    return cmul(x, cinv(y))


def exact_coefficient_identity(k: int) -> bool:
    """1/(k-i)-1/(k+a-i) = a/((k-i)(k+a-i)), exactly."""
    left_factor = (Q(k), Q(-1))
    right_factor = (Q(k) + ALPHA_Q, Q(-1))
    lhs = csub(cinv(left_factor), cinv(right_factor))
    rhs = cdiv((ALPHA_Q, Q(0)), cmul(left_factor, right_factor))
    return lhs == rhs


def resolvent_term(k: int) -> Decimal:
    kd = D(k)
    first = (kd * kd + D(1)).sqrt()
    shifted = kd + ALPHA
    second = (shifted * shifted + D(1)).sqrt()
    return ALPHA / (first * second)


def trace_norm_partial(n: int) -> Decimal:
    return sum((resolvent_term(k) for k in range(-n, n + 1)), D(0))


def trace_norm_tail_upper(n: int) -> Decimal:
    """For alpha=1/2, bound the omitted two-sided tail by log((N+a)/(N-a))."""
    nd = D(n)
    assert nd > ALPHA
    return ((nd + ALPHA) / (nd - ALPHA)).ln()


def gaussian(t: Decimal) -> Decimal:
    return (-(t * t) / (D(2) * SIGMA * SIGMA)).exp()


def gaussian_fourier(xi: Decimal) -> Decimal:
    return SIGMA * (D(2) * PI).sqrt() * (-(SIGMA * SIGMA * xi * xi) / D(2)).exp()


def cutoff_pairing(n: int) -> Decimal:
    total = D(0)
    for k in range(-n, n + 1):
        kd = D(k)
        total += gaussian_fourier(kd) - gaussian_fourier(kd + ALPHA)
    return total


def comb_pairing(m_cutoff: int) -> Decimal:
    # alpha=1/2: 1-exp(2*pi*i*alpha*m) is 0 for even m and 2 for odd m.
    total = D(0)
    for m in range(-m_cutoff, m_cutoff + 1):
        coefficient = D(0) if m % 2 == 0 else D(2)
        total += D(2) * PI * coefficient * gaussian(D(2) * PI * D(m))
    return total


def comb_tail_upper(m_cutoff: int) -> Decimal:
    """Bound |tail| after |m|<=M using a Gaussian integral estimate."""
    m = D(m_cutoff)
    c = D(2) * PI * PI / (SIGMA * SIGMA)
    # 2 sides * coefficient<=2 * outer 2*pi, then integral tail.
    return D(4) * PI * (-(c * m * m)).exp() / (c * m)


def zadd(x: tuple[Decimal, Decimal], y: tuple[Decimal, Decimal]) -> tuple[Decimal, Decimal]:
    return (x[0] + y[0], x[1] + y[1])


def zmul(x: tuple[Decimal, Decimal], y: tuple[Decimal, Decimal]) -> tuple[Decimal, Decimal]:
    return (x[0] * y[0] - x[1] * y[1], x[0] * y[1] + x[1] * y[0])


def third_root_power(m: int) -> tuple[Decimal, Decimal]:
    root3_over_2 = D(3).sqrt() / D(2)
    return (
        (D(1), D(0)),
        (-D(1) / D(2), root3_over_2),
        (-D(1) / D(2), -root3_over_2),
    )[m % 3]


def i_power(m: int) -> tuple[Decimal, Decimal]:
    return ((D(1), D(0)), (D(0), D(1)), (-D(1), D(0)), (D(0), -D(1)))[m % 4]


def phase_sensitive_fixture(n: int, m_cutoff: int) -> dict:
    """Non-even Schwartz test locking the Fourier sign and comb phase."""
    alpha = D(1) / D(3)
    beta = D(1) / D(4)

    def hat_phi(xi: Decimal) -> Decimal:
        return gaussian_fourier(xi - beta)

    finite = D(0)
    for k in range(-n, n + 1):
        kd = D(k)
        # Deliberately retain the negative arguments dictated by the convention.
        finite += hat_phi(-kd) - hat_phi(-(kd + alpha))

    comb = (D(0), D(0))
    for m in range(-m_cutoff, m_cutoff + 1):
        root = third_root_power(m)
        coefficient = (D(1) - root[0], -root[1])
        phi_at_lattice = i_power(m)  # exp(i * (1/4) * 2*pi*m)
        weighted = zmul(coefficient, phi_at_lattice)
        scale = D(2) * PI * gaussian(D(2) * PI * D(m))
        comb = zadd(comb, (scale * weighted[0], scale * weighted[1]))

    difference = ((finite - comb[0]) ** 2 + comb[1] ** 2).sqrt()
    assert difference < D("1e-60")
    return {
        "alpha": "1/3",
        "test_function": "exp(-t^2/8) exp(i t/4)",
        "N": n,
        "comb_cutoff": m_cutoff,
        "cutoff_pairing": [ds(finite), ds(D(0))],
        "comb_pairing": [ds(comb[0]), ds(comb[1])],
        "absolute_difference": ds(difference),
        "purpose": "locks hat(phi)(-xi) and the positive phase exp(2*pi*i*alpha*m)",
    }


def ds(x: Decimal) -> str:
    return format(x, ".60E")


def main() -> None:
    exact_range = 500
    assert all(exact_coefficient_identity(k) for k in range(-exact_range, exact_range + 1))

    norm_rows = []
    for n in (4, 8, 16, 32, 64, 128, 256):
        partial = trace_norm_partial(n)
        tail = trace_norm_tail_upper(n)
        norm_rows.append(
            {
                "N": n,
                "partial_trace_norm": ds(partial),
                "analytic_tail_bound_80digit_evaluation": ds(tail),
                "enclosure_upper": ds(partial + tail),
            }
        )
    assert all(
        D(norm_rows[j + 1]["analytic_tail_bound_80digit_evaluation"])
        < D(norm_rows[j]["analytic_tail_bound_80digit_evaluation"])
        for j in range(len(norm_rows) - 1)
    )

    m_cutoff = 20
    comb = comb_pairing(m_cutoff)
    comb_tail = comb_tail_upper(m_cutoff)
    distribution_rows = []
    for n in (0, 1, 2, 3, 4, 6, 8, 12, 16):
        finite = cutoff_pairing(n)
        distribution_rows.append(
            {
                "N": n,
                "cutoff_pairing": ds(finite),
                "difference_from_truncated_comb": ds(abs(finite - comb)),
            }
        )
    assert D(distribution_rows[-1]["difference_from_truncated_comb"]) < D("1e-60")

    report = {
        "schema": "shifted-ladder-reproduction/v1",
        "model": {
            "Hilbert_space": "ell^2(Z)",
            "A_e_k": "k e_k",
            "A0_e_k": "(k+1/2) e_k",
            "resolvent_point": "i",
            "test_function": "exp(-t^2/(2 sigma^2))",
            "sigma": "2",
        },
        "exact_checks": {
            "coefficient_identity": "pass",
            "integer_range": [-exact_range, exact_range],
            "arithmetic": "fractions.Fraction over Q(i)",
        },
        "trace_norm_convergence": norm_rows,
        "distributional_convergence": {
            "fourier_convention": "hat(phi)(xi)=integral phi(t) exp(-i t xi) dt",
            "comb_pairing_M20": ds(comb),
            "comb_tail_upper_bound": ds(comb_tail),
            "rows": distribution_rows,
            "phase_sensitive_non_even_fixture": phase_sensitive_fixture(16, 20),
        },
        "epistemic_status": {
            "coefficient_identity": "exactly mechanically verified on the stated finite range",
            "decimal_tables": "80-digit numerical corroboration",
            "universal_convergence": "proved analytically in the companion theorem note",
        },
    }
    payload = json.dumps(report, sort_keys=True, indent=2) + "\n"
    out = Path(__file__).with_name("shifted_ladder_report.json")
    out.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(f"PASS: shifted ladder reproduced; report_sha256={digest}")


if __name__ == "__main__":
    main()
