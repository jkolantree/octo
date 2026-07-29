from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from bsc_audit.theorem import (
    MAX_VARIABLES,
    audit_theorem_certificate,
    canonical_formal_title,
    canonical_formal_statement,
    load_and_replay_theorem_certificate,
    replay_theorem_certificate,
)
from bsc_audit.schema_validation import validate_route_schema


def const(value: object) -> dict[str, object]:
    return {"op": "const", "value": value}


def var(name: str) -> dict[str, object]:
    return {"op": "var", "name": name}


def add(*args: dict[str, object]) -> dict[str, object]:
    return {"op": "add", "args": list(args)}


def mul(*args: dict[str, object]) -> dict[str, object]:
    return {"op": "mul", "args": list(args)}


def power(base: dict[str, object], exponent: int) -> dict[str, object]:
    return {"op": "pow", "base": base, "exponent": exponent}


class TheoremCertificateTests(unittest.TestCase):
    def positive_certificate(self) -> dict[str, object]:
        x = var("x")
        y = var("y")
        return {
            "certificate_version": "0.1.0",
            "claim_id": "bsc:test:binomial-identity",
            "formal_statement": {
                "language": "q-polynomial-identity-v0.1",
                "field": "Q",
                "variables": ["x", "y"],
                "relation": {
                    "op": "eq",
                    "left": power(add(x, y), 2),
                    "right": add(
                        power(x, 2),
                        mul(const(2), x, y),
                        power(y, 2),
                    ),
                },
            },
            "residual": [],
        }

    def negative_certificate(self) -> dict[str, object]:
        x = var("x")
        return {
            "certificate_version": "0.1.0",
            "claim_id": "bsc:test:false-polynomial-identity",
            "formal_statement": {
                "language": "q-polynomial-identity-v0.1",
                "field": "Q",
                "variables": ["x"],
                "relation": {
                    "op": "eq",
                    "left": power(add(x, const(1)), 2),
                    "right": add(power(x, 2), const(1)),
                },
            },
            "residual": [{"powers": [1], "coefficient": 2}],
        }

    def test_binomial_identity_replays_exactly(self):
        certificate = self.positive_certificate()
        replay = replay_theorem_certificate(certificate)
        self.assertTrue(replay.valid)
        self.assertEqual(replay.result, "pass")
        self.assertEqual(replay.residual_json(), [])
        self.assertEqual(replay.findings[0].code, "THEOREM_IDENTITY_REPLAYED")
        self.assertFalse(
            any(
                finding.severity.value in {"ERROR", "BLOCKED", "DEMOTION"}
                for finding in audit_theorem_certificate(certificate)
            )
        )

    def test_canonical_projection_and_authority_boundary_are_explicit(self):
        certificate = self.positive_certificate()
        expected = (
            "Q[x,y] polynomial identity: ((x + y)^2) = "
            "((x^2) + (2 * x * y) + (y^2))"
        )
        expected_title = "Exact polynomial identity in Q[x,y]"
        self.assertEqual(
            canonical_formal_title(certificate["formal_statement"]),
            expected_title,
        )
        self.assertEqual(
            canonical_formal_statement(certificate["formal_statement"]),
            expected,
        )
        witness = replay_theorem_certificate(certificate).findings[0].witness
        self.assertEqual(witness["canonical_formal_title"], expected_title)
        self.assertEqual(witness["canonical_formal_statement"], expected)
        self.assertEqual(witness["authority"], "bsc_internal_exact_replay")
        self.assertEqual(
            witness["authority_scope"],
            "canonical_formal_statement_only",
        )
        self.assertEqual(witness["human_gloss"], "non_admissible")
        self.assertEqual(witness["scientific_truth"], "not_established")
        self.assertEqual(witness["deployment_authority"], "not_granted")

    def test_canonical_projection_parenthesizes_signed_rationals(self):
        statement = {
            "language": "q-polynomial-identity-v0.1",
            "field": "Q",
            "variables": [],
            "relation": {
                "op": "eq",
                "left": power(
                    const("-1/2"),
                    2,
                ),
                "right": const("1/4"),
            },
        }
        self.assertEqual(
            canonical_formal_title(statement),
            "Exact polynomial identity in Q",
        )
        self.assertEqual(
            canonical_formal_statement(statement),
            "Q polynomial identity: ((-1/2)^2) = (1/4)",
        )

    def test_nonidentity_has_a_replayable_coefficient_countercertificate(self):
        replay = replay_theorem_certificate(self.negative_certificate())
        self.assertTrue(replay.valid)
        self.assertEqual(replay.result, "fail")
        self.assertEqual(
            replay.residual_json(),
            [{"powers": [1], "coefficient": 2}],
        )
        self.assertEqual(replay.findings[0].code, "THEOREM_IDENTITY_REFUTED")
        self.assertEqual(replay.findings[0].severity.value, "DEMOTION")

    def test_forged_empty_residual_is_rejected(self):
        certificate = self.negative_certificate()
        certificate["residual"] = []
        replay = replay_theorem_certificate(certificate)
        self.assertFalse(replay.valid)
        self.assertIsNone(replay.result)
        self.assertEqual(
            replay.findings[0].code,
            "THEOREM_CERTIFICATE_RESIDUAL_MISMATCH",
        )

    def test_claim_binding_mismatch_is_not_admissible(self):
        replay = replay_theorem_certificate(
            self.positive_certificate(),
            expected_claim_id="bsc:test:different-claim",
        )
        self.assertFalse(replay.valid)
        self.assertIsNone(replay.result)
        self.assertEqual(
            replay.findings[0].code,
            "THEOREM_CERTIFICATE_CLAIM_MISMATCH",
        )
        self.assertEqual(replay.findings[0].severity.value, "BLOCKED")

    def test_formal_statement_swap_is_not_admissible(self):
        expected = copy.deepcopy(self.positive_certificate()["formal_statement"])
        expected["relation"]["right"] = const(0)
        replay = replay_theorem_certificate(
            self.positive_certificate(),
            expected_formal_statement=expected,
        )
        self.assertFalse(replay.valid)
        self.assertEqual(
            replay.findings[0].code,
            "THEOREM_CERTIFICATE_STATEMENT_MISMATCH",
        )

    def test_float_and_noncanonical_rational_are_forbidden(self):
        for value in (0.5, "2/4", "1/1"):
            with self.subTest(value=value):
                certificate = self.positive_certificate()
                certificate["formal_statement"]["relation"]["right"] = const(value)
                certificate["residual"] = []
                replay = replay_theorem_certificate(certificate)
                self.assertFalse(replay.valid)
                self.assertEqual(
                    replay.findings[0].code,
                    "THEOREM_CERTIFICATE_INVALID",
                )

    def test_unknown_operator_and_negative_exponent_are_forbidden(self):
        mutations = (
            {"op": "div", "args": [var("x"), const(2)]},
            power(var("x"), -1),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                certificate = self.positive_certificate()
                certificate["formal_statement"]["relation"]["left"] = mutation
                replay = replay_theorem_certificate(certificate)
                self.assertFalse(replay.valid)
                self.assertEqual(
                    replay.findings[0].code,
                    "THEOREM_CERTIFICATE_INVALID",
                )

    def test_undeclared_or_unsorted_variables_are_forbidden(self):
        undeclared = self.positive_certificate()
        undeclared["formal_statement"]["relation"]["left"] = var("z")
        replay = replay_theorem_certificate(undeclared)
        self.assertFalse(replay.valid)
        self.assertEqual(replay.findings[0].code, "THEOREM_CERTIFICATE_INVALID")

        unsorted = self.positive_certificate()
        unsorted["formal_statement"]["variables"] = ["y", "x"]
        replay = replay_theorem_certificate(unsorted)
        self.assertFalse(replay.valid)
        self.assertEqual(replay.findings[0].code, "THEOREM_CERTIFICATE_INVALID")

    def test_resource_limits_fail_closed(self):
        certificate = self.positive_certificate()
        variables = [f"x{index}" for index in range(MAX_VARIABLES + 1)]
        certificate["formal_statement"]["variables"] = variables
        replay = replay_theorem_certificate(certificate)
        self.assertFalse(replay.valid)
        self.assertIsNone(replay.result)
        self.assertEqual(replay.findings[0].code, "THEOREM_RESOURCE_LIMIT")

    def test_compact_dense_expression_hits_arithmetic_budget(self):
        certificate = self.positive_certificate()
        dense = add(const(1), var("x"))
        for _ in range(3):
            dense = power(dense, 16)
        certificate["formal_statement"] = {
            "language": "q-polynomial-identity-v0.1",
            "field": "Q",
            "variables": ["x"],
            "relation": {
                "op": "eq",
                "left": dense,
                "right": const(0),
            },
        }
        certificate["residual"] = []
        replay = replay_theorem_certificate(certificate)
        self.assertFalse(replay.valid)
        self.assertIsNone(replay.result)
        self.assertEqual(replay.findings[0].code, "THEOREM_RESOURCE_LIMIT")
        self.assertIn("arithmetic operations", replay.findings[0].message)

    def test_closed_top_level_contract_rejects_authority_smuggling(self):
        certificate = self.positive_certificate()
        certificate["authority"] = "non_admissive_declaration_provenance"
        replay = replay_theorem_certificate(certificate)
        self.assertFalse(replay.valid)
        self.assertEqual(replay.findings[0].code, "THEOREM_CERTIFICATE_INVALID")

    def test_local_loader_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            replay = load_and_replay_theorem_certificate(
                Path(directory),
                "../certificate.json",
            )
        self.assertFalse(replay.valid)
        self.assertEqual(
            replay.findings[0].code,
            "THEOREM_CERTIFICATE_PATH_UNSAFE",
        )

    def test_local_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            certificate = json.dumps(self.positive_certificate())
            duplicate = certificate.replace(
                '"certificate_version": "0.1.0",',
                '"certificate_version": "0.1.0", '
                '"certificate_version": "0.1.0",',
                1,
            )
            (root / "certificate.json").write_text(
                duplicate,
                encoding="utf-8",
            )
            replay = load_and_replay_theorem_certificate(
                root,
                "certificate.json",
            )
        self.assertFalse(replay.valid)
        self.assertEqual(
            replay.findings[0].code,
            "THEOREM_CERTIFICATE_INVALID",
        )

    def test_local_loader_rechecks_the_exact_hash_before_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "certificate.json").write_text(
                json.dumps(self.positive_certificate()),
                encoding="utf-8",
            )
            replay = load_and_replay_theorem_certificate(
                root,
                "certificate.json",
                expected_sha256="sha256:" + "1" * 64,
            )
        self.assertFalse(replay.valid)
        self.assertEqual(
            replay.findings[0].code,
            "THEOREM_CERTIFICATE_BYTES_CHANGED",
        )

    def test_nested_tagged_terms_validate_without_branch_explosion(self):
        certificate = self.positive_certificate()
        nested = var("x")
        for _ in range(24):
            nested = add(nested, const(0))
        certificate["formal_statement"] = {
            "language": "q-polynomial-identity-v0.1",
            "field": "Q",
            "variables": ["x"],
            "relation": {
                "op": "eq",
                "left": nested,
                "right": var("x"),
            },
        }
        certificate["residual"] = []
        self.assertEqual(validate_route_schema("theorem", certificate), [])
        replay = replay_theorem_certificate(certificate)
        self.assertTrue(replay.valid)
        self.assertEqual(replay.result, "pass")


if __name__ == "__main__":
    unittest.main()
