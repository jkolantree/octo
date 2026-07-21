from __future__ import annotations

import hashlib
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .bicomplex import ChainComplex, Transport, load_complex, load_transport, matrix_witness
from .exact import Matrix, scalar_json
from .exact_linear import (
    MAX_LINEAR_CELLS,
    MAX_LINEAR_EQUATIONS,
    MAX_INTERMEDIATE_BITS,
    MAX_LINEAR_VARIABLES,
    LinearCertificate,
    solve_exact,
)
from .findings import Finding, Severity


MAX_COMPOSITION_SCALAR_PRODUCTS = 1_000_000


class HolonomyResourceLimit(ValueError):
    pass


@dataclass
class CompositionBudget:
    used: int = 0

    def consume(self, amount: int) -> None:
        if amount < 0 or self.used + amount > MAX_COMPOSITION_SCALAR_PRODUCTS:
            raise HolonomyResourceLimit(
                f"path composition exceeds {MAX_COMPOSITION_SCALAR_PRODUCTS} scalar products per document"
            )
        self.used += amount


def _bounded_fraction(value: Fraction) -> Fraction:
    if value.numerator.bit_length() > MAX_INTERMEDIATE_BITS or value.denominator.bit_length() > MAX_INTERMEDIATE_BITS:
        raise HolonomyResourceLimit(
            f"path-composition intermediate exceeds {MAX_INTERMEDIATE_BITS} bits"
        )
    return value


def _bounded_matmul(left: Matrix, right: Matrix, budget: CompositionBudget) -> Matrix:
    rows, inner = left.shape
    inner_right, columns = right.shape
    if inner != inner_right:
        raise ValueError(f"matrix shape mismatch: {left.shape} @ {right.shape}")
    budget.consume(rows * inner * columns)
    values: list[tuple[Fraction, ...]] = []
    for row in range(rows):
        output_row: list[Fraction] = []
        for column in range(columns):
            total = Fraction(0)
            for index in range(inner):
                product = _bounded_fraction(left.rows[row][index] * right.rows[index][column])
                total = _bounded_fraction(total + product)
            output_row.append(total)
        values.append(tuple(output_row))
    return Matrix(tuple(values), columns)


def _bounded_then(first: Transport, second: Transport, name: str, budget: CompositionBudget) -> Transport:
    if first.target.name != second.source.name:
        raise ValueError("transport endpoints do not compose")
    degrees = set(first.source.groups) | set(second.target.groups)
    maps = {
        degree: _bounded_matmul(second.map_at(degree), first.map_at(degree), budget)
        for degree in degrees
    }
    return Transport(name, first.source, second.target, maps)


