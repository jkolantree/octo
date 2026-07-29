from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping, Protocol

from .exact import Matrix
from .exact_linear import (
    MAX_LINEAR_CELLS,
    MAX_LINEAR_EQUATIONS,
    MAX_LINEAR_VARIABLES,
)


MAX_MAPPING_DEGREE = 2
Coordinate = tuple[int, int, int]


class ComplexLike(Protocol):
    groups: Mapping[int, int]
    differentials: Mapping[int, Matrix]


@dataclass(frozen=True)
class MappingDifferentialSystem:
    """Coordinate matrix for one differential in ``Hom(C, D)``.

    A degree-``r`` homogeneous map has components
    ``phi_n: C_n -> D_(n+r)``.  The homological mapping-complex
    differential is

    ``(delta_r phi)_n = d_D phi_n - (-1)^r phi_(n-1) d_C``.
    """

    matrix: tuple[tuple[Fraction, ...], ...]
    equation_coordinates: tuple[Coordinate, ...]
    variable_coordinates: tuple[Coordinate, ...]


def _mapping_degree(value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("mapping degree must be an integer")
    if value < minimum or value > MAX_MAPPING_DEGREE:
        raise ValueError(
            f"mapping degree must lie in [{minimum},{MAX_MAPPING_DEGREE}]"
        )
    return value


def _component_at(
    source: ComplexLike,
    target: ComplexLike,
    components: Mapping[int, Matrix],
    degree: int,
    source_degree: int,
) -> Matrix:
    return components.get(
        source_degree,
        Matrix.zero(
            target.groups.get(source_degree + degree, 0),
            source.groups.get(source_degree, 0),
        ),
    )


def _validate_component_shapes(
    source: ComplexLike,
    target: ComplexLike,
    components: Mapping[int, Matrix],
    degree: int,
) -> None:
    for source_degree, component in components.items():
        if isinstance(source_degree, bool) or not isinstance(source_degree, int):
            raise TypeError("homogeneous-map component degrees must be integers")
        expected = (
            target.groups.get(source_degree + degree, 0),
            source.groups.get(source_degree, 0),
        )
        if component.shape != expected:
            raise ValueError(
                "homogeneous-map component shape mismatch at degree "
                f"{source_degree}: expected {expected}, found {component.shape}"
            )


def mapping_differential(
    source: ComplexLike,
    target: ComplexLike,
    components: Mapping[int, Matrix],
    degree: int,
) -> dict[int, Matrix]:
    """Apply the exact homological differential ``delta`` to a graded map."""

    degree = _mapping_degree(degree)
    _validate_component_shapes(source, target, components, degree)
    result: dict[int, Matrix] = {}
    for source_degree in sorted(source.groups):
        target_differential = target.differentials.get(
            source_degree + degree,
            Matrix.zero(
                target.groups.get(source_degree + degree - 1, 0),
                target.groups.get(source_degree + degree, 0),
            ),
        )
        source_differential = source.differentials.get(
            source_degree,
            Matrix.zero(
                source.groups.get(source_degree - 1, 0),
                source.groups.get(source_degree, 0),
            ),
        )
        left = target_differential @ _component_at(
            source,
            target,
            components,
            degree,
            source_degree,
        )
        right = _component_at(
            source,
            target,
            components,
            degree,
            source_degree - 1,
        ) @ source_differential
        result[source_degree] = left - right if degree % 2 == 0 else left + right
    return result


def mapping_differential_system(
    source: ComplexLike,
    target: ComplexLike,
    degree: int,
) -> MappingDifferentialSystem:
    """Compile ``delta_r`` to a bounded exact linear system over ``Q``."""

    degree = _mapping_degree(degree, minimum=1)
    source_degrees = sorted(set(source.groups) | set(target.groups))
    equations = tuple(
        (source_degree, row, column)
        for source_degree in source_degrees
        for row in range(target.groups.get(source_degree + degree - 1, 0))
        for column in range(source.groups.get(source_degree, 0))
    )
    variables = tuple(
        (source_degree, row, column)
        for source_degree in source_degrees
        for row in range(target.groups.get(source_degree + degree, 0))
        for column in range(source.groups.get(source_degree, 0))
    )
    equation_count = len(equations)
    variable_count = len(variables)
    if equation_count > MAX_LINEAR_EQUATIONS:
        raise ValueError(
            f"homotopy system exceeds {MAX_LINEAR_EQUATIONS} equations"
        )
    if variable_count > MAX_LINEAR_VARIABLES:
        raise ValueError(
            f"homotopy system exceeds {MAX_LINEAR_VARIABLES} variables"
        )
    if equation_count * variable_count > MAX_LINEAR_CELLS:
        raise ValueError(
            f"homotopy system exceeds {MAX_LINEAR_CELLS} coefficient cells"
        )

    equation_index = {
        coordinate: index for index, coordinate in enumerate(equations)
    }
    coefficients = [
        [Fraction(0) for _ in range(variable_count)]
        for _ in range(equation_count)
    ]
    source_sign = Fraction(-1 if degree % 2 == 0 else 1)
    for variable_index, (source_degree, row, column) in enumerate(variables):
        target_differential = target.differentials.get(
            source_degree + degree,
            Matrix.zero(
                target.groups.get(source_degree + degree - 1, 0),
                target.groups.get(source_degree + degree, 0),
            ),
        )
        for output_row in range(
            target.groups.get(source_degree + degree - 1, 0)
        ):
            value = target_differential.rows[output_row][row]
            if value:
                coefficients[
                    equation_index[(source_degree, output_row, column)]
                ][variable_index] += value

        source_differential = source.differentials.get(
            source_degree + 1,
            Matrix.zero(
                source.groups.get(source_degree, 0),
                source.groups.get(source_degree + 1, 0),
            ),
        )
        for input_column in range(source.groups.get(source_degree + 1, 0)):
            value = source_differential.rows[column][input_column]
            if value:
                coefficients[
                    equation_index[(source_degree + 1, row, input_column)]
                ][variable_index] += source_sign * value

    return MappingDifferentialSystem(
        tuple(tuple(row) for row in coefficients),
        equations,
        variables,
    )


def flatten_homogeneous_map(
    source: ComplexLike,
    target: ComplexLike,
    components: Mapping[int, Matrix],
    degree: int,
    coordinates: tuple[Coordinate, ...],
) -> tuple[Fraction, ...]:
    """Flatten a homogeneous map in an explicit deterministic coordinate order."""

    degree = _mapping_degree(degree)
    _validate_component_shapes(source, target, components, degree)
    return tuple(
        _component_at(
            source,
            target,
            components,
            degree,
            source_degree,
        ).rows[row][column]
        for source_degree, row, column in coordinates
    )
