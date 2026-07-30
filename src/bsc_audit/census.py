from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal

from .exact import rational, scalar_json
from .findings import Finding, Severity
from .provenance import (
    is_placeholder_sha256,
    is_sha256,
    resolve_local_artifact,
    sha256_bytes,
    sha256_json,
)


CERTIFICATE_VERSION = "0.1.0"
LANGUAGE = "finite-census-affine-bound-v0.1"
FIELD = "Q"
CENSUS_GATE_ID = "finite_census_affine_bound"
CENSUS_AUTHORITY = "bsc_conditional_finite_census_exact_replay"
CENSUS_AUTHORITY_SCOPE = "hash_bound_finite_population_observational_bound_only"
CENSUS_PROFILE_SCOPE = (
    "Every declared unit in one closed finite frame, under the supplied exact "
    "measurement enclosures and required guard band."
)

MAX_UNITS = 4096
MAX_OBSERVABLES = 32
MAX_CELLS = 131_072
MAX_CERTIFICATE_BYTES = 4 * 1024 * 1024
MAX_CERTIFICATE_CONTAINER_ITEMS = 420_000
MAX_INTERMEDIATE_BITS = 8192

CLAIM_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,191}$")
UNIT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
OBSERVABLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")

EXTERNAL_PREMISES = {
    "frame_denotes_target_population",
    "unit_identity_authentic",
    "measurement_enclosures_sound",
    "guard_band_scientifically_adequate",
}

ComputedResult = Literal["pass", "fail", "inconclusive"]
UnitBound = tuple[str, Fraction, Fraction]


@dataclass(frozen=True)
class CensusReplay:
    """A deterministic replay of one closed finite-census certificate.

    ``valid`` means the closed certificate was parsed, bound, and replayed
    faithfully. A valid result is still conditional on the four external
    premises identified by hash; this kernel neither establishes those
    premises nor grants causal, generalization, or deployment authority.
    """

    valid: bool
    result: ComputedResult | None
    formal_statement_sha256: str | None
    frame_sha256: str | None
    certificate_semantic_sha256: str | None
    observations_sha256: str | None
    bounds: tuple[UnitBound, ...]
    findings: tuple[Finding, ...]

    def bounds_json(self) -> list[dict[str, object]]:
        return [
            {
                "unit_id": unit_id,
                "lower": scalar_json(lower),
                "upper": scalar_json(upper),
            }
            for unit_id, lower, upper in self.bounds
        ]


class _CertificateError(ValueError):
    def __init__(self, code: str, path: str, message: str):
        super().__init__(message)
        self.code = code
        self.path = path
        self.message = message


def _require_exact_keys(
    value: object,
    required: set[str],
    path: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            path,
            "expected an object",
        )
    keys = set(value)
    if keys != required:
        missing = sorted(required - keys)
        extra = sorted(keys - required)
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            path,
            "object fields do not match the closed contract "
            f"(missing={missing}, extra={extra})",
        )
    return value


def _bounded_fraction(value: Fraction, path: str) -> Fraction:
    if (
        value.numerator.bit_length() > MAX_INTERMEDIATE_BITS
        or value.denominator.bit_length() > MAX_INTERMEDIATE_BITS
    ):
        raise _CertificateError(
            "CENSUS_RESOURCE_LIMIT",
            path,
            f"exact rational intermediate exceeds {MAX_INTERMEDIATE_BITS} bits",
        )
    return value


def _canonical_rational(value: object, path: str) -> Fraction:
    try:
        parsed = rational(value)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            path,
            f"invalid exact rational: {exc}",
        ) from exc
    if scalar_json(parsed) != value:
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            path,
            "rational must use canonical reduced integer or numerator/denominator form",
        )
    return _bounded_fraction(parsed, path)


def _checked_add(left: Fraction, right: Fraction, path: str) -> Fraction:
    return _bounded_fraction(left + right, path)


def _checked_multiply(left: Fraction, right: Fraction, path: str) -> Fraction:
    return _bounded_fraction(left * right, path)


