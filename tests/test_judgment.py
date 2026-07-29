from __future__ import annotations

import unittest
from dataclasses import replace

from bsc_audit.gates import _bound_evidence_is_valid
from bsc_audit.judgment import CheckedJudgment
from bsc_audit.plugins import arithmetic_trace_findings, recovery_findings


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
OBLIGATIONS = (
    "self_adjointness",
    "trace_class_resolvent",
    "exact_prime_increment",
    "joint_trace_norm_cauchy",
    "atomic_rigidity",
)


class CheckedJudgmentTests(unittest.TestCase):
    def judgment(self, **changes: str) -> CheckedJudgment:
        values = {
            "subject_id": "claim:trace:test",
            "subject_sha256": SHA_A,
            "predicate": "arithmetic_trace:self_adjointness",
            "scope": "declared_arithmetic_trace_obligation_only",
            "method_id": "arithmetic-trace-obligation-v0.1",
            "evidence_id": "evidence:self-adjointness",
            "evidence_sha256": SHA_B,
            "authority": "bsc_registered_arithmetic_trace_replay",
            "result": "pass",
        }
        values.update(changes)
        return CheckedJudgment(**values)

    def test_support_requires_every_authority_coordinate(self) -> None:
        judgment = self.judgment()
        expected = {
            "subject_id": judgment.subject_id,
            "subject_sha256": judgment.subject_sha256,
            "predicate": judgment.predicate,
            "scope": judgment.scope,
            "method_id": judgment.method_id,
            "evidence_id": judgment.evidence_id,
            "evidence_sha256": judgment.evidence_sha256,
            "authority": judgment.authority,
            "result": judgment.result,
        }
        self.assertTrue(judgment.supports(**expected))
        for field in expected:
            with self.subTest(field=field):
                changed = dict(expected)
                changed[field] = "fail" if field == "result" else f"wrong:{field}"
                self.assertFalse(judgment.supports(**changed))

    def test_invalid_hash_identity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "subject_sha256"):
            self.judgment(subject_sha256="not-a-hash")
        with self.assertRaisesRegex(ValueError, "evidence_sha256"):
            self.judgment(evidence_sha256="not-a-hash")

    def test_nonstring_and_blank_coordinates_are_rejected(self) -> None:
        for field, value in {
            "subject_id": 1,
            "predicate": {},
            "scope": [],
            "method_id": True,
            "evidence_id": 17,
            "authority": "   ",
        }.items():
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    self.judgment(**{field: value})  # type: ignore[arg-type]

    def test_gate_rechecks_every_judgment_coordinate(self) -> None:
        evidence_id = "evidence:theorem"
        judgment = CheckedJudgment(
            subject_id="claim:theorem",
            subject_sha256=SHA_A,
            predicate="exact_polynomial_identity",
            scope="canonical_formal_statement_only",
            method_id="q-polynomial-identity-v0.1",
            evidence_id=evidence_id,
            evidence_sha256=SHA_B,
            authority="bsc_internal_exact_replay",
            result="pass",
        )
        records = {
            evidence_id: {
                "kind": "exact_certificate",
                "sha256": SHA_B,
                "verifies_gates": ["exact_polynomial_identity"],
            }
        }
        arguments = (
            "exact_polynomial_identity",
            "pass",
            [evidence_id],
            records,
            {evidence_id},
        )
        valid, computed, _ = _bound_evidence_is_valid(
            *arguments,
            {evidence_id: judgment},
            "theorem_schema",
            "claim:theorem",
            SHA_A,
        )
        self.assertTrue(valid)
        self.assertEqual(computed, "pass")

        mutations = {
            "subject_id": "claim:other",
            "subject_sha256": "sha256:" + "c" * 64,
            "predicate": "other_predicate",
            "scope": "other_scope",
            "method_id": "other_method",
            "evidence_id": "evidence:other",
            "evidence_sha256": "sha256:" + "d" * 64,
            "authority": "other_authority",
            "result": "fail",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                forged = replace(judgment, **{field: value})
                valid, computed, _ = _bound_evidence_is_valid(
                    *arguments,
                    {evidence_id: forged},
                    "theorem_schema",
                    "claim:theorem",
                    SHA_A,
                )
                self.assertFalse(valid)
                self.assertNotEqual((valid, computed), (True, "pass"))

    def test_arithmetic_plugin_accepts_no_external_judgment_registry(self) -> None:
        raw = self.trace_claim()
        evidence_id = raw["evidence"][0]["id"]
        forged = self.judgment(evidence_id=evidence_id)
        with self.assertRaises(TypeError):
            arithmetic_trace_findings(raw, {evidence_id: forged})  # type: ignore[call-arg]

    def test_caller_constructed_trace_judgments_remain_non_admissive(self) -> None:
        raw = self.trace_claim()
        raw["evidence"] = []
        bindings = {}
        for index, obligation in enumerate(OBLIGATIONS):
            evidence_id = f"evidence:{obligation}"
            raw["evidence"].append({"id": evidence_id})
            evidence_sha256 = "sha256:" + f"{index + 1:x}" * 64
            raw["evidence"][-1]["sha256"] = evidence_sha256
            bindings[obligation] = [evidence_id]
        raw["domain_checks"]["arithmetic_trace"]["obligation_evidence"] = bindings

        findings = arithmetic_trace_findings(raw)

        rejected = [
            finding
            for finding in findings
            if finding.code == "TRACE_OBLIGATION_EVIDENCE_UNVERIFIED"
        ]
        self.assertEqual(len(rejected), len(OBLIGATIONS))
        self.assertTrue(
            all(
                finding.code == "TRACE_OBLIGATION_EVIDENCE_UNVERIFIED"
                for finding in rejected
            )
        )

    def test_global_recovery_rejects_truthy_non_boolean_flags(self) -> None:
        raw = {
            "domain_checks": {
                "global_recovery": {
                    "local_nondegenerate": "false",
                    "claims_global_recovery": "false",
                    "fiber_unique": "false",
                    "boundary_complete": "false",
                }
            }
        }

        findings = recovery_findings(raw)

        self.assertEqual(len(findings), 4)
        self.assertTrue(
            all(
                finding.code == "GLOBAL_RECOVERY_FLAG_TYPE"
                and finding.severity.value == "ERROR"
                for finding in findings
            )
        )

    def test_global_recovery_truth_table_requires_global_certificates(self) -> None:
        cases = (
            (False, False, False, False, False),
            (True, False, False, False, False),
            (False, True, False, False, True),
            (True, True, False, False, True),
            (False, True, True, True, False),
            (True, True, True, True, False),
        )
        for local, claims, fiber, boundary, blocked in cases:
            with self.subTest(
                local=local,
                claims=claims,
                fiber=fiber,
                boundary=boundary,
            ):
                raw = {
                    "domain_checks": {
                        "global_recovery": {
                            "local_nondegenerate": local,
                            "claims_global_recovery": claims,
                            "fiber_unique": fiber,
                            "boundary_complete": boundary,
                        }
                    }
                }

                findings = recovery_findings(raw)

                observed = [
                    finding
                    for finding in findings
                    if finding.code == "LOCAL_GLOBAL_PROMOTION_FAILURE"
                ]
                self.assertEqual(bool(observed), blocked)

    def test_global_recovery_rejects_nonobject_domain_registry(self) -> None:
        findings = recovery_findings({"domain_checks": []})
        self.assertEqual(
            [(finding.code, finding.path) for finding in findings],
            [("DOMAIN_CHECKS_TYPE", "domain_checks")],
        )

    def test_arithmetic_plugin_rejects_unknown_obligations_and_nonstring_bindings(
        self,
    ) -> None:
        raw = self.trace_claim()
        config = raw["domain_checks"]["arithmetic_trace"]
        config["certified_obligations"].append("unknown_obligation")
        config["obligation_evidence"]["self_adjointness"] = [17]

        findings = arithmetic_trace_findings(raw)

        self.assertTrue(
            any(
                finding.code == "TRACE_OBLIGATION_UNREGISTERED"
                and finding.witness == ["unknown_obligation"]
                for finding in findings
            )
        )
        self.assertTrue(
            any(
                finding.code == "TRACE_EVIDENCE_BINDING_TYPE"
                and finding.path.endswith(".self_adjointness")
                for finding in findings
            )
        )

    @staticmethod
    def trace_claim() -> dict:
        evidence_id = "evidence:shared"
        return {
            "claim": {
                "id": "claim:trace:test",
                "family": "arithmetic_trace",
                "statement": "A typed arithmetic trace obligation.",
            },
            "evidence": [{"id": evidence_id, "sha256": SHA_B}],
            "domain_checks": {
                "arithmetic_trace": {
                    "model_dimension": "infinite",
                    "target": "distributional_prime_increment",
                    "uses_zero_ordinates": False,
                    "primary_gram_uses_zero_table": False,
                    "counterterm_singular_support": ["origin"],
                    "certified_obligations": list(OBLIGATIONS),
                    "obligation_evidence": {
                        obligation: [evidence_id] for obligation in OBLIGATIONS
                    },
                }
            },
        }


if __name__ == "__main__":
    unittest.main()
