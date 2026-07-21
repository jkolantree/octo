#!/usr/bin/env python3
"""Mechanical checks accompanying the orthogonal-prime-block obstruction.

The theorem is analytic.  This script checks its finite algebraic core exactly
(uniformly bounded origin jets are killed by one common derivative) and records
prime-cutoff growth of the surviving first-prime-power lower bound.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path


def derivative(coefficients: list[Q]) -> list[Q]:
    """Ascending coefficients for d/dx of a rational polynomial."""
    return [Q(j) * coefficients[j] for j in range(1, len(coefficients))]


def derivative_n(coefficients: list[Q], n: int) -> list[Q]:
    out = coefficients[:]
    for _ in range(n):
        out = derivative(out)
    return out


def sieve(limit: int) -> list[int]:
    flags = bytearray(b"\x01") * (limit + 1)
    if limit >= 0:
        flags[0] = 0
    if limit >= 1:
        flags[1] = 0
    for p in range(2, math.isqrt(limit) + 1):
        if flags[p]:
            start = p * p
            flags[start : limit + 1 : p] = b"\x00" * (((limit - start) // p) + 1)
    return [p for p in range(2, limit + 1) if flags[p]]


def lower_sum(primes: list[int], d: int, eta: float) -> float:
    s = 0.5 + eta
    return math.fsum((math.log(p) ** (d + 2)) / (p**s) for p in primes)


def main() -> None:
    # Arbitrary exact jet coefficients for degrees 0,...,d.  The same d+1
    # derivative annihilates every one, regardless of coefficient magnitude.
    jet_checks = []
    for d in range(0, 9):
        coefficients = [Q((-1) ** j * (j + 2), j + 1) for j in range(d + 1)]
        killed = derivative_n(coefficients, d + 1)
        assert killed == []
        jet_checks.append(
            {
                "maximum_jet_order": d,
                "annihilating_derivative_order": d + 1,
                "exact_result": [],
            }
        )

    cutoffs = (100, 1_000, 10_000, 100_000, 1_000_000)
    all_primes = sieve(max(cutoffs))
    growth = []
    for x in cutoffs:
        ps = [p for p in all_primes if p <= x]
        row = {"prime_cutoff": x, "prime_count": len(ps), "partial_lower_bounds": {}}
        for d in (0, 1, 2, 4):
            for eta in (0.25, 0.5):
                key = f"d={d},eta={eta}"
                row["partial_lower_bounds"][key] = format(lower_sum(ps, d, eta), ".16e")
        growth.append(row)

    report = {
        "schema": "orthogonal-prime-block-obstruction/v1",
        "exact_jet_annihilation": jet_checks,
        "prime_growth_experiment": growth,
        "lower_bound": "(log p)^(d+2) p^(-(1/2+eta))",
        "proof_dependency": "Euler's theorem that sum_p 1/p diverges",
        "scope": {
            "ruled_out": "locally uniform S1-Cauchy orthogonal prime blocks with a uniformly bounded origin-jet order, on a domain meeting 0<Im(z)<=1/2",
            "stronger_relative_resolvent_corollary": "for genuine self-adjoint relative resolvents, the resolvent power identity rules out even pointwise S1-Cauchy convergence at i*eta",
            "not_ruled_out": [
                "nonorthogonal interacting gluing",
                "convergence confined to Im(z)>1/2",
                "unbounded-order origin counterterms",
                "nonsummable absolutely-continuous cancellation",
                "weaker operator topologies",
            ],
        },
        "epistemic_status": {
            "jet_annihilation": "exact rational computation",
            "prime_cutoff_table": "double-precision numerical corroboration",
            "divergence_and_operator_contradiction": "analytic proof in companion note",
        },
    }
    payload = json.dumps(report, sort_keys=True, indent=2) + "\n"
    out = Path(__file__).with_name("prime_block_obstruction_report.json")
    out.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(f"PASS: jet annihilation and prime growth reproduced; report_sha256={digest}")


if __name__ == "__main__":
    main()