def _normalize_hash(value: object, path: str, *, premise: bool = False) -> str:
    if not is_sha256(value) or (premise and is_placeholder_sha256(value)):
        qualifier = "non-placeholder " if premise else ""
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            path,
            f"expected a {qualifier}sha256 identity",
        )
    assert isinstance(value, str)
    return value


def _normalize_observables(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.formal_statement.observables",
            "observables must be a nonempty list",
        )
    if len(value) > MAX_OBSERVABLES:
        raise _CertificateError(
            "CENSUS_RESOURCE_LIMIT",
            "$.formal_statement.observables",
            f"certificate exceeds the hard limit of {MAX_OBSERVABLES} observables",
        )
    if not all(
        isinstance(name, str) and OBSERVABLE_PATTERN.fullmatch(name)
        for name in value
    ):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.formal_statement.observables",
            "observable names must match the closed identifier grammar",
        )
    if value != sorted(set(value)):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.formal_statement.observables",
            "observables must be unique and strictly lexicographically sorted",
        )
    return list(value)


def _normalize_formal_statement(raw: object) -> dict[str, Any]:
    statement = _require_exact_keys(
        raw,
        {
            "language",
            "field",
            "frame_sha256",
            "observables",
            "coefficients",
            "relation",
            "required_guard_band",
            "external_premises",
        },
        "$.formal_statement",
    )
    if statement["language"] != LANGUAGE:
        raise _CertificateError(
            "CENSUS_CERTIFICATE_LANGUAGE_UNSUPPORTED",
            "$.formal_statement.language",
            f"supported census language is {LANGUAGE!r}",
        )
    if statement["field"] != FIELD:
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.formal_statement.field",
            f"finite-census arithmetic field must be {FIELD!r}",
        )
    frame_sha256 = _normalize_hash(
        statement["frame_sha256"],
        "$.formal_statement.frame_sha256",
    )
    observables = _normalize_observables(statement["observables"])

    coefficients_raw = _require_exact_keys(
        statement["coefficients"],
        set(observables),
        "$.formal_statement.coefficients",
    )
    coefficients = {
        observable: scalar_json(
            _canonical_rational(
                coefficients_raw[observable],
                f"$.formal_statement.coefficients.{observable}",
            )
        )
        for observable in observables
    }

    relation = _require_exact_keys(
        statement["relation"],
        {"op", "bound"},
        "$.formal_statement.relation",
    )
    if relation["op"] != "le":
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.formal_statement.relation.op",
            "the only admitted relation is the affine upper bound 'le'",
        )
    bound = _canonical_rational(
        relation["bound"],
        "$.formal_statement.relation.bound",
    )
    guard = _canonical_rational(
        statement["required_guard_band"],
        "$.formal_statement.required_guard_band",
    )
    if guard <= 0:
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.formal_statement.required_guard_band",
            "required_guard_band must be strictly positive",
        )

    premises_raw = _require_exact_keys(
        statement["external_premises"],
        EXTERNAL_PREMISES,
        "$.formal_statement.external_premises",
    )
    premises = {
        name: _normalize_hash(
            premises_raw[name],
            f"$.formal_statement.external_premises.{name}",
            premise=True,
        )
        for name in sorted(EXTERNAL_PREMISES)
    }
    return {
        "language": LANGUAGE,
        "field": FIELD,
        "frame_sha256": frame_sha256,
        "observables": observables,
        "coefficients": coefficients,
        "relation": {"op": "le", "bound": scalar_json(bound)},
        "required_guard_band": scalar_json(guard),
        "external_premises": premises,
    }


