import copy
import hashlib
import json
import unittest
from fractions import Fraction
from pathlib import Path

from bsc_audit.exact import Matrix
from bsc_audit.exact_linear import solve_exact
from bsc_audit.holonomy import _homotopy_system, audit_holonomy_document
from bsc_audit.bicomplex import ChainComplex


ROOT = Path(__file__).resolve().parents[1]


def basis(label: str, meaning: str) -> dict[str, str]:
    return {
        "label": label,
        "meaning": meaning,
        "sha256": "sha256:" + hashlib.sha256(meaning.encode("utf-8")).hexdigest(),
    }


class ExactLinearTests(unittest.TestCase):
    def test_primal_solution_replays(self):
        certificate = solve_exact(
            [[Fraction(1), Fraction(2)], [Fraction(3), Fraction(4)]],
            [Fraction(5), Fraction(11)],
        )
        self.assertTrue(certificate.consistent)
        self.assertEqual(certificate.solution, (Fraction(1), Fraction(2)))
        self.assertEqual(certificate.eta_squared, 0)

    def test_dual_and_singular_least_squares_replay(self):
        certificate = solve_exact(
            [[Fraction(1), Fraction(1)], [Fraction(2), Fraction(2)]],
            [Fraction(0), Fraction(1)],
        )
        self.assertFalse(certificate.consistent)
        self.assertNotEqual(certificate.pairing, 0)
        self.assertGreater(certificate.eta_squared, 0)
        self.assertEqual(certificate.least_squares_solution, (Fraction(2, 5), Fraction(0)))
        self.assertEqual(sum(certificate.dual[i] * Fraction((0, 1)[i]) for i in range(2)), certificate.pairing)

    def test_zero_variable_obstruction(self):
        certificate = solve_exact([[]], [Fraction(1)])
        self.assertFalse(certificate.consistent)
        self.assertEqual(certificate.dual, (Fraction(1),))
        self.assertEqual(certificate.eta_squared, 1)

    def test_zero_equation_system_preserves_declared_variable_width(self):
        certificate = solve_exact([], [], ncols=2)
        self.assertTrue(certificate.consistent)
        self.assertEqual(certificate.solution, (Fraction(0), Fraction(0)))


