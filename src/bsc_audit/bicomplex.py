from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exact import MAX_MATRIX_AXIS, Matrix, scalar_json
from .findings import Finding, Severity
from .mapping_complex import mapping_differential


@dataclass(frozen=True)
class ChainComplex:
    name: str
    groups: dict[int, int]
    differentials: dict[int, Matrix]

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []
        shape_valid: set[int] = set()
        for degree, dimension in self.groups.items():
            if degree < 0:
                findings.append(Finding(Severity.ERROR, "COMPLEX_NEGATIVE_DEGREE", f"contexts.{self.name}.groups.{degree}", "the 0.3 format supports only nonnegative chain degrees"))
            if dimension < 0:
                findings.append(Finding(Severity.ERROR, "COMPLEX_NEGATIVE_DIMENSION", f"contexts.{self.name}.groups.{degree}", "group dimension is negative"))
        for degree, differential in self.differentials.items():
            if degree not in self.groups:
                findings.append(Finding(Severity.ERROR, "COMPLEX_UNDECLARED_DIFFERENTIAL", f"contexts.{self.name}.differentials.{degree}", "differential degree is not declared in groups"))
                continue
            expected = (self.groups.get(degree - 1, 0), self.groups.get(degree, 0))
            if differential.shape != expected:
                findings.append(Finding(Severity.ERROR, "COMPLEX_SHAPE", f"contexts.{self.name}.differentials.{degree}", f"expected shape {expected}, found {differential.shape}"))
            else:
                shape_valid.add(degree)
        for degree in sorted(self.differentials):
            if degree not in shape_valid or degree - 1 not in shape_valid:
                continue
            square = self.differentials[degree - 1] @ self.differentials[degree]
            if not square.is_zero():
                witness = square.first_nonzero_column()
                findings.append(Finding(Severity.ERROR, "COMPLEX_D_SQUARED", f"contexts.{self.name}.differentials.{degree}", "declared differential does not square to zero", matrix_witness(witness)))
        return findings


@dataclass(frozen=True)
class Transport:
    name: str
    source: ChainComplex
    target: ChainComplex
    maps: dict[int, Matrix]

    def validate_shapes(self) -> list[Finding]:
        findings: list[Finding] = []
        declared_degrees = set(self.source.groups) | set(self.target.groups)
        for degree in set(self.maps) - declared_degrees:
            findings.append(Finding(Severity.ERROR, "TRANSPORT_UNDECLARED_DEGREE", f"transports.{self.name}.maps.{degree}", "transport component is supplied at a degree undeclared by both endpoint complexes"))
        for degree in set(self.source.groups) | set(self.target.groups):
            matrix = self.maps.get(degree, Matrix.zero(self.target.groups.get(degree, 0), self.source.groups.get(degree, 0)))
            expected = (self.target.groups.get(degree, 0), self.source.groups.get(degree, 0))
            if matrix.shape != expected:
                findings.append(Finding(Severity.ERROR, "TRANSPORT_SHAPE", f"transports.{self.name}.maps.{degree}", f"expected shape {expected}, found {matrix.shape}"))
        return findings

    def map_at(self, degree: int) -> Matrix:
        return self.maps.get(degree, Matrix.zero(self.target.groups.get(degree, 0), self.source.groups.get(degree, 0)))

    def theta(self) -> dict[int, Matrix]:
        return mapping_differential(self.source, self.target, self.maps, 0)

    def audit_naturality(self) -> list[Finding]:
        findings = self.validate_shapes()
        if findings:
            return findings
        for degree, defect in self.theta().items():
            if defect.is_zero():
                continue
            column = defect.first_nonzero_column()
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "CERTIFICATE_INTERCHANGE_DEFECT",
                    f"transports.{self.name}.maps.{degree}",
                    "verification does not commute with this context transport",
                    matrix_witness(column, degree),
                    "supply a chain-map correction or restrict the promoted claim to its source context",
                )
            )
        if not any(f.severity in {Severity.ERROR, Severity.BLOCKED} for f in findings):
            findings.append(Finding(Severity.INFO, "CERTIFICATE_NATURAL", f"transports.{self.name}", "all certificate-interchange defects vanish"))
        return findings

    def then(self, second: "Transport", name: str | None = None) -> "Transport":
        if self.target.name != second.source.name:
            raise ValueError("transport endpoints do not compose")
        degrees = set(self.source.groups) | set(second.target.groups)
        return Transport(name or f"{second.name}_after_{self.name}", self.source, second.target, {degree: second.map_at(degree) @ self.map_at(degree) for degree in degrees})