def _normalize_population(raw: object) -> dict[str, Any]:
    population = _require_exact_keys(
        raw,
        {"coverage", "declared_size", "unit_ids"},
        "$.population",
    )
    if population["coverage"] != "census":
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.population.coverage",
            "population coverage must be the closed value 'census'",
        )
    declared_size = population["declared_size"]
    if (
        not isinstance(declared_size, int)
        or isinstance(declared_size, bool)
        or declared_size < 1
    ):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.population.declared_size",
            "declared_size must be a positive integer",
        )
    if declared_size > MAX_UNITS:
        raise _CertificateError(
            "CENSUS_RESOURCE_LIMIT",
            "$.population.declared_size",
            f"certificate exceeds the hard limit of {MAX_UNITS} units",
        )
    unit_ids = population["unit_ids"]
    if not isinstance(unit_ids, list):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.population.unit_ids",
            "unit_ids must be a list",
        )
    if len(unit_ids) > MAX_UNITS:
        raise _CertificateError(
            "CENSUS_RESOURCE_LIMIT",
            "$.population.unit_ids",
            f"certificate exceeds the hard limit of {MAX_UNITS} unit identifiers",
        )
    if not all(
        isinstance(unit_id, str) and UNIT_ID_PATTERN.fullmatch(unit_id)
        for unit_id in unit_ids
    ):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.population.unit_ids",
            "unit identifiers must match the closed identifier grammar",
        )
    if unit_ids != sorted(set(unit_ids)):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.population.unit_ids",
            "unit identifiers must be unique and strictly lexicographically sorted",
        )
    if declared_size != len(unit_ids):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.population.declared_size",
            "declared_size must equal the number of unit identifiers",
        )
    return {
        "coverage": "census",
        "declared_size": declared_size,
        "unit_ids": list(unit_ids),
    }


def _normalize_observations(
    raw: object,
    *,
    unit_ids: list[str],
    observables: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.observations",
            "observations must be a list",
        )
    if len(raw) > MAX_UNITS:
        raise _CertificateError(
            "CENSUS_RESOURCE_LIMIT",
            "$.observations",
            f"certificate exceeds the hard limit of {MAX_UNITS} observations",
        )
    if len(unit_ids) * len(observables) > MAX_CELLS:
        raise _CertificateError(
            "CENSUS_RESOURCE_LIMIT",
            "$.observations",
            f"certificate exceeds the hard limit of {MAX_CELLS} observation cells",
        )

    normalized: list[dict[str, Any]] = []
    observed_ids: list[str] = []
    for index, raw_observation in enumerate(raw):
        path = f"$.observations.{index}"
        observation = _require_exact_keys(
            raw_observation,
            {"unit_id", "intervals"},
            path,
        )
        unit_id = observation["unit_id"]
        if not isinstance(unit_id, str) or not UNIT_ID_PATTERN.fullmatch(unit_id):
            raise _CertificateError(
                "CENSUS_CERTIFICATE_INVALID",
                f"{path}.unit_id",
                "unit identifier does not match the closed identifier grammar",
            )
        intervals_raw = _require_exact_keys(
            observation["intervals"],
            set(observables),
            f"{path}.intervals",
        )
        intervals: dict[str, dict[str, object]] = {}
        for observable in observables:
            interval_path = f"{path}.intervals.{observable}"
            interval = _require_exact_keys(
                intervals_raw[observable],
                {"lower", "upper"},
                interval_path,
            )
            lower = _canonical_rational(
                interval["lower"],
                f"{interval_path}.lower",
            )
            upper = _canonical_rational(
                interval["upper"],
                f"{interval_path}.upper",
            )
            if lower > upper:
                raise _CertificateError(
                    "CENSUS_CERTIFICATE_INVALID",
                    interval_path,
                    "measurement enclosure lower bound exceeds its upper bound",
                )
            intervals[observable] = {
                "lower": scalar_json(lower),
                "upper": scalar_json(upper),
            }
        observed_ids.append(unit_id)
        normalized.append({"unit_id": unit_id, "intervals": intervals})

    if observed_ids != sorted(observed_ids) or len(observed_ids) != len(set(observed_ids)):
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.observations",
            "observations must be unique and strictly sorted by unit_id",
        )
    if observed_ids != unit_ids:
        missing = sorted(set(unit_ids) - set(observed_ids))
        extra = sorted(set(observed_ids) - set(unit_ids))
        raise _CertificateError(
            "CENSUS_CERTIFICATE_INVALID",
            "$.observations",
            "observations must contain exactly one row for every population unit "
            f"(missing={missing[:8]}, extra={extra[:8]})",
        )
    return normalized