def _degree(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError("basis degree must be an integer or decimal integer string")
    text = str(value)
    if not text.isdigit():
        raise ValueError("basis degree must be nonnegative")
    return int(text)


def _basis_findings(name: str, raw: dict[str, Any], context: ChainComplex) -> list[Finding]:
    path = f"contexts.{name}.basis"
    basis = raw.get("basis")
    if not isinstance(basis, dict):
        return [Finding(Severity.ERROR, "SEMANTIC_BASIS_MISSING", path, "every holonomy context requires content-addressed basis semantics")]
    findings: list[Finding] = []
    normalized: dict[int, list[Any]] = {}
    for degree_raw, records in basis.items():
        try:
            degree = _degree(degree_raw)
        except (TypeError, ValueError) as exc:
            findings.append(Finding(Severity.ERROR, "SEMANTIC_BASIS_DEGREE", path, str(exc)))
            continue
        if degree in normalized:
            findings.append(Finding(Severity.ERROR, "SEMANTIC_BASIS_DEGREE", path, f"duplicate normalized basis degree {degree}"))
            continue
        if not isinstance(records, list):
            findings.append(Finding(Severity.ERROR, "SEMANTIC_BASIS_TYPE", f"{path}.{degree}", "basis records must be an array"))
            continue
        normalized[degree] = records
    if set(normalized) != set(context.groups):
        findings.append(
            Finding(
                Severity.ERROR,
                "SEMANTIC_BASIS_COVERAGE",
                path,
                "basis degrees must exactly match the declared chain groups",
                {"declared": sorted(context.groups), "provided": sorted(normalized)},
            )
        )
    for degree, dimension in context.groups.items():
        records = normalized.get(degree, [])
        if len(records) != dimension:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "SEMANTIC_BASIS_DIMENSION",
                    f"{path}.{degree}",
                    f"expected {dimension} semantic basis records, found {len(records)}",
                )
            )
        seen: set[str] = set()
        for index, record in enumerate(records):
            record_path = f"{path}.{degree}.{index}"
            if not isinstance(record, dict):
                findings.append(Finding(Severity.ERROR, "SEMANTIC_BASIS_TYPE", record_path, "basis record must be an object"))
                continue
            label = record.get("label")
            meaning = record.get("meaning")
            digest = record.get("sha256")
            if not isinstance(label, str) or not label or not isinstance(meaning, str) or not meaning or not isinstance(digest, str):
                findings.append(Finding(Severity.ERROR, "SEMANTIC_BASIS_TYPE", record_path, "basis record requires nonempty label, meaning, and sha256 strings"))
                continue
            expected = "sha256:" + hashlib.sha256(meaning.encode("utf-8")).hexdigest()
            if digest != expected:
                findings.append(Finding(Severity.ERROR, "SEMANTIC_BASIS_HASH", record_path, "semantic meaning does not match its declared SHA-256 digest"))
            if label in seen:
                findings.append(Finding(Severity.ERROR, "SEMANTIC_BASIS_LABEL", record_path, "basis labels must be unique within a degree"))
            seen.add(label)
    if not findings:
        findings.append(Finding(Severity.INFO, "SEMANTIC_BASIS_BOUND", path, "all basis vectors are bound to explicit semantic records; interpretation remains an external obligation"))
    return findings


def _compose_path(
    name: str,
    identifiers: list[str],
    transports: dict[str, Transport],
    budget: CompositionBudget,
    cache: dict[tuple[str, ...], Transport],
) -> Transport:
    key = tuple(identifiers)
    if key in cache:
        return cache[key]
    composed = transports[identifiers[0]]
    for identifier in identifiers[1:]:
        composed = _bounded_then(composed, transports[identifier], name, budget)
    result = Transport(name, composed.source, composed.target, composed.maps)
    cache[key] = result
    return result


def _homotopy_system(source: ChainComplex, target: ChainComplex, omega: dict[int, Matrix]) -> tuple[list[list[Fraction]], list[Fraction], list[tuple[int, int, int]], list[tuple[int, int, int]]]:
    degrees = sorted(set(source.groups) | set(target.groups))
    equation_count = sum(target.groups.get(degree, 0) * source.groups.get(degree, 0) for degree in degrees)
    variable_count = sum(target.groups.get(degree + 1, 0) * source.groups.get(degree, 0) for degree in degrees)
    if equation_count > MAX_LINEAR_EQUATIONS:
        raise ValueError(f"homotopy system exceeds {MAX_LINEAR_EQUATIONS} equations")
    if variable_count > MAX_LINEAR_VARIABLES:
        raise ValueError(f"homotopy system exceeds {MAX_LINEAR_VARIABLES} variables")
    if equation_count * variable_count > MAX_LINEAR_CELLS:
        raise ValueError(f"homotopy system exceeds {MAX_LINEAR_CELLS} coefficient cells")
    equations = [
        (degree, row, column)
        for degree in degrees
        for row in range(target.groups.get(degree, 0))
        for column in range(source.groups.get(degree, 0))
    ]
    variables = [
        (degree, row, column)
        for degree in degrees
        for row in range(target.groups.get(degree + 1, 0))
        for column in range(source.groups.get(degree, 0))
    ]
    equation_index = {coordinate: index for index, coordinate in enumerate(equations)}
    coefficients = [[Fraction(0) for _ in variables] for _ in equations]
    for variable_index, (degree, row, column) in enumerate(variables):
        d_target = target.differentials.get(
            degree + 1,
            Matrix.zero(target.groups.get(degree, 0), target.groups.get(degree + 1, 0)),
        )
        for output_row in range(target.groups.get(degree, 0)):
            value = d_target.rows[output_row][row]
            if value:
                coefficients[equation_index[(degree, output_row, column)]][variable_index] += value
        d_source = source.differentials.get(
            degree + 1,
            Matrix.zero(source.groups.get(degree, 0), source.groups.get(degree + 1, 0)),
        )
        for input_column in range(source.groups.get(degree + 1, 0)):
            value = d_source.rows[column][input_column]
            if value:
                coefficients[equation_index[(degree + 1, row, input_column)]][variable_index] += value
    rhs = [omega[degree].rows[row][column] for degree, row, column in equations]
    return coefficients, rhs, equations, variables