def matrix_witness(witness: tuple[int, tuple] | None, degree: int | None = None) -> dict[str, Any] | None:
    if witness is None:
        return None
    index, residual = witness
    result: dict[str, Any] = {"basis_index": index, "residual": [scalar_json(value) for value in residual]}
    if degree is not None:
        result["degree"] = degree
    return result


def square_holonomy(name: str, first_path: Transport, second_path: Transport) -> list[Finding]:
    if first_path.source.name != second_path.source.name or first_path.target.name != second_path.target.name:
        return [Finding(Severity.ERROR, "SQUARE_ENDPOINTS", f"squares.{name}", "the two square paths have different endpoints")]
    findings: list[Finding] = []
    degrees = set(first_path.source.groups) | set(first_path.target.groups)
    for degree in sorted(degrees):
        defect = first_path.map_at(degree) - second_path.map_at(degree)
        if not defect.is_zero():
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "TRANSPORT_HOLONOMY",
                    f"squares.{name}.{degree}",
                    "transport depends on the chosen context path",
                    matrix_witness(defect.first_nonzero_column(), degree),
                    "declare a bounded naturality defect or repair the gluing maps",
                )
            )
    if not findings:
        findings.append(Finding(Severity.INFO, "TRANSPORT_FLAT", f"squares.{name}", "the declared transport square commutes exactly"))
    return findings


