from __future__ import annotations

import unittest
from dataclasses import replace
from fractions import Fraction

from bsc_audit.bicomplex import ChainComplex, Transport
from bsc_audit.exact import Matrix
from bsc_audit.exact_linear import replay_linear_certificate, solve_exact
from bsc_audit.mapping_complex import (
    flatten_homogeneous_map,
    mapping_differential,
    mapping_differential_system,
)


class MappingComplexTests(unittest.TestCase):
    def test_degree_zero_differential_matches_the_chain_map_defect(self):
        source = ChainComplex(
            "C",
            {0: 1, 1: 1},
            {1: Matrix.from_nested([[3]])},
        )
        target = ChainComplex(
            "D",
            {0: 1, 1: 1},
            {1: Matrix.from_nested([[5]])},
        )
        transport = Transport(
            "f",
            source,
            target,
            {
                0: Matrix.from_nested([[2]]),
                1: Matrix.from_nested([[1]]),
            },
        )

        expected = {}
        for degree in sorted(source.groups):
            d_target = target.differentials.get(
                degree,
                Matrix.zero(
                    target.groups.get(degree - 1, 0),
                    target.groups.get(degree, 0),
                ),
            )
            d_source = source.differentials.get(
                degree,
                Matrix.zero(
                    source.groups.get(degree - 1, 0),
                    source.groups.get(degree, 0),
                ),
            )
            expected[degree] = (
                d_target @ transport.map_at(degree)
                - transport.map_at(degree - 1) @ d_source
            )

        actual = mapping_differential(
            source,
            target,
            transport.maps,
            0,
        )
        self.assertEqual(actual, expected)
        self.assertEqual(transport.theta(), expected)
        self.assertEqual(actual[1].rows, ((Fraction(-1),),))

    def test_mapping_differential_squares_to_zero_with_nontrivial_signs(self):
        source = ChainComplex(
            "C",
            {0: 1, 1: 1},
            {1: Matrix.from_nested([[1]])},
        )
        target = ChainComplex(
            "D",
            {0: 0, 1: 1, 2: 1},
            {
                1: Matrix.zero(0, 1),
                2: Matrix.from_nested([[1]]),
            },
        )
        degree_two = {0: Matrix.from_nested([[1]])}

        degree_one = mapping_differential(
            source,
            target,
            degree_two,
            2,
        )
        self.assertEqual(degree_one[0].rows, ((Fraction(1),),))
        self.assertEqual(degree_one[1].rows, ((Fraction(-1),),))

        degree_zero = mapping_differential(
            source,
            target,
            degree_one,
            1,
        )
        self.assertTrue(all(component.is_zero() for component in degree_zero.values()))

    def test_compiled_system_is_exactly_the_mapping_differential(self):
        source = ChainComplex(
            "C",
            {0: 1, 1: 1},
            {1: Matrix.from_nested([[1]])},
        )
        target = ChainComplex(
            "D",
            {0: 1, 1: 1, 2: 1},
            {
                1: Matrix.from_nested([[0]]),
                2: Matrix.from_nested([[1]]),
            },
        )
        homotopy = {
            0: Matrix.from_nested([[2]]),
            1: Matrix.from_nested([[-3]]),
        }
        system = mapping_differential_system(source, target, 1)
        vector = flatten_homogeneous_map(
            source,
            target,
            homotopy,
            1,
            system.variable_coordinates,
        )
        compiled = tuple(
            sum(
                (coefficient * vector[index] for index, coefficient in enumerate(row)),
                Fraction(0),
            )
            for row in system.matrix
        )
        direct = flatten_homogeneous_map(
            source,
            target,
            mapping_differential(source, target, homotopy, 1),
            0,
            system.equation_coordinates,
        )
        self.assertEqual(compiled, direct)
        self.assertEqual(direct, (Fraction(0), Fraction(-1)))

    def test_derived_verdict_is_invariant_under_rational_basis_rescaling(self):
        source = ChainComplex(
            "C",
            {0: 1, 1: 1},
            {1: Matrix.from_nested([[3]])},
        )
        target = ChainComplex(
            "D",
            {0: 1, 1: 1},
            {1: Matrix.from_nested([[5]])},
        )
        omega = {
            0: Matrix.from_nested([[5]]),
            1: Matrix.from_nested([[3]]),
        }
        system = mapping_differential_system(source, target, 1)
        rhs = flatten_homogeneous_map(
            source,
            target,
            omega,
            0,
            system.equation_coordinates,
        )
        original = solve_exact(system.matrix, rhs, ncols=len(system.variable_coordinates))

        rescaled_source = ChainComplex(
            "C'",
            {0: 1, 1: 1},
            {1: Matrix.from_nested([[Fraction(21, 2)]])},
        )
        rescaled_target = ChainComplex(
            "D'",
            {0: 1, 1: 1},
            {1: Matrix.from_nested([[Fraction(55, 3)]])},
        )
        rescaled_omega = {
            0: Matrix.from_nested([[Fraction(10, 3)]]),
            1: Matrix.from_nested([[Fraction(21, 11)]]),
        }
        rescaled_system = mapping_differential_system(
            rescaled_source,
            rescaled_target,
            1,
        )
        rescaled_rhs = flatten_homogeneous_map(
            rescaled_source,
            rescaled_target,
            rescaled_omega,
            0,
            rescaled_system.equation_coordinates,
        )
        rescaled = solve_exact(
            rescaled_system.matrix,
            rescaled_rhs,
            ncols=len(rescaled_system.variable_coordinates),
        )
        self.assertTrue(original.consistent)
        self.assertTrue(rescaled.consistent)

        zero_source = ChainComplex("E", {0: 1}, {})
        zero_target = ChainComplex("F", {0: 1}, {})
        zero_system = mapping_differential_system(zero_source, zero_target, 1)
        obstructed = solve_exact(
            zero_system.matrix,
            [Fraction(1)],
            ncols=len(zero_system.variable_coordinates),
        )
        rescaled_obstructed = solve_exact(
            zero_system.matrix,
            [Fraction(2, 3)],
            ncols=len(zero_system.variable_coordinates),
        )
        self.assertFalse(obstructed.consistent)
        self.assertFalse(rescaled_obstructed.consistent)

    def test_gapped_complex_and_zero_variable_obstruction(self):
        source = ChainComplex("C", {0: 1, 2: 1}, {})
        target = ChainComplex("D", {0: 1, 2: 1}, {})
        omega = {
            0: Matrix.from_nested([[0]]),
            2: Matrix.from_nested([[1]]),
        }
        system = mapping_differential_system(source, target, 1)
        rhs = flatten_homogeneous_map(
            source,
            target,
            omega,
            0,
            system.equation_coordinates,
        )
        certificate = solve_exact(
            system.matrix,
            rhs,
            ncols=len(system.variable_coordinates),
        )
        self.assertEqual(system.variable_coordinates, ())
        self.assertFalse(certificate.consistent)
        replay_linear_certificate(
            system.matrix,
            rhs,
            certificate,
            ncols=0,
        )

    def test_forged_primal_certificate_is_rejected(self):
        matrix = [[Fraction(1)]]
        rhs = [Fraction(1)]
        certificate = solve_exact(matrix, rhs)
        replay_linear_certificate(matrix, rhs, certificate)
        with self.assertRaisesRegex(ValueError, "does not replay"):
            replay_linear_certificate(
                matrix,
                rhs,
                replace(certificate, solution=(Fraction(2),)),
            )

    def test_system_resource_limit_is_checked_before_allocation(self):
        source = ChainComplex("C", {0: 12}, {})
        target = ChainComplex("D", {0: 12}, {})
        with self.assertRaisesRegex(ValueError, "exceeds 128 equations"):
            mapping_differential_system(source, target, 1)


if __name__ == "__main__":
    unittest.main()