def _certificate_json(
    certificate: LinearCertificate,
    source: ChainComplex,
    target: ChainComplex,
    equations: list[tuple[int, int, int]],
    variables: list[tuple[int, int, int]],
) -> dict[str, object]:
    result = certificate.to_json()
    result["equation_coordinates"] = [
        {"degree": degree, "target_basis": row, "source_basis": column}
        for degree, row, column in equations
    ]
    result["variable_coordinates"] = [
        {"degree": degree, "target_basis": row, "source_basis": column}
        for degree, row, column in variables
    ]
    if certificate.solution is not None:
        by_coordinate = {coordinate: certificate.solution[index] for index, coordinate in enumerate(variables)}
        homotopy: list[dict[str, object]] = []
        for degree in sorted(source.groups):
            rows = target.groups.get(degree + 1, 0)
            columns = source.groups.get(degree, 0)
            values = [
                [scalar_json(by_coordinate.get((degree, row, column), Fraction(0))) for column in range(columns)]
                for row in range(rows)
            ]
            homotopy.append({"degree": degree, "shape": [rows, columns], "matrix": values})
        result["homotopy"] = homotopy
    return result


def _derived_certificate(first: Transport, second: Transport) -> tuple[LinearCertificate, dict[str, object]]:
    degrees = sorted(set(first.source.groups) | set(first.target.groups))
    omega = {degree: first.map_at(degree) - second.map_at(degree) for degree in degrees}
    coefficients, rhs, equations, variables = _homotopy_system(first.source, first.target, omega)
    certificate = solve_exact(coefficients, rhs, ncols=len(variables))
    return certificate, _certificate_json(certificate, first.source, first.target, equations, variables)


def _strict_defects(first: Transport, second: Transport) -> list[tuple[int, Matrix]]:
    degrees = sorted(set(first.source.groups) | set(first.target.groups))
    return [(degree, first.map_at(degree) - second.map_at(degree)) for degree in degrees if not (first.map_at(degree) - second.map_at(degree)).is_zero()]


def _projection_findings(name: str, projection: Transport, expected_source: ChainComplex) -> list[Finding]:
    path = f"relations.{name}.observation_projection"
    findings: list[Finding] = []
    if projection.source.name != expected_source.name:
        return [Finding(Severity.ERROR, "OBSERVATION_PROJECTION_SOURCE", path, "observation projection must start at the common path target")]
    shape_findings = projection.validate_shapes()
    if shape_findings:
        return [Finding(Severity.ERROR, "OBSERVATION_PROJECTION_SHAPE", path, "observation projection has invalid component shapes")]
    nonzero_theta = [degree for degree, defect in projection.theta().items() if not defect.is_zero()]
    if nonzero_theta:
        return [Finding(Severity.ERROR, "OBSERVATION_PROJECTION_CHAIN_MAP", path, "observation projection must be a chain map", {"degrees": nonzero_theta})]
    rank_failures = []
    for degree, dimension in projection.target.groups.items():
        rank = projection.map_at(degree).rank()
        if rank != dimension:
            rank_failures.append({"degree": degree, "rank": rank, "target_dimension": dimension})
    if rank_failures:
        findings.append(Finding(Severity.ERROR, "OBSERVATION_PROJECTION_NOT_SURJECTIVE", path, "observation projection must be degreewise surjective", rank_failures))
    else:
        findings.append(Finding(Severity.INFO, "OBSERVATION_PROJECTION_LAWFUL", path, "chain-map surjectivity certifies a null-subcomplex kernel and finite observed quotient"))
    return findings