def _degree(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError("degree must be an integer or decimal integer string")
    if isinstance(value, str) and (not value or (value.startswith("-") and not value[1:].isdigit()) or (not value.startswith("-") and not value.isdigit())):
        raise ValueError("degree string must contain only an optional minus sign and decimal digits")
    degree = int(value)
    if degree < 0:
        raise ValueError("the 0.3 format supports only nonnegative chain degrees")
    return degree


def _matrix(values: Any, ncols: int) -> Matrix:
    if not isinstance(values, (list, tuple)):
        raise TypeError("matrix must be a list of row lists")
    if any(not isinstance(row, (list, tuple)) for row in values):
        raise TypeError("every matrix row must be a list")
    return Matrix.from_nested(values, ncols=ncols)


def load_complex(name: str, raw: dict[str, Any]) -> ChainComplex:
    if not isinstance(raw, dict):
        raise TypeError("context must be a JSON object")
    groups_raw = raw.get("groups")
    if not isinstance(groups_raw, dict) or not groups_raw:
        raise ValueError("context requires a nonempty groups object")
    groups: dict[int, int] = {}
    for degree_raw, dimension_raw in groups_raw.items():
        degree = _degree(degree_raw)
        if degree in groups:
            raise ValueError(f"duplicate degree after integer normalization: {degree}")
        if isinstance(dimension_raw, bool) or not isinstance(dimension_raw, (int, str)):
            raise TypeError("dimension must be an integer or decimal integer string")
        if isinstance(dimension_raw, str) and (not dimension_raw or not dimension_raw.isdigit()):
            raise ValueError("dimension string must contain decimal digits")
        dimension = int(dimension_raw)
        if dimension < 0:
            raise ValueError(f"negative dimension at degree {degree}")
        if dimension > MAX_MATRIX_AXIS:
            raise ValueError(f"dimension at degree {degree} exceeds the executable limit {MAX_MATRIX_AXIS}")
        groups[degree] = dimension

    differentials_raw = raw.get("differentials", {})
    if not isinstance(differentials_raw, dict):
        raise TypeError("differentials must be a JSON object")
    differentials: dict[int, Matrix] = {}
    for degree_raw, values in differentials_raw.items():
        degree = _degree(degree_raw)
        if degree not in groups:
            raise ValueError(f"differential supplied at undeclared degree {degree}")
        if degree in differentials:
            raise ValueError(f"duplicate differential degree after integer normalization: {degree}")
        differentials[degree] = _matrix(values, groups[degree])
    return ChainComplex(name, groups, differentials)


def load_transport(name: str, raw: dict[str, Any], contexts: dict[str, ChainComplex]) -> Transport:
    if not isinstance(raw, dict):
        raise TypeError("transport must be a JSON object")
    source_name = raw.get("source")
    target_name = raw.get("target")
    if not isinstance(source_name, str) or not isinstance(target_name, str):
        raise TypeError("transport source and target must be context-name strings")
    if source_name not in contexts or target_name not in contexts:
        raise ValueError("transport source and target must name declared valid contexts")
    source = contexts[source_name]
    target = contexts[target_name]
    maps_raw = raw.get("maps", {})
    if not isinstance(maps_raw, dict):
        raise TypeError("transport maps must be a JSON object")
    declared_degrees = set(source.groups) | set(target.groups)
    maps: dict[int, Matrix] = {}
    for degree_raw, values in maps_raw.items():
        degree = _degree(degree_raw)
        if degree not in declared_degrees:
            raise ValueError(f"transport component supplied at undeclared degree {degree}")
        if degree in maps:
            raise ValueError(f"duplicate transport degree after integer normalization: {degree}")
        maps[degree] = _matrix(values, source.groups.get(degree, 0))
    return Transport(name, source, target, maps)


def audit_complex_document(raw: dict[str, Any]) -> list[Finding]:
    if not isinstance(raw, dict):
        return [Finding(Severity.ERROR, "COMPLEX_DOCUMENT_TYPE", "$", "complex document must be a JSON object")]
    contexts_raw = raw.get("contexts")
    if not isinstance(contexts_raw, dict) or not contexts_raw:
        return [Finding(Severity.ERROR, "CONTEXTS_MISSING", "contexts", "at least one certificate context is required")]

    findings: list[Finding] = []
    contexts: dict[str, ChainComplex] = {}
    for name, value in contexts_raw.items():
        if not isinstance(name, str) or not name:
            findings.append(Finding(Severity.ERROR, "CONTEXT_NAME", "contexts", "context names must be nonempty strings"))
            continue
        try:
            context = load_complex(name, value)
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            findings.append(Finding(Severity.ERROR, "CONTEXT_TYPE", f"contexts.{name}", f"invalid certificate context: {exc}"))
            continue
        contexts[name] = context
        findings.extend(context.validate())

    if any(finding.severity == Severity.ERROR for finding in findings):
        return findings

    transports_raw = raw.get("transports", {})
    if not isinstance(transports_raw, dict):
        findings.append(Finding(Severity.ERROR, "TRANSPORTS_TYPE", "transports", "transports must be a JSON object"))
        return findings
    transports: dict[str, Transport] = {}
    for name, value in transports_raw.items():
        if not isinstance(name, str) or not name:
            findings.append(Finding(Severity.ERROR, "TRANSPORT_NAME", "transports", "transport names must be nonempty strings"))
            continue
        try:
            transport = load_transport(name, value, contexts)
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            findings.append(Finding(Severity.ERROR, "TRANSPORT_TYPE", f"transports.{name}", f"invalid certificate transport: {exc}"))
            continue
        transports[name] = transport
        findings.extend(transport.audit_naturality())

    squares_raw = raw.get("squares", {})
    if not isinstance(squares_raw, dict):
        findings.append(Finding(Severity.ERROR, "SQUARES_TYPE", "squares", "squares must be a JSON object"))
        return findings
    for name, square in squares_raw.items():
        path = f"squares.{name}"
        if not isinstance(name, str) or not name or not isinstance(square, dict):
            findings.append(Finding(Severity.ERROR, "SQUARE_TYPE", path, "square name and record must be well-formed"))
            continue
        required = ("left_first", "left_second", "right_first", "right_second")
        malformed = [field for field in required if not isinstance(square.get(field), str)]
        if malformed:
            findings.append(Finding(Severity.ERROR, "SQUARE_TRANSPORT_REFERENCE", path, "square transport references must be strings", witness={"fields": malformed}))
            continue
        missing = [field for field in required if square[field] not in transports]
        if missing:
            findings.append(Finding(Severity.ERROR, "SQUARE_TRANSPORT_REFERENCE", path, "square references missing or invalid transports", witness={"fields": missing}))
            continue
        try:
            left = transports[square["left_first"]].then(transports[square["left_second"]], f"{name}_left")
            right = transports[square["right_first"]].then(transports[square["right_second"]], f"{name}_right")
        except ValueError as exc:
            findings.append(Finding(Severity.ERROR, "SQUARE_COMPOSITION", path, f"square paths do not compose: {exc}"))
            continue
        findings.extend(square_holonomy(name, left, right))
    return findings