def _affine_bounds(
    observations: list[dict[str, Any]],
    statement: dict[str, Any],
) -> tuple[UnitBound, ...]:
    observables = statement["observables"]
    coefficients = {
        name: rational(statement["coefficients"][name])
        for name in observables
    }
    bounds: list[UnitBound] = []
    for observation in observations:
        lower = Fraction(0)
        upper = Fraction(0)
        unit_id = observation["unit_id"]
        for observable in observables:
            coefficient = coefficients[observable]
            interval = observation["intervals"][observable]
            interval_lower = rational(interval["lower"])
            interval_upper = rational(interval["upper"])
            if coefficient >= 0:
                lower_term = _checked_multiply(
                    coefficient,
                    interval_lower,
                    f"$.observations.{unit_id}.intervals.{observable}",
                )
                upper_term = _checked_multiply(
                    coefficient,
                    interval_upper,
                    f"$.observations.{unit_id}.intervals.{observable}",
                )
            else:
                lower_term = _checked_multiply(
                    coefficient,
                    interval_upper,
                    f"$.observations.{unit_id}.intervals.{observable}",
                )
                upper_term = _checked_multiply(
                    coefficient,
                    interval_lower,
                    f"$.observations.{unit_id}.intervals.{observable}",
                )
            lower = _checked_add(
                lower,
                lower_term,
                f"$.observations.{unit_id}",
            )
            upper = _checked_add(
                upper,
                upper_term,
                f"$.observations.{unit_id}",
            )
        bounds.append((unit_id, lower, upper))
    return tuple(bounds)


def _render_rational(value: object) -> str:
    parsed = rational(value)
    rendered = str(scalar_json(parsed))
    return rendered if parsed >= 0 else f"({rendered})"


def _render_title(_statement: dict[str, Any]) -> str:
    return "Finite-census affine upper bound in Q"


def _render_statement(statement: dict[str, Any]) -> str:
    terms = [
        f"{_render_rational(statement['coefficients'][name])}*{name}"
        for name in statement["observables"]
    ]
    return (
        f"Q finite census frame {statement['frame_sha256']}: for every unit, "
        f"({' + '.join(terms)}) <= "
        f"{_render_rational(statement['relation']['bound'])}; "
        "required_guard_band="
        f"{_render_rational(statement['required_guard_band'])}"
    )


def canonical_formal_title(raw: object) -> str:
    """Return the deterministic title for a valid closed census statement."""

    return _render_title(_normalize_formal_statement(raw))


def canonical_formal_statement(raw: object) -> str:
    """Render only the exact statement admitted by the closed census grammar."""

    return _render_statement(_normalize_formal_statement(raw))


def _conclusion_witness(
    *,
    claim_id: str,
    statement: dict[str, Any],
    statement_sha256: str,
    certificate_semantic_sha256: str,
    observations_sha256: str,
    result: ComputedResult,
    bounds: tuple[UnitBound, ...],
) -> dict[str, object]:
    if result == "pass":
        observational_truth = "established_conditionally"
    elif result == "fail":
        observational_truth = "refuted_conditionally"
    else:
        observational_truth = "not_established"
    return {
        "subject": {
            "claim_id": claim_id,
            "frame_sha256": statement["frame_sha256"],
        },
        "scope": CENSUS_PROFILE_SCOPE,
        "method": {
            "id": CENSUS_GATE_ID,
            "language": LANGUAGE,
            "field": FIELD,
            "actual_execution": "exact_fraction_interval_replay_performed",
        },
        "evidence_identity": {
            "certificate_semantic_sha256": certificate_semantic_sha256,
            "formal_statement_sha256": statement_sha256,
            "frame_sha256": statement["frame_sha256"],
            "observations_sha256": observations_sha256,
            "external_premises": statement["external_premises"],
        },
        "evidence_premises": {
            "status": "hash_identified_not_established_by_this_kernel",
            "required": sorted(EXTERNAL_PREMISES),
        },
        "authority": {
            "id": CENSUS_AUTHORITY,
            "scope": CENSUS_AUTHORITY_SCOPE,
        },
        "result": result,
        "units_replayed": len(bounds),
        "observational_truth": observational_truth,
        "observational_truth_condition": (
            "all four hash-identified external premises hold"
        ),
        "causal_truth": "not_granted",
        "generalization_beyond_frame": "not_granted",
        "transport_behavior": "not_evaluated",
        "deployment_authority": "not_granted",
        "canonical_formal_title": _render_title(statement),
        "canonical_formal_statement": _render_statement(statement),
    }


