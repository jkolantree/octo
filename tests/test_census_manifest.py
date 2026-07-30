from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from bsc_audit.census import (
    CENSUS_AUTHORITY,
    CENSUS_AUTHORITY_SCOPE,
    CENSUS_GATE_ID,
    CENSUS_PROFILE_SCOPE,
    LANGUAGE,
    canonical_formal_statement,
    canonical_formal_title,
)
from bsc_audit.cli import audit_claim
from bsc_audit.manifest import replayed_census_evidence
from bsc_audit.provenance import sha256_bytes, sha256_json


HASHES = {
    "frame_denotes_target_population": "sha256:" + "1" * 64,
    "unit_identity_authentic": "sha256:" + "2" * 64,
    "measurement_enclosures_sound": "sha256:" + "3" * 64,
    "guard_band_scientifically_adequate": "sha256:" + "4" * 64,
}


class CensusManifestTests(unittest.TestCase):
    def certificate(self) -> dict[str, object]:
        population = {
            "coverage": "census",
            "declared_size": 2,
            "unit_ids": ["u1", "u2"],
        }
        return {
            "certificate_version": "0.1.0",
            "claim_id": "bsc:test:census-bound",
            "formal_statement": {
                "language": LANGUAGE,
                "field": "Q",
                "frame_sha256": sha256_json(population),
                "observables": ["x", "y"],
                "coefficients": {"x": 2, "y": -1},
                "relation": {"op": "le", "bound": 10},
                "required_guard_band": 1,
                "external_premises": HASHES,
            },
            "population": population,
            "observations": [
                {
                    "unit_id": "u1",
                    "intervals": {
                        "x": {"lower": 1, "upper": 2},
                        "y": {"lower": 0, "upper": 1},
                    },
                },
                {
                    "unit_id": "u2",
                    "intervals": {
                        "x": {"lower": 2, "upper": 3},
                        "y": {"lower": 1, "upper": 2},
                    },
                },
            ],
            "declared_result": "pass",
        }

    def manifest(self, root: Path) -> dict[str, object]:
        certificate = self.certificate()
        payload = (
            json.dumps(
                certificate,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        (root / "census.json").write_bytes(payload)
        formal_statement = certificate["formal_statement"]
        assert isinstance(formal_statement, dict)
        claim_id = certificate["claim_id"]
        return {
            "manifest_version": "0.5.0",
            "draft": False,
            "claim": {
                "id": claim_id,
                "title": canonical_formal_title(formal_statement),
                "type": "empirical_claim",
                "evidence_maturity": "empirically_passed",
                "deployment_status": "research_only",
                "statement": canonical_formal_statement(formal_statement),
                "scope": CENSUS_PROFILE_SCOPE,
                "family": LANGUAGE,
                "formal_statement": formal_statement,
            },
            "system": {
                "domain": "declared finite population",
                "state_type": "rational measurement enclosures",
            },
            "observation": {
                "kernel_or_instrument": "hash-identified measurement contract",
                "legal_filtration": {},
            },
            "representation": {"kind": "rational_interval_boxes"},
            "target": {
                "outcome": "finite-population affine upper bound",
                "horizon": "bound observation window",
                "loss_or_score": "exact inequality with positive guard band",
            },
            "experiment": {
                "baseline_model": "no sampling or parametric model",
                "search_budget": "complete declared census",
            },
            "admission": {
                "hard_gates": [CENSUS_GATE_ID],
                "gate_results": [
                    {
                        "id": CENSUS_GATE_ID,
                        "state": "pass",
                        "fatal": True,
                        "evidence": ["evidence:census"],
                    }
                ],
            },
            "demotion": {
                "owner": "maintainer",
                "rules": [
                    {
                        "if": "frame, observation, or premise identity changes",
                        "then": "replay under a new evidence identity",
                    }
                ],
                "negative_result_destination": "negative-results/",
            },
            "preservation": {
                "known_failures": [
                    "external premise truth is not established by the replay"
                ]
            },
            "evidence": [
                {
                    "id": "evidence:census",
                    "kind": "empirical_certificate",
                    "status": "verified",
                    "result": "pass",
                    "artifact": "census.json",
                    "sha256": sha256_bytes(payload),
                    "verifies_gates": [CENSUS_GATE_ID],
                    "verifies_claims": [claim_id],
                }
            ],
            "dependency_graph": {
                "root": claim_id,
                "nodes": [CENSUS_GATE_ID, claim_id],
                "edges": [{"source": CENSUS_GATE_ID, "target": claim_id}],
            },
        }

    def test_registered_census_pass_advances_empirical_maturity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.manifest(root)
            findings = audit_claim(raw, root)
            judgments, replay_findings = replayed_census_evidence(raw, root)

        self.assertFalse(
            any(
                finding.severity.value in {"ERROR", "BLOCKED", "DEMOTION"}
                for finding in findings
            ),
            [finding.to_dict() for finding in findings],
        )
        self.assertTrue(
            any(finding.code == "CENSUS_BOUND_REPLAYED" for finding in findings)
        )
        self.assertTrue(
            any(
                finding.code == "CENSUS_BOUND_REPLAYED"
                for finding in replay_findings
            )
        )
        judgment = judgments["evidence:census"]
        self.assertEqual(judgment.predicate, CENSUS_GATE_ID)
        self.assertEqual(judgment.scope, CENSUS_AUTHORITY_SCOPE)
        self.assertEqual(judgment.method_id, LANGUAGE)
        self.assertEqual(judgment.authority, CENSUS_AUTHORITY)
        self.assertEqual(judgment.result, "pass")

    def test_hash_only_empirical_record_remains_nonsemantic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.manifest(root)
            raw["evidence"][0]["kind"] = "experimental_record"
            findings = audit_claim(raw, root)

        codes = {finding.code for finding in findings}
        self.assertIn("EMPIRICAL_EVIDENCE_MISSING", codes)
        self.assertIn("CENSUS_CERTIFICATE_MISSING", codes)
        self.assertIn("GATE_RESULT_UNVERIFIED", codes)

    def test_census_replay_cannot_raise_maturity_without_gate_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.manifest(root)
            raw["evidence"][0]["verifies_gates"] = []
            raw["admission"]["gate_results"][0].update(
                {"state": "unrun", "evidence": []}
            )
            findings = audit_claim(raw, root)

        codes = {finding.code for finding in findings}
        self.assertTrue(
            {
                "CENSUS_EVIDENCE_GATE_BINDING_MISSING",
                "CENSUS_CERTIFICATE_MISSING",
                "EVIDENCE_MATURITY_UNSUPPORTED",
                "EMPIRICAL_EVIDENCE_MISSING",
            }.issubset(codes)
        )
        self.assertNotIn("CENSUS_BOUND_REPLAYED", codes)
        self.assertNotIn("MANIFEST_STRUCTURALLY_VALID", codes)

    def test_boundary_only_result_cannot_promote_empirical_maturity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.manifest(root)
            certificate = json.loads((root / "census.json").read_text("utf-8"))
            certificate["observations"][1]["intervals"]["x"]["upper"] = "11/2"
            certificate["declared_result"] = "inconclusive"
            payload = (
                json.dumps(certificate, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            (root / "census.json").write_bytes(payload)
            raw["evidence"][0]["sha256"] = sha256_bytes(payload)
            raw["evidence"][0]["result"] = "inconclusive"
            raw["admission"]["gate_results"][0]["state"] = "unrun"
            findings = audit_claim(raw, root)

        codes = {finding.code for finding in findings}
        self.assertIn("CENSUS_BOUND_INCONCLUSIVE", codes)
        self.assertIn("EMPIRICAL_EVIDENCE_MISSING", codes)
        self.assertFalse(
            any(finding.code == "MANIFEST_STRUCTURALLY_VALID" for finding in findings)
        )

    def test_census_replay_grants_no_deployment_or_replication_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            admitted = self.manifest(root)
            admitted["claim"]["deployment_status"] = "admitted"
            admitted_findings = audit_claim(admitted, root)

            replicated = deepcopy(self.manifest(root))
            replicated["claim"]["evidence_maturity"] = "externally_replicated"
            replicated_findings = audit_claim(replicated, root)

        self.assertTrue(
            any(
                finding.code == "SCHEMA_VALIDATION"
                and finding.path == "$.claim.deployment_status"
                for finding in admitted_findings
            )
        )
        self.assertTrue(
            any(
                finding.code == "SCHEMA_VALIDATION"
                and finding.path == "$.claim.evidence_maturity"
                for finding in replicated_findings
            )
        )


if __name__ == "__main__":
    unittest.main()
