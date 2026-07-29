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
    is_sha256,
    resolve_local_artifact,
    sha256_bytes,
    sha256_json,
)


CERTIFICATE_VERSION = "0.1.0"
LANGUAGE = "q-polynomial-identity-v0.1"
FIELD = "Q"
THEOREM_GATE_ID = "exact_polynomial_identity"

MAX_VARIABLES = 8
MAX_AST_DEPTH = 32
MAX_AST_NODES = 256
MAX_ARITY = 16
MAX_EXPONENT = 16
MAX_MONOMIALS = 4096
MAX_INTERMEDIATE_BITS = 8192
MAX_ARITHMETIC_OPS = 50_000
MAX_CERTIFICATE_BYTES = 1024 * 1024

CLAIM_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,191}$")
VARIABLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")

Monomial = tuple[int, ...]
Polynomial = dict[Monomial, Fraction]
ComputedResult = Literal["pass", "fail"]


@dataclass(frozen=True)
class TheoremReplay:
    """A deterministic replay result.

    ``valid`` distinguishes a well-formed, faithfully replayed certificate from
    an invalid or mismatched certificate. ``result`` is populated only for a
    valid replay: ``pass`` means the exact residual is zero and ``fail`` means
    the supplied formal identity has a nonzero exact residual.
    """

    valid: bool
    result: ComputedResult | None
    formal_statement_sha256: str | None
    residual: tuple[tuple[Monomial, Fraction], ...]
    findings: tuple[Finding, ...]

    def residual_json(self) -> list[dict[str, object]]:
        return _residual_json(dict(self.residual))


class _CertificateError(ValueError):
    def __init__(self, code: str, path: str, message: str, *, resource: bool = False):
        super().__init__(message)
        self.code = code
        self.path = path
        self.message = message
        self.resource = resource


@dataclass
class _Budget:
    nodes: int = 0
    arithmetic_ops: int = 0

    def visit(self, depth: int) -> None:
        if depth > MAX_AST_DEPTH:
            raise _CertificateError(
                "THEOREM_RESOURCE_LIMIT",
                "$.formal_statement.relation",
                f"term nesting exceeds {MAX_AST_DEPTH}",
                resource=True,
            )
        self.nodes += 1
        if self.nodes > MAX_AST_NODES:
            raise _CertificateError(
                "THEOREM_RESOURCE_LIMIT",
                "$.formal_statement.relation",
                f"term tree exceeds {MAX_AST_NODES} nodes",
                resource=True,
            )

    def consume_arithmetic(self, amount: int, path: str) -> None:
        if self.arithmetic_ops + amount > MAX_ARITHMETIC_OPS:
            raise _CertificateError(
                "THEOREM_RESOURCE_LIMIT",
                path,
                f"exact normalization exceeds {MAX_ARITHMETIC_OPS} arithmetic operations",
                resource=True,
            )
        self.arithmetic_ops += amount