def _invalid_replay(error: _CertificateError) -> CensusReplay:
    return CensusReplay(
        valid=False,
        result=None,
        formal_statement_sha256=None,
        frame_sha256=None,
        certificate_semantic_sha256=None,
        observations_sha256=None,
        bounds=(),
        findings=(
            Finding(
                Severity.ERROR,
                error.code,
                error.path,
                error.message,
            ),
        ),
    )


def replay_census_certificate(
    raw: object,
    *,
    expected_claim_id: str | None = None,
    expected_formal_statement: object | None = None,
) -> CensusReplay:
    """Replay a closed finite census using exact rational interval arithmetic."""

    try:
        certificate = _require_exact_keys(
            raw,
            {
                "certificate_version",
                "claim_id",
                "formal_statement",
                "population",
                "observations",
                "declared_result",
            },
            "$",
        )
        if certificate["certificate_version"] != CERTIFICATE_VERSION:
            raise _CertificateError(
                "CENSUS_CERTIFICATE_VERSION_UNSUPPORTED",
                "$.certificate_version",
                f"supported census certificate version is {CERTIFICATE_VERSION!r}",
            )
        claim_id = certificate["claim_id"]
        if not isinstance(claim_id, str) or not CLAIM_ID_PATTERN.fullmatch(claim_id):
            raise _CertificateError(
                "CENSUS_CERTIFICATE_INVALID",
                "$.claim_id",
                "claim identifier does not match the closed identifier grammar",
            )
        statement = _normalize_formal_statement(certificate["formal_statement"])
        statement_hash = sha256_json(statement)
        population = _normalize_population(certificate["population"])
        frame_hash = sha256_json(population)
        if statement["frame_sha256"] != frame_hash:
            raise _CertificateError(
                "CENSUS_FRAME_HASH_MISMATCH",
                "$.formal_statement.frame_sha256",
                "formal statement frame hash does not equal sha256_json(population)",
            )
        observations = _normalize_observations(
            certificate["observations"],
            unit_ids=population["unit_ids"],
            observables=statement["observables"],
        )
        bounds = _affine_bounds(observations, statement)
        bound = rational(statement["relation"]["bound"])
        guard = rational(statement["required_guard_band"])
        guarded_bounds = tuple(
            (
                unit_id,
                lower,
                upper,
                _checked_add(
                    upper,
                    guard,
                    f"$.observations[{index}].upper_plus_guard_band",
                ),
            )
            for index, (unit_id, lower, upper) in enumerate(bounds)
        )
        if all(upper_with_guard <= bound for _, _, _, upper_with_guard in guarded_bounds):
            result: ComputedResult = "pass"
        elif any(lower > bound for _, lower, _ in bounds):
            result = "fail"
        else:
            result = "inconclusive"

        declared_result = certificate["declared_result"]
        if declared_result not in {"pass", "fail", "inconclusive"}:
            raise _CertificateError(
                "CENSUS_CERTIFICATE_INVALID",
                "$.declared_result",
                "declared_result must be pass, fail, or inconclusive",
            )
        if declared_result != result:
            raise _CertificateError(
                "CENSUS_CERTIFICATE_RESULT_MISMATCH",
                "$.declared_result",
                "declared_result does not equal the exact census replay result",
            )
        observations_hash = sha256_json(observations)
        certificate_semantic_hash = sha256_json(
            {
                "certificate_version": CERTIFICATE_VERSION,
                "claim_id": claim_id,
                "formal_statement": statement,
                "population": population,
                "observations": observations,
                "declared_result": declared_result,
            }
        )
        if expected_claim_id is not None and claim_id != expected_claim_id:
            finding = Finding(
                Severity.BLOCKED,
                "CENSUS_CERTIFICATE_CLAIM_MISMATCH",
                "$.claim_id",
                "certificate claim identifier does not match the expected claim",
                witness={"declared": claim_id, "expected": expected_claim_id},
            )
            return CensusReplay(
                valid=False,
                result=None,
                formal_statement_sha256=statement_hash,
                frame_sha256=frame_hash,
                certificate_semantic_sha256=certificate_semantic_hash,
                observations_sha256=observations_hash,
                bounds=bounds,
                findings=(finding,),
            )
        if expected_formal_statement is not None:
            try:
                expected_statement = _normalize_formal_statement(
                    expected_formal_statement
                )
                expected_hash = sha256_json(expected_statement)
            except _CertificateError:
                expected_statement = None
                expected_hash = None
            if statement != expected_statement:
                finding = Finding(
                    Severity.BLOCKED,
                    "CENSUS_CERTIFICATE_STATEMENT_MISMATCH",
                    "$.formal_statement",
                    "certificate formal statement does not match the expected statement",
                    witness={
                        "certificate_sha256": statement_hash,
                        "expected_sha256": expected_hash,
                    },
                )
                return CensusReplay(
                    valid=False,
                    result=None,
                    formal_statement_sha256=statement_hash,
                    frame_sha256=frame_hash,
                    certificate_semantic_sha256=certificate_semantic_hash,
                    observations_sha256=observations_hash,
                    bounds=bounds,
                    findings=(finding,),
                )
    except _CertificateError as error:
        return _invalid_replay(error)

    witness = _conclusion_witness(
        claim_id=claim_id,
        statement=statement,
        statement_sha256=statement_hash,
        certificate_semantic_sha256=certificate_semantic_hash,
        observations_sha256=observations_hash,
        result=result,
        bounds=bounds,
    )
    if result == "pass":
        finding = Finding(
            Severity.INFO,
            "CENSUS_BOUND_REPLAYED",
            "$.observations",
            "every affine enclosure upper bound plus the required guard band "
            "is at or below the declared bound",
            witness=witness,
        )
    elif result == "fail":
        counterexamples = [
            {
                "unit_id": unit_id,
                "lower": scalar_json(lower),
                "bound": scalar_json(bound),
            }
            for unit_id, lower, _ in bounds
            if lower > bound
        ]
        finding = Finding(
            Severity.DEMOTION,
            "CENSUS_BOUND_REFUTED",
            "$.observations",
            "at least one affine enclosure lies strictly above the declared bound",
            witness={
                **witness,
                "counterexample_count": len(counterexamples),
                "first_counterexample": counterexamples[0],
            },
        )
    else:
        unresolved = [
            {
                "unit_id": unit_id,
                "lower": scalar_json(lower),
                "upper": scalar_json(upper),
                "upper_plus_guard_band": scalar_json(upper_with_guard),
                "bound": scalar_json(bound),
            }
            for unit_id, lower, upper, upper_with_guard in guarded_bounds
            if not upper_with_guard <= bound and not lower > bound
        ]
        finding = Finding(
            Severity.BLOCKED,
            "CENSUS_BOUND_INCONCLUSIVE",
            "$.observations",
            "the exact enclosures neither establish the guard-banded upper "
            "bound nor refute the unguarded bound",
            witness={
                **witness,
                "unresolved_count": len(unresolved),
                "first_unresolved": unresolved[0],
            },
        )
    return CensusReplay(
        valid=True,
        result=result,
        formal_statement_sha256=statement_hash,
        frame_sha256=frame_hash,
        certificate_semantic_sha256=certificate_semantic_hash,
        observations_sha256=observations_hash,
        bounds=bounds,
        findings=(finding,),
    )


