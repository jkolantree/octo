from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .exact import rational, scalar_json
from .findings import Finding, Severity


MAX_DEFECT_STEPS = 256


@dataclass(frozen=True)
class AffineDefect:
    """Composable certificate for a Lipschitz transport with bounded defect.

    `lipschitz` bounds amplification of incoming discrepancy, `epsilon` bounds
    newly introduced discrepancy, and `failure_probability` is an optional
    union-bound budget. The propagation rule is evaluated exactly over the
    rationals; whether the declared bounds model the external system remains a
    separate scientific obligation.
    """

    lipschitz: Fraction
    epsilon: Fraction
    failure_probability: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        if self.lipschitz < 0 or self.epsilon < 0:
            raise ValueError("Lipschitz and defect bounds must be nonnegative")
        if not 0 <= self.failure_probability <= 1:
            raise ValueError("failure probability must lie in [0,1]")

    def then(self, second: "AffineDefect") -> "AffineDefect":
        return AffineDefect(
            second.lipschitz * self.lipschitz,
            second.epsilon + second.lipschitz * self.epsilon,
            min(Fraction(1), self.failure_probability + second.failure_probability),
        )

    def to_dict(self) -> dict[str, int | str]:
        return {
            "lipschitz": scalar_json(self.lipschitz),
            "epsilon": scalar_json(self.epsilon),
            "failure_probability": scalar_json(self.failure_probability),
        }


def load_defect(raw: dict[str, Any]) -> AffineDefect:
    return AffineDefect(
        rational(raw["lipschitz"]),
        rational(raw["epsilon"]),
        rational(raw.get("failure_probability", 0)),
    )


def audit_defect_composition(raw: dict[str, Any]) -> list[Finding]:
    if not isinstance(raw, dict):
        return [Finding(Severity.ERROR, "DEFECT_DOCUMENT_TYPE", "$", "defect document must be a JSON object")]
    steps_raw = raw.get("steps", [])
    if not isinstance(steps_raw, list):
        return [Finding(Severity.ERROR, "DEFECT_STEPS_TYPE", "steps", "steps must be a JSON array")]
    if len(steps_raw) > MAX_DEFECT_STEPS:
        return [Finding(Severity.ERROR, "DEFECT_STEPS_LIMIT", "steps", f"at most {MAX_DEFECT_STEPS} transport steps may be audited in one record")]
    try:
        steps = [load_defect(item) for item in steps_raw]
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return [Finding(Severity.ERROR, "DEFECT_TYPE", "steps", f"invalid affine-defect certificate: {exc}")]
    if not steps:
        return [Finding(Severity.ERROR, "DEFECT_STEPS_MISSING", "steps", "at least one transport certificate is required")]
    result = AffineDefect(Fraction(1), Fraction(0), Fraction(0))
    for step in steps:
        result = result.then(step)
    declared = raw.get("declared_composite")
    if declared is None:
        return [Finding(Severity.INFO, "DEFECT_COMPOSITE", "$", "declared affine upper bounds propagated exactly", witness=result.to_dict())]
    try:
        claimed = load_defect(declared)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return [Finding(Severity.ERROR, "DEFECT_COMPOSITE_TYPE", "declared_composite", f"invalid declared composite: {exc}")]
    if claimed.lipschitz < result.lipschitz or claimed.epsilon < result.epsilon or claimed.failure_probability < result.failure_probability:
        return [
            Finding(
                Severity.DEMOTION,
                "DEFECT_UNDERSTATED",
                "declared_composite",
                "the declared path certificate understates the propagated affine upper bound",
                witness={"required": result.to_dict(), "declared": claimed.to_dict()},
            )
        ]
    return [Finding(Severity.INFO, "DEFECT_COMPOSITE_VALID", "$", "declared composite encloses the exactly propagated affine upper bound", witness=result.to_dict())]