def audit_holonomy_document(raw: dict[str, Any]) -> list[Finding]:
    if raw.get("field") != "Q":
        return [Finding(Severity.ERROR, "HOLONOMY_FIELD", "field", "derived-holonomy certificates currently require the exact field Q")]
    contexts_raw = raw.get("contexts")
    if not isinstance(contexts_raw, dict) or not contexts_raw:
        return [Finding(Severity.ERROR, "CONTEXTS_MISSING", "contexts", "at least one certificate context is required")]

    findings: list[Finding] = []
    contexts: dict[str, ChainComplex] = {}
    for name, value in contexts_raw.items():
        if not name:
            findings.append(Finding(Severity.ERROR, "CONTEXT_NAME", "contexts", "context names must be nonempty strings"))
            continue
        try:
            context = load_complex(name, value)
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            findings.append(Finding(Severity.ERROR, "CONTEXT_TYPE", f"contexts.{name}", f"invalid certificate context: {exc}"))
            continue
        context_findings = context.validate()
        findings.extend(context_findings)
        findings.extend(_basis_findings(name, value, context))
        if not any(finding.severity == Severity.ERROR for finding in context_findings):
            contexts[name] = context
    if any(finding.severity == Severity.ERROR for finding in findings):
        return findings

    transports_raw = raw.get("transports")
    if not isinstance(transports_raw, dict):
        return findings + [Finding(Severity.ERROR, "TRANSPORTS_TYPE", "transports", "transports must be a JSON object")]
    transports: dict[str, Transport] = {}
    lawful: dict[str, bool] = {}
    for name, value in transports_raw.items():
        if not name:
            findings.append(Finding(Severity.ERROR, "TRANSPORT_NAME", "transports", "transport names must be nonempty strings"))
            continue
        try:
            transport = load_transport(name, value, contexts)
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            findings.append(Finding(Severity.ERROR, "TRANSPORT_TYPE", f"transports.{name}", f"invalid certificate transport: {exc}"))
            continue
        shape_findings = transport.validate_shapes()
        findings.extend(shape_findings)
        if shape_findings:
            continue
        defects = [(degree, defect) for degree, defect in transport.theta().items() if not defect.is_zero()]
        lawful[name] = not defects
        transports[name] = transport
        if defects:
            degree, defect = defects[0]
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "HOLONOMY_EDGE_ILLEGAL",
                    f"transports.{name}.maps.{degree}",
                    "edge transport is not a chain map, so no derived class may be constructed",
                    matrix_witness(defect.first_nonzero_column(), degree),
                )
            )
        else:
            findings.append(Finding(Severity.INFO, "HOLONOMY_EDGE_LAWFUL", f"transports.{name}", "edge transport is an exact chain map"))
    if any(finding.severity == Severity.ERROR for finding in findings):
        return findings

    relations_raw = raw.get("relations")
    if not isinstance(relations_raw, dict):
        return findings + [Finding(Severity.ERROR, "RELATIONS_TYPE", "relations", "relations must be a JSON object")]
    composition_budget = CompositionBudget()
    path_cache: dict[tuple[str, ...], Transport] = {}
    for name, relation in relations_raw.items():
        if not name or not isinstance(relation, dict):
            findings.append(Finding(Severity.ERROR, "HOLONOMY_RELATION_TYPE", "relations", "relation names and records must be well formed"))
            continue
        path = f"relations.{name}"
        left_ids = relation["left_path"]
        right_ids = relation["right_path"]
        missing = sorted({identifier for identifier in left_ids + right_ids if identifier not in transports})
        if missing:
            findings.append(Finding(Severity.ERROR, "HOLONOMY_TRANSPORT_REFERENCE", path, "relation references missing or invalid transports", {"transports": missing}))
            continue
        illegal = sorted({identifier for identifier in left_ids + right_ids if not lawful.get(identifier, False)})
        try:
            left = _compose_path(f"{name}_left", left_ids, transports, composition_budget, path_cache)
            right = _compose_path(f"{name}_right", right_ids, transports, composition_budget, path_cache)
        except HolonomyResourceLimit as exc:
            findings.append(Finding(Severity.ERROR, "HOLONOMY_RESOURCE_LIMIT", path, str(exc)))
            continue
        except ValueError as exc:
            findings.append(Finding(Severity.ERROR, "HOLONOMY_PATH_COMPOSITION", path, f"path transports do not compose: {exc}"))
            continue
        if left.source.name != right.source.name or left.target.name != right.target.name:
            findings.append(Finding(Severity.ERROR, "HOLONOMY_ENDPOINTS", path, "the two paths must have identical source and target contexts"))
            continue

        required = relation["required_equivalence"]
        defects = _strict_defects(left, right)
        if not defects:
            findings.append(Finding(Severity.INFO, "HOLONOMY_STRICT_PASS", path, "the two path transports agree exactly"))
        else:
            degree, defect = defects[0]
            severity = Severity.BLOCKED if required == "strict" else Severity.WARNING
            findings.append(
                Finding(
                    severity,
                    "HOLONOMY_STRICT_FAIL",
                    path,
                    "the two path transports differ strictly",
                    matrix_witness(defect.first_nonzero_column(), degree),
                )
            )
        if illegal:
            if required != "strict":
                findings.append(Finding(Severity.BLOCKED, "HOLONOMY_DERIVED_NOT_CONSTRUCTED", path, "derived comparison is prohibited because a path contains a non-chain-map edge", {"transports": illegal}))
            continue
        if required == "strict":
            continue

        projection: Transport | None = None
        if required == "observed_derived":
            projection_name = relation["observation_projection"]
            projection = transports.get(projection_name)
            if projection is None:
                findings.append(Finding(Severity.ERROR, "OBSERVATION_PROJECTION_REFERENCE", f"{path}.observation_projection", "observation projection must name a valid transport"))
                continue
            projection_checks = _projection_findings(name, projection, left.target)
            findings.extend(projection_checks)
            if any(finding.severity == Severity.ERROR for finding in projection_checks):
                continue

        try:
            derived, derived_json = _derived_certificate(left, right)
        except ValueError as exc:
            findings.append(Finding(Severity.ERROR, "HOLONOMY_RESOURCE_LIMIT", path, str(exc)))
            continue
        if required == "derived":
            findings.append(
                Finding(
                    Severity.INFO if derived.consistent else Severity.BLOCKED,
                    "HOLONOMY_DERIVED_PASS" if derived.consistent else "HOLONOMY_DERIVED_FAIL",
                    path,
                    "strict defect is chain-null-homotopic over Q" if derived.consistent else "strict defect survives in H_0(Hom) over Q",
                    derived_json,
                )
            )
            continue

        if projection is None:  # pragma: no cover - guarded by the route enum
            raise ArithmeticError("observed-derived route lost its validated projection")
        findings.append(
            Finding(
                Severity.INFO if derived.consistent else Severity.WARNING,
                "HOLONOMY_DERIVED_PASS" if derived.consistent else "HOLONOMY_DERIVED_FAIL",
                path,
                "strict defect is already chain-null-homotopic" if derived.consistent else "pre-observation derived obstruction remains and requires the declared quotient",
                derived_json,
            )
        )
        try:
            observed_left = _bounded_then(left, projection, f"{name}_observed_left", composition_budget)
            observed_right = _bounded_then(right, projection, f"{name}_observed_right", composition_budget)
        except HolonomyResourceLimit as exc:
            findings.append(Finding(Severity.ERROR, "HOLONOMY_RESOURCE_LIMIT", path, str(exc)))
            continue
        try:
            observed, observed_json = _derived_certificate(observed_left, observed_right)
        except ValueError as exc:
            findings.append(Finding(Severity.ERROR, "HOLONOMY_RESOURCE_LIMIT", path, str(exc)))
            continue
        findings.append(
            Finding(
                Severity.INFO if observed.consistent else Severity.BLOCKED,
                "HOLONOMY_OBSERVED_DERIVED_PASS" if observed.consistent else "HOLONOMY_OBSERVED_DERIVED_FAIL",
                path,
                "the projected defect is chain-null-homotopic over Q" if observed.consistent else "the derived obstruction survives the declared observation quotient",
                observed_json,
            )
        )
    return findings