def _loader_failure(
    severity: Severity,
    code: str,
    message: str,
    *,
    witness: object | None = None,
) -> CensusReplay:
    return CensusReplay(
        valid=False,
        result=None,
        formal_statement_sha256=None,
        frame_sha256=None,
        certificate_semantic_sha256=None,
        observations_sha256=None,
        bounds=(),
        findings=(
            Finding(
                severity,
                code,
                "$",
                message,
                witness=witness,
            ),
        ),
    )


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        value[key] = item
    return value


def load_and_replay_census_certificate(
    artifact_root: Path | None,
    relative_path: object,
    *,
    expected_sha256: object | None = None,
    expected_claim_id: str | None = None,
    expected_formal_statement: object | None = None,
) -> CensusReplay:
    """Load, hash, parse, and replay one local certificate from one byte buffer."""

    if artifact_root is None:
        return _loader_failure(
            Severity.BLOCKED,
            "CENSUS_CERTIFICATE_UNAVAILABLE",
            "census replay requires an explicit local artifact root",
            witness={"reason": "artifact_root_unavailable"},
        )
    try:
        path = resolve_local_artifact(artifact_root, relative_path)
    except (ValueError, OSError, RuntimeError):
        return _loader_failure(
            Severity.ERROR,
            "CENSUS_CERTIFICATE_PATH_UNSAFE",
            "the census certificate path must remain below the artifact root",
        )
    if not path.is_file():
        return _loader_failure(
            Severity.BLOCKED,
            "CENSUS_CERTIFICATE_UNAVAILABLE",
            "the local census certificate is missing",
            witness={"reason": "missing_artifact"},
        )
    try:
        size = path.stat().st_size
    except OSError:
        return _loader_failure(
            Severity.BLOCKED,
            "CENSUS_CERTIFICATE_UNAVAILABLE",
            "the local census certificate could not be inspected",
            witness={"reason": "unreadable_artifact"},
        )
    if size > MAX_CERTIFICATE_BYTES:
        return _loader_failure(
            Severity.ERROR,
            "CENSUS_RESOURCE_LIMIT",
            f"census certificate exceeds {MAX_CERTIFICATE_BYTES} bytes",
        )
    try:
        with path.open("rb") as stream:
            payload = stream.read(MAX_CERTIFICATE_BYTES + 1)
        if len(payload) > MAX_CERTIFICATE_BYTES:
            return _loader_failure(
                Severity.ERROR,
                "CENSUS_RESOURCE_LIMIT",
                f"census certificate exceeds {MAX_CERTIFICATE_BYTES} bytes",
            )
        if expected_sha256 is not None:
            if not is_sha256(expected_sha256):
                return _loader_failure(
                    Severity.ERROR,
                    "CENSUS_CERTIFICATE_HASH_INVALID",
                    "the expected census-certificate hash is malformed",
                )
            actual_sha256 = sha256_bytes(payload)
            if actual_sha256 != expected_sha256:
                return _loader_failure(
                    Severity.BLOCKED,
                    "CENSUS_CERTIFICATE_BYTES_CHANGED",
                    "census certificate bytes changed between artifact "
                    "verification and replay",
                    witness={
                        "expected_sha256": expected_sha256,
                        "actual_sha256": actual_sha256,
                    },
                )
        text = payload.decode("utf-8")
        raw = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except OSError:
        return _loader_failure(
            Severity.BLOCKED,
            "CENSUS_CERTIFICATE_UNAVAILABLE",
            "the local census certificate could not be read",
            witness={"reason": "unreadable_artifact"},
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        return _loader_failure(
            Severity.ERROR,
            "CENSUS_CERTIFICATE_INVALID",
            "the census certificate must be strict UTF-8 JSON with unique keys",
        )
    return replay_census_certificate(
        raw,
        expected_claim_id=expected_claim_id,
        expected_formal_statement=expected_formal_statement,
    )


def audit_census_certificate(
    raw: dict[str, Any],
    _artifact_root: Path | None = None,
) -> list[Finding]:
    """CLI-compatible finite-census certificate auditor."""

    return list(replay_census_certificate(raw).findings)