def _require_exact_keys(value: object, required: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _CertificateError("THEOREM_CERTIFICATE_INVALID", path, "expected an object")
    keys = set(value)
    if keys != required:
        missing = sorted(required - keys)
        extra = sorted(keys - required)
        raise _CertificateError(
            "THEOREM_CERTIFICATE_INVALID",
            path,
            f"object fields do not match the closed contract (missing={missing}, extra={extra})",
        )
    return value


def _bounded_fraction(value: Fraction, path: str) -> Fraction:
    if (
        value.numerator.bit_length() > MAX_INTERMEDIATE_BITS
        or value.denominator.bit_length() > MAX_INTERMEDIATE_BITS
    ):
        raise _CertificateError(
            "THEOREM_RESOURCE_LIMIT",
            path,
            f"exact rational intermediate exceeds {MAX_INTERMEDIATE_BITS} bits",
            resource=True,
        )
    return value


def _canonical_rational(value: object, path: str) -> Fraction:
    try:
        parsed = rational(value)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise _CertificateError(
            "THEOREM_CERTIFICATE_INVALID",
            path,
            f"invalid exact rational: {exc}",
        ) from exc
    if scalar_json(parsed) != value:
        raise _CertificateError(
            "THEOREM_CERTIFICATE_INVALID",
            path,
            "rational must use canonical reduced integer or numerator/denominator form",
        )
    return _bounded_fraction(parsed, path)


def _bounded_polynomial(polynomial: Polynomial, path: str) -> Polynomial:
    cleaned = {
        monomial: _bounded_fraction(coefficient, path)
        for monomial, coefficient in polynomial.items()
        if coefficient != 0
    }
    if len(cleaned) > MAX_MONOMIALS:
        raise _CertificateError(
            "THEOREM_RESOURCE_LIMIT",
            path,
            f"expanded normal form exceeds {MAX_MONOMIALS} monomials",
            resource=True,
        )
    return cleaned


def _add(
    left: Polynomial,
    right: Polynomial,
    path: str,
    budget: _Budget,
) -> Polynomial:
    result = dict(left)
    for monomial, coefficient in right.items():
        budget.consume_arithmetic(1, path)
        result[monomial] = _bounded_fraction(
            result.get(monomial, Fraction(0)) + coefficient,
            path,
        )
    return _bounded_polynomial(result, path)


def _negate(value: Polynomial, path: str, budget: _Budget) -> Polynomial:
    budget.consume_arithmetic(len(value), path)
    return _bounded_polynomial(
        {monomial: _bounded_fraction(-coefficient, path) for monomial, coefficient in value.items()},
        path,
    )


def _multiply(
    left: Polynomial,
    right: Polynomial,
    path: str,
    budget: _Budget,
) -> Polynomial:
    result: Polynomial = {}
    for left_monomial, left_coefficient in left.items():
        for right_monomial, right_coefficient in right.items():
            # Count the exact coefficient multiplication and accumulation before
            # performing either operation. This closes compact exponent-tree
            # inputs that otherwise expand into minutes of deterministic work
            # while remaining below the AST and monomial-count ceilings.
            budget.consume_arithmetic(2, path)
            monomial = tuple(
                left_power + right_power
                for left_power, right_power in zip(left_monomial, right_monomial)
            )
            product = _bounded_fraction(left_coefficient * right_coefficient, path)
            result[monomial] = _bounded_fraction(
                result.get(monomial, Fraction(0)) + product,
                path,
            )
            if len(result) > MAX_MONOMIALS:
                raise _CertificateError(
                    "THEOREM_RESOURCE_LIMIT",
                    path,
                    f"expanded normal form exceeds {MAX_MONOMIALS} monomials",
                    resource=True,
                )
    return _bounded_polynomial(result, path)


def _power(
    base: Polynomial,
    exponent: int,
    variable_count: int,
    path: str,
    budget: _Budget,
) -> Polynomial:
    result: Polynomial = {(0,) * variable_count: Fraction(1)}
    factor = base
    remaining = exponent
    while remaining:
        if remaining & 1:
            result = _multiply(result, factor, path, budget)
        remaining //= 2
        if remaining:
            factor = _multiply(factor, factor, path, budget)
    return result


def _normalize_term(
    raw: object,
    variables: dict[str, int],
    budget: _Budget,
    path: str,
    depth: int = 0,
) -> Polynomial:
    budget.visit(depth)
    if not isinstance(raw, dict):
        raise _CertificateError("THEOREM_CERTIFICATE_INVALID", path, "term must be an object")
    op = raw.get("op")
    variable_count = len(variables)
    zero = (0,) * variable_count

    if op == "const":
        term = _require_exact_keys(raw, {"op", "value"}, path)
        value = _canonical_rational(term["value"], f"{path}.value")
        return {} if value == 0 else {zero: value}

    if op == "var":
        term = _require_exact_keys(raw, {"op", "name"}, path)
        name = term["name"]
        if not isinstance(name, str) or name not in variables:
            raise _CertificateError(
                "THEOREM_CERTIFICATE_INVALID",
                f"{path}.name",
                "variable must be declared by the formal statement",
            )
        powers = [0] * variable_count
        powers[variables[name]] = 1
        return {tuple(powers): Fraction(1)}

    if op == "neg":
        term = _require_exact_keys(raw, {"op", "arg"}, path)
        return _negate(
            _normalize_term(term["arg"], variables, budget, f"{path}.arg", depth + 1),
            path,
            budget,
        )

    if op in {"add", "mul"}:
        term = _require_exact_keys(raw, {"op", "args"}, path)
        args = term["args"]
        if not isinstance(args, list) or not 2 <= len(args) <= MAX_ARITY:
            raise _CertificateError(
                "THEOREM_RESOURCE_LIMIT" if isinstance(args, list) and len(args) > MAX_ARITY else "THEOREM_CERTIFICATE_INVALID",
                f"{path}.args",
                f"{op} requires between 2 and {MAX_ARITY} arguments",
                resource=isinstance(args, list) and len(args) > MAX_ARITY,
            )
        if op == "add":
            result: Polynomial = {}
            for index, arg in enumerate(args):
                result = _add(
                    result,
                    _normalize_term(arg, variables, budget, f"{path}.args.{index}", depth + 1),
                    path,
                    budget,
                )
            return result
        result = {zero: Fraction(1)}
        for index, arg in enumerate(args):
            result = _multiply(
                result,
                _normalize_term(arg, variables, budget, f"{path}.args.{index}", depth + 1),
                path,
                budget,
            )
        return result

    if op == "pow":
        term = _require_exact_keys(raw, {"op", "base", "exponent"}, path)
        exponent = term["exponent"]
        if (
            not isinstance(exponent, int)
            or isinstance(exponent, bool)
            or exponent < 0
            or exponent > MAX_EXPONENT
        ):
            code = (
                "THEOREM_RESOURCE_LIMIT"
                if isinstance(exponent, int)
                and not isinstance(exponent, bool)
                and exponent > MAX_EXPONENT
                else "THEOREM_CERTIFICATE_INVALID"
            )
            raise _CertificateError(
                code,
                f"{path}.exponent",
                f"exponent must be an integer in [0,{MAX_EXPONENT}]",
                resource=code == "THEOREM_RESOURCE_LIMIT",
            )
        base = _normalize_term(term["base"], variables, budget, f"{path}.base", depth + 1)
        return _power(base, exponent, variable_count, path, budget)

    raise _CertificateError(
        "THEOREM_CERTIFICATE_INVALID",
        f"{path}.op",
        "operator must be one of const, var, neg, add, mul, or pow",
    )


def _normalize_statement(raw: object) -> tuple[dict[str, Any], Polynomial]:
    statement = _require_exact_keys(
        raw,
        {"language", "field", "variables", "relation"},
        "$.formal_statement",
    )
    if statement["language"] != LANGUAGE:
        raise _CertificateError(
            "THEOREM_LANGUAGE_NOT_ADMISSIBLE",
            "$.formal_statement.language",
            f"only {LANGUAGE!r} is admissible",
        )
    if statement["field"] != FIELD:
        raise _CertificateError(
            "THEOREM_LANGUAGE_NOT_ADMISSIBLE",
            "$.formal_statement.field",
            "the exact polynomial kernel is defined only over Q",
        )
    variable_values = statement["variables"]
    if not isinstance(variable_values, list):
        raise _CertificateError(
            "THEOREM_CERTIFICATE_INVALID",
            "$.formal_statement.variables",
            "variables must be a list",
        )
    if len(variable_values) > MAX_VARIABLES:
        raise _CertificateError(
            "THEOREM_RESOURCE_LIMIT",
            "$.formal_statement.variables",
            f"formal statement exceeds {MAX_VARIABLES} variables",
            resource=True,
        )
    if not all(isinstance(value, str) and VARIABLE_PATTERN.fullmatch(value) for value in variable_values):
        raise _CertificateError(
            "THEOREM_CERTIFICATE_INVALID",
            "$.formal_statement.variables",
            "variable names must match the closed identifier grammar",
        )
    if len(variable_values) != len(set(variable_values)):
        raise _CertificateError(
            "THEOREM_CERTIFICATE_INVALID",
            "$.formal_statement.variables",
            "variable names must be unique",
        )
    if variable_values != sorted(variable_values):
        raise _CertificateError(
            "THEOREM_CERTIFICATE_INVALID",
            "$.formal_statement.variables",
            "variable names must be lexicographically sorted",
        )
    variables = {name: index for index, name in enumerate(variable_values)}

    relation = _require_exact_keys(
        statement["relation"],
        {"op", "left", "right"},
        "$.formal_statement.relation",
    )
    if relation["op"] != "eq":
        raise _CertificateError(
            "THEOREM_LANGUAGE_NOT_ADMISSIBLE",
            "$.formal_statement.relation.op",
            "the v0.1 theorem kernel admits polynomial equality only",
        )
    budget = _Budget()
    left = _normalize_term(
        relation["left"],
        variables,
        budget,
        "$.formal_statement.relation.left",
    )
    right = _normalize_term(
        relation["right"],
        variables,
        budget,
        "$.formal_statement.relation.right",
    )
    residual = _add(
        left,
        _negate(right, "$.formal_statement.relation.right", budget),
        "$.formal_statement.relation",
        budget,
    )
    return statement, residual


def _residual_json(polynomial: Polynomial) -> list[dict[str, object]]:
    return [
        {"powers": list(monomial), "coefficient": scalar_json(coefficient)}
        for monomial, coefficient in sorted(polynomial.items())
    ]


def _parse_declared_residual(
    raw: object,
    variable_count: int,
) -> Polynomial:
    if not isinstance(raw, list):
        raise _CertificateError(
            "THEOREM_CERTIFICATE_INVALID",
            "$.residual",
            "residual must be a canonical sparse-polynomial list",
        )
    if len(raw) > MAX_MONOMIALS:
        raise _CertificateError(
            "THEOREM_RESOURCE_LIMIT",
            "$.residual",
            f"declared residual exceeds {MAX_MONOMIALS} monomials",
            resource=True,
        )
    result: Polynomial = {}
    previous: Monomial | None = None
    for index, item in enumerate(raw):
        path = f"$.residual.{index}"
        record = _require_exact_keys(item, {"powers", "coefficient"}, path)
        powers = record["powers"]
        if (
            not isinstance(powers, list)
            or len(powers) != variable_count
            or not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in powers)
        ):
            raise _CertificateError(
                "THEOREM_CERTIFICATE_INVALID",
                f"{path}.powers",
                "power vector must contain one nonnegative integer per declared variable",
            )
        monomial = tuple(powers)
        if previous is not None and monomial <= previous:
            raise _CertificateError(
                "THEOREM_CERTIFICATE_INVALID",
                "$.residual",
                "residual monomials must be unique and strictly lexicographically sorted",
            )
        coefficient = _canonical_rational(record["coefficient"], f"{path}.coefficient")
        if coefficient == 0:
            raise _CertificateError(
                "THEOREM_CERTIFICATE_INVALID",
                f"{path}.coefficient",
                "zero coefficients must be omitted from canonical residuals",
            )
        result[monomial] = coefficient
        previous = monomial
    return result