class HolonomyTests(unittest.TestCase):
    def load(self, name: str) -> dict:
        return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))

    def codes(self, name: str) -> dict[str, object]:
        return {finding.code: finding for finding in audit_holonomy_document(self.load(name))}

    def test_contractible_strict_failure_has_exact_homotopy(self):
        codes = self.codes("holonomy_contractible_derived_pass.json")
        self.assertIn("HOLONOMY_STRICT_FAIL", codes)
        certificate = codes["HOLONOMY_DERIVED_PASS"].witness
        self.assertEqual(certificate["kind"], "exact_solution")
        self.assertEqual(certificate["eta_squared"], 0)
        self.assertEqual(certificate["homotopy"][0]["matrix"], [[1]])

    def test_homology_visible_defect_has_dual_certificate(self):
        codes = self.codes("holonomy_homology_obstruction.json")
        certificate = codes["HOLONOMY_DERIVED_FAIL"].witness
        self.assertEqual(certificate["kind"], "dual_obstruction")
        self.assertNotEqual(certificate["pairing"], 0)
        self.assertEqual(certificate["least_squares_solution"], [])
        self.assertEqual(certificate["eta_squared"], 1)

    def test_observation_quotient_kills_declared_null_direction(self):
        codes = self.codes("holonomy_observed_quotient_pass.json")
        self.assertIn("OBSERVATION_PROJECTION_LAWFUL", codes)
        self.assertIn("HOLONOMY_DERIVED_FAIL", codes)
        self.assertIn("HOLONOMY_OBSERVED_DERIVED_PASS", codes)

    def test_non_chain_map_blocks_derived_construction(self):
        codes = self.codes("holonomy_non_chain_map.json")
        self.assertIn("HOLONOMY_EDGE_ILLEGAL", codes)
        self.assertIn("HOLONOMY_STRICT_FAIL", codes)
        self.assertIn("HOLONOMY_DERIVED_NOT_CONSTRUCTED", codes)
        self.assertNotIn("HOLONOMY_DERIVED_PASS", codes)
        self.assertNotIn("HOLONOMY_DERIVED_FAIL", codes)

    def test_non_surjective_projection_is_rejected(self):
        raw = self.load("holonomy_observed_quotient_pass.json")
        raw["transports"]["observe"]["maps"]["0"] = [[0, 0]]
        codes = {finding.code for finding in audit_holonomy_document(raw)}
        self.assertIn("OBSERVATION_PROJECTION_NOT_SURJECTIVE", codes)
        self.assertNotIn("HOLONOMY_OBSERVED_DERIVED_PASS", codes)

    def test_semantic_basis_digest_is_replayed(self):
        raw = self.load("holonomy_contractible_derived_pass.json")
        raw["contexts"]["C"]["basis"]["0"][0]["meaning"] = "silently changed"
        codes = {finding.code for finding in audit_holonomy_document(raw)}
        self.assertIn("SEMANTIC_BASIS_HASH", codes)

    def test_arbitrary_length_path_relation(self):
        semantic = basis("v", "intermediate path witness")
        raw = {
            "holonomy_version": "0.1.0",
            "field": "Q",
            "contexts": {
                name: {"groups": {"0": 1}, "differentials": {}, "basis": {"0": [semantic]}}
                for name in ("A", "B", "C", "D")
            },
            "transports": {
                "ab": {"source": "A", "target": "B", "maps": {"0": [[1]]}},
                "bc": {"source": "B", "target": "C", "maps": {"0": [[1]]}},
                "cd": {"source": "C", "target": "D", "maps": {"0": [[1]]}},
                "ad": {"source": "A", "target": "D", "maps": {"0": [[1]]}},
            },
            "relations": {
                "three_edges": {
                    "left_path": ["ab", "bc", "cd"],
                    "right_path": ["ad"],
                    "required_equivalence": "strict",
                }
            },
        }
        codes = {finding.code for finding in audit_holonomy_document(raw)}
        self.assertIn("HOLONOMY_STRICT_PASS", codes)

    def test_flattened_system_resource_cap_is_fail_closed(self):
        source_basis = [basis(f"c{i}", f"source coordinate {i}") for i in range(12)]
        target_zero_basis = [basis("d0", "target degree zero")]
        target_one_basis = [basis(f"d{i}", f"target degree one {i}") for i in range(12)]
        raw = {
            "holonomy_version": "0.1.0",
            "field": "Q",
            "contexts": {
                "C": {"groups": {"0": 12}, "differentials": {}, "basis": {"0": source_basis}},
                "D": {"groups": {"0": 1, "1": 12}, "differentials": {}, "basis": {"0": target_zero_basis, "1": target_one_basis}},
            },
            "transports": {
                "left": {"source": "C", "target": "D", "maps": {"0": [[0] * 12]}},
                "right": {"source": "C", "target": "D", "maps": {"0": [[0] * 12]}},
            },
            "relations": {
                "large": {"left_path": ["left"], "right_path": ["right"], "required_equivalence": "derived"}
            },
        }
        codes = {finding.code for finding in audit_holonomy_document(raw)}
        self.assertIn("HOLONOMY_RESOURCE_LIMIT", codes)

    def test_equation_cap_is_checked_before_coefficient_allocation(self):
        source_basis = [basis(f"c{i}", f"equation source {i}") for i in range(12)]
        target_basis = [basis(f"d{i}", f"equation target {i}") for i in range(12)]
        raw = {
            "holonomy_version": "0.1.0",
            "field": "Q",
            "contexts": {
                "C": {"groups": {"0": 12}, "differentials": {}, "basis": {"0": source_basis}},
                "D": {"groups": {"0": 12}, "differentials": {}, "basis": {"0": target_basis}},
            },
            "transports": {
                "left": {"source": "C", "target": "D", "maps": {"0": [[0] * 12 for _ in range(12)]}},
                "right": {"source": "C", "target": "D", "maps": {"0": [[0] * 12 for _ in range(12)]}},
            },
            "relations": {
                "large": {"left_path": ["left"], "right_path": ["right"], "required_equivalence": "derived"}
            },
        }
        messages = [finding.message for finding in audit_holonomy_document(raw) if finding.code == "HOLONOMY_RESOURCE_LIMIT"]
        self.assertEqual(messages, ["homotopy system exceeds 128 equations"])

    def test_repeated_dense_path_hits_document_composition_budget(self):
        dimension = 32
        semantic = [basis(f"v{i}", f"composition coordinate {i}") for i in range(dimension)]
        identity = [[int(row == column) for column in range(dimension)] for row in range(dimension)]
        raw = {
            "holonomy_version": "0.1.0",
            "field": "Q",
            "contexts": {
                "C": {"groups": {"0": dimension}, "differentials": {}, "basis": {"0": semantic}}
            },
            "transports": {
                "loop": {"source": "C", "target": "C", "maps": {"0": identity}}
            },
            "relations": {
                "expensive": {
                    "left_path": ["loop"] * 128,
                    "right_path": ["loop"],
                    "required_equivalence": "strict",
                }
            },
        }
        messages = [finding.message for finding in audit_holonomy_document(raw) if finding.code == "HOLONOMY_RESOURCE_LIMIT"]
        self.assertEqual(messages, ["path composition exceeds 1000000 scalar products per document"])

    def test_path_composition_bit_growth_is_bounded(self):
        value = 10**200
        raw = {
            "holonomy_version": "0.1.0",
            "field": "Q",
            "contexts": {
                "C": {"groups": {"0": 1}, "differentials": {}, "basis": {"0": [basis("v", "bit-growth coordinate")]}}
            },
            "transports": {
                "loop": {"source": "C", "target": "C", "maps": {"0": [[value]]}}
            },
            "relations": {
                "growth": {
                    "left_path": ["loop"] * 16,
                    "right_path": ["loop"],
                    "required_equivalence": "strict",
                }
            },
        }
        messages = [finding.message for finding in audit_holonomy_document(raw) if finding.code == "HOLONOMY_RESOURCE_LIMIT"]
        self.assertEqual(messages, ["path-composition intermediate exceeds 8192 bits"])

    def test_153_small_two_term_cases_match_induced_homology(self):
        values = (-1, 0, 1)
        checked = 0
        for a in values:
            for b in values:
                source = ChainComplex("C", {0: 1, 1: 1}, {1: Matrix.from_nested([[a]])})
                target = ChainComplex("D", {0: 1, 1: 1}, {1: Matrix.from_nested([[b]])})
                for f0 in values:
                    for f1 in values:
                        if b * f1 != f0 * a:
                            continue
                        for g0 in values:
                            for g1 in values:
                                if b * g1 != g0 * a:
                                    continue
                                omega = {
                                    0: Matrix.from_nested([[f0 - g0]]),
                                    1: Matrix.from_nested([[f1 - g1]]),
                                }
                                matrix, rhs, _equations, _variables = _homotopy_system(source, target, omega)
                                actual = solve_exact(matrix, rhs).consistent
                                expected = not (a == 0 and b == 0) or (f0 == g0 and f1 == g1)
                                self.assertEqual(actual, expected, (a, b, f0, f1, g0, g1))
                                checked += 1
        self.assertEqual(checked, 153)


if __name__ == "__main__":
    unittest.main()