def _invalid_replay(error: _CertificateError) -> TheoremReplay:
    return TheoremReplay(
        valid=False,
        result=None,
        formal_statement_sha256=None,
        residual=(),
        findings=(
            Finding(
                Severity.ERROR,
                error.code,
                error.path,
                error.message,
            ),
        ),
    )


def replay_theorem_certificate(
    raw: object,
    *,
    expected_claim_id: str | None = None,
    expected_formal_statement: object | None = None,
) -> TheoremReplay:
    """Strictly replay a closed exact-Q polynomial identity certificate.

    This proves or refutes only the supplied formal polynomial identity. It does
    not interpret free-form prose, validate scientific declarations, execute an
    external prover, or grant deployment authority.
    """

    try:
        certificate = _require_exact_keys(
            raw,
            {"certificate_version", "claim_id", "formal_statement", "residual"},
            "$",
        )
        if certificate["certificate_version"] != CERTIFICATE_VERSION:
            raise _CertificateError(
                "THEOREM_CERTIFICATE_VERSION_UNSUPPORTED",
                "$.certificate_version",
                f"supported theorem certificate version is {CERTIFICATE_VERSION!r}",
            )
        claim_id = certificate["claim_id"]
        if not isinstance(claim_id, str) or not CLAIM_ID_PATTERN.fullmatch(claim_id):
            raise _CertificateError(
                "THEOREM_CERTIFICATE_INVALID",
                "$.claim_id",
                "claim identifier does not match the closed identifier grammar",
            )
        formal_statement, computed_residual = _normalize_statement(certificate["formal_statement"])
        statement_hash = sha256_json(formal_statement)
        declared_residual = _parse_declared_residual(
            certificate["residual"],
            len(formal_statement["variables"]),
        )
        if declared_residual != computed_residual:
            raise _CertificateError(
                "THEOREM_CERTIFICATE_RESIDUAL_MISMATCH",
                "$.residual",
                "declared residual does not equal the exact normal form of left minus right",
            )
        if expected_claim_id is not None and claim_id != expected_claim_id:
            finding = Finding(
                Severity.BLOCKED,
                "THEOREM_CERTIFICATE_CLAIM_MISMATCH",
                "$.claim_id",
                "certificate claim identifier does not match the manifest claim",
                witness={"declared": claim_id, "expected": expected_claim_id},
            )
            return TheoremReplay(False, None, statement_hash, tuple(sorted(computed_residual.items())), (finding,))
        if expected_formal_statement is not None and formal_statement != expected_formal_statement:
            try:
                expected_hash = sha256_json(expected_formal_statement)
            except (TypeError, ValueError):
                expected_hash = None
            finding = Finding(
                Severity.BLOCKED,
                "THEOREM_CERTIFICATE_STATEMENT_MISMATCH",
                "$.formal_statement",
                "certificate formal statement does not match the authoritative manifest statement",
                witness={
                    "certificate_sha256": statement_hash,
                    "manifest_sha256": expected_hash,
                },
            )
            return TheoremReplay(False, None, statement_hash, tuple(sorted(computed_residual.items())), (finding,))
    except _CertificateError as error:
        return _invalid_replay(error)

    result: ComputedResult = "pass" if not computed_residual else "fail"
    if result == "pass":
        finding = Finding(
            Severity.INFO,
            "THEOREM_IDENTITY_REPLAYED",
            "$.formal_statement",
            "exact normalization proved the supplied polynomial identity in Q[variables]",
            witness={
                "kernel": LANGUAGE,
                "formal_statement_sha256": statement_hash,
                "residual_terms": 0,
            },
        )
    else:
        residual_json = _residual_json(computed_residual)
        finding = Finding(
            Severity.DEMOTION,
            "THEOREM_IDENTITY_REFUTED",
            "$.formal_statement",
            "exact normalization produced a nonzero polynomial residual",
            witness={
                "kernel": LANGUAGE,
                "formal_statement_sha256": statement_hash,
                "residual_terms": len(residual_json),
                "first_residual_term": residual_json[0],
            },
        )
    return TheoremReplay(
        valid=True,
        result=result,
        formal_statement_sha256=statement_hash,
        residual=tuple(sorted(computed_residual.items())),
        findings=(finding,),
    )


def _loader_failure(
    severity: Severity,
    code: str,
    message: str,
    *,
    witness: object | None = None,
) -> TheoremReplay:
    return TheoremReplay(
        valid=False,
        result=None,
        formal_statement_sha256=None,
        residual=(),
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


def load_and_replay_theorem_certificate(
    artifact_root: Path | None,
    relative_path: object,
    *,
    expected_sha256: object | None = None,
    expected_claim_id: str | None = None,
    expected_formal_statement: object | None = None,
) -> TheoremReplay:
    """Strictly load one local certificate and replay it under the closed kernel."""

    if artifact_root is None:
        return _loader_failure(
            Severity.BLOCKED,
            "THEOREM_CERTIFICATE_UNAVAILABLE",
            "theorem replay requires an explicit local artifact root",
            witness={"reason": "artifact_root_unavailable"},
        )
    try:
        path = resolve_local_artifact(artifact_root, relative_path)
    except (ValueError, OSError, RuntimeError):
        return _loader_failure(
            Severity.ERROR,
            "THEOREM_CERTIFICATE_PATH_UNSAFE",
            "the theorem certificate path must remain below the manifest directory",
        )
    if not path.is_file():
        return _loader_failure(
            Severity.BLOCKED,
            "THEOREM_CERTIFICATE_UNAVAILABLE",
            "the local theorem certificate is missing",
            witness={"reason": "missing_artifact"},
        )
    try:
        size = path.stat().st_size
    except OSError:
        return _loader_failure(
            Severity.BLOCKED,
            "THEOREM_CERTIFICATE_UNAVAILABLE",
            "the local theorem certificate could not be inspected",
            witness={"reason": "unreadable_artifact"},
        )
    if size > MAX_CERTIFICATE_BYTES:
        return _loader_failure(
            Severity.ERROR,
            "THEOREM_RESOURCE_LIMIT",
            f"theorem certificate exceeds {MAX_CERTIFICATE_BYTES} bytes",
        )
    try:
        with path.open("rb") as stream:
            payload = stream.read(MAX_CERTIFICATE_BYTES + 1)
        if len(payload) > MAX_CERTIFICATE_BYTES:
            return _loader_failure(
                Severity.ERROR,
                "THEOREM_RESOURCE_LIMIT",
                f"theorem certificate exceeds {MAX_CERTIFICATE_BYTES} bytes",
            )
        if expected_sha256 is not None:
            if not is_sha256(expected_sha256):
                return _loader_failure(
                    Severity.ERROR,
                    "THEOREM_CERTIFICATE_HASH_INVALID",
                    "the expected theorem-certificate hash is malformed",
                )
            actual_sha256 = sha256_bytes(payload)
            if actual_sha256 != expected_sha256:
                return _loader_failure(
                    Severity.BLOCKED,
                    "THEOREM_CERTIFICATE_BYTES_CHANGED",
                    "theorem certificate bytes changed between artifact verification and replay",
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
            "THEOREM_CERTIFICATE_UNAVAILABLE",
            "the local theorem certificate could not be read",
            witness={"reason": "unreadable_artifact"},
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        return _loader_failure(
            Severity.ERROR,
            "THEOREM_CERTIFICATE_INVALID",
            "the theorem certificate must be strict UTF-8 JSON with unique keys",
        )
    return replay_theorem_certificate(
        raw,
        expected_claim_id=expected_claim_id,
        expected_formal_statement=expected_formal_statement,
    )


def audit_theorem_certificate(
    raw: dict[str, Any],
    _artifact_root: Path | None = None,
) -> list[Finding]:
    """CLI-compatible theorem-certificate auditor."""

    return list(replay_theorem_certificate(raw).findings)
