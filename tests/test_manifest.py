import json
import tempfile
import unittest
from pathlib import Path

from bsc_audit.cli import audit_claim
from bsc_audit.manifest import lint_manifest
from bsc_audit.provenance import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def make_manifest(self, root: Path) -> dict:
        artifacts = {
            "proof.json": b'{"proof":"exact fixture"}\n',
            "source.txt": b"frozen source fixture\n",
            "code.py": b"print('fixture')\n",
        }
        for name, content in artifacts.items():
            (root / name).write_bytes(content)
        return {
            "manifest_version": "0.3.0",
            "draft": False,
            "claim": {
                "id": "bsc:test:claim",
                "title": "Exact fixture claim",
                "type": "definition",
                "evidence_maturity": "structurally_checked",
                "deployment_status": "sandboxed",
                "statement": "The frozen fixture satisfies its declared exact identity.",
                "scope": "frozen test fixture",
            },
            "system": {"domain": "finite exact states", "state_type": "rational vectors"},
            "observation": {"kernel_or_instrument": "identity", "legal_filtration": {}},
            "representation": {"kind": "identity"},
            "target": {"outcome": "exact identity", "horizon": "static", "loss_or_score": "equality"},
            "experiment": {"baseline_model": "exact fixture", "search_budget": "predeclared finite check"},
            "admission": {
                "hard_gates": ["exact_identity"],
                "gate_results": [
                    {"id": "exact_identity", "state": "pass", "fatal": True, "evidence": ["evidence:proof"]}
                ],
            },
            "demotion": {
                "owner": "maintainer",
                "rules": [{"if": "counterexample", "then": "retire"}],
                "negative_result_destination": "negative-results/",
            },
            "preservation": {
                "source_artifact": "source.txt",
                "source_hash": sha256_bytes(artifacts["source.txt"]),
                "code_artifact": "code.py",
                "code_hash": sha256_bytes(artifacts["code.py"]),
                "known_failures": ["fixture proves only its declared finite identity"],
            },
            "evidence": [
                {
                    "id": "evidence:proof",
                    "kind": "audit_report",
                    "status": "verified",
                    "result": "pass",
                    "artifact": "proof.json",
                    "sha256": sha256_bytes(artifacts["proof.json"]),
                    "verifies_gates": ["exact_identity"],
                    "verifies_claims": ["bsc:test:claim"],
                }
            ],
            "dependency_graph": {
                "root": "bsc:test:claim",
                "nodes": ["exact_identity", "bsc:test:claim"],
                "edges": [{"source": "exact_identity", "target": "bsc:test:claim"}],
            },
        }

    def test_valid_manifest_and_gate_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            findings = audit_claim(self.make_manifest(root), root)
        self.assertFalse(any(f.severity.value in {"ERROR", "BLOCKED", "DEMOTION"} for f in findings))
        self.assertTrue(any(f.code == "MANIFEST_STRUCTURALLY_VALID" for f in findings))

    def test_hash_bound_proof_cannot_admit_a_false_theorem(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["claim"].update(
                {
                    "type": "theorem",
                    "statement": "Every integer is even.",
                    "scope": "all integers",
                    "deployment_status": "admitted",
                }
            )
            raw["system"]["domain"] = "integers"
            raw["evidence"][0]["kind"] = "exact_certificate"
            findings = audit_claim(raw, root)
        blocked = next(
            finding
            for finding in findings
            if finding.code == "THEOREM_CERTIFICATE_MISSING"
        )
        self.assertEqual(
            blocked.witness,
            {"hash_bound_proof_evidence": ["evidence:proof"]},
        )
        self.assertEqual(blocked.severity.value, "BLOCKED")
        self.assertFalse(
            any(finding.code == "MANIFEST_STRUCTURALLY_VALID" for finding in findings)
        )
        gate = next(
            finding
            for finding in findings
            if finding.code == "GATE_RESULT_UNVERIFIED"
        )
        self.assertEqual(gate.witness["computed_state"], "unrun")
        self.assertEqual(
            gate.witness["hash_only_proof_evidence"],
            ["evidence:proof"],
        )

    def test_missing_demotion_is_malformed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["demotion"]["rules"] = []
            findings = lint_manifest(raw, root)
        self.assertTrue(any(f.code == "DEMOTION_RULES_MISSING" and f.severity.value == "ERROR" for f in findings))

    def test_unsupported_manifest_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["manifest_version"] = "0.2.0"
            findings = lint_manifest(raw, root)
        self.assertTrue(any(f.code == "MANIFEST_VERSION_UNSUPPORTED" for f in findings))

    def test_epistemic_status_is_not_part_of_v03(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["claim"]["epistemic_status"] = "checked"
            findings = lint_manifest(raw, root)
        self.assertTrue(any(f.code == "EPISTEMIC_STATUS_PROHIBITED" for f in findings))

    def test_draft_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["draft"] = True
            findings = lint_manifest(raw, root)
        self.assertTrue(any(f.code == "DRAFT_MANIFEST" and f.severity.value == "BLOCKED" for f in findings))

    def test_placeholder_and_zero_hash_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["demotion"]["owner"] = "unassigned"
            raw["preservation"]["source_hash"] = "sha256:" + "0" * 64
            findings = lint_manifest(raw, root)
        self.assertTrue(any(f.code == "DRAFT_PLACEHOLDER" for f in findings))
        self.assertTrue(any(f.code == "HASH_PLACEHOLDER" for f in findings))

    def test_hash_mismatch_blocks_verified_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["evidence"][0]["sha256"] = "sha256:" + "1" * 64
            findings = lint_manifest(raw, root)
        mismatch = next(f for f in findings if f.code == "EVIDENCE_ARTIFACT_UNVERIFIED")
        self.assertEqual(mismatch.witness["reason"], "hash_mismatch")

    def test_declared_evidence_rejects_dangling_or_placeholder_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["claim"]["type"] = "conjecture"
            raw["claim"]["evidence_maturity"] = "declared"
            raw["evidence"][0] = {
                "id": "evidence:declared",
                "kind": "audit_report",
                "status": "declared",
                "result": "inconclusive",
                "sha256": "sha256:" + "0" * 64,
                "verifies_gates": [],
            }
            findings = lint_manifest(raw, root)
        self.assertTrue(any(f.code == "EVIDENCE_ARTIFACT_PAIR" for f in findings))
        self.assertTrue(any(f.code == "HASH_PLACEHOLDER" for f in findings))

    def test_gate_pass_requires_verified_bound_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["evidence"][0]["verifies_gates"] = []
            findings = audit_claim(raw, root)
        self.assertTrue(any(f.code == "GATE_RESULT_UNVERIFIED" for f in findings))

    def test_admission_requires_all_verified_fatal_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["claim"]["deployment_status"] = "admitted"
            raw["admission"]["hard_gates"].append("boundary_accounting")
            raw["admission"]["gate_results"].append(
                {"id": "boundary_accounting", "state": "unrun", "fatal": True, "evidence": []}
            )
            findings = audit_claim(raw, root)
        self.assertTrue(any(f.code == "ADMISSION_WITHOUT_FATAL_PASSES" for f in findings))

    def test_verified_fatal_failure_propagates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["evidence"][0]["verifies_gates"] = []
            failure = b'{"counterexample":true}\n'
            (root / "failure.json").write_bytes(failure)
            raw["evidence"].append(
                {
                    "id": "evidence:failure",
                    "kind": "counterexample",
                    "status": "verified",
                    "result": "fail",
                    "artifact": "failure.json",
                    "sha256": sha256_bytes(failure),
                    "verifies_gates": ["exact_identity"],
                }
            )
            raw["admission"]["gate_results"][0] = {
                "id": "exact_identity",
                "state": "fail",
                "fatal": True,
                "evidence": ["evidence:failure"],
            }
            findings = audit_claim(raw, root)
        self.assertTrue(any(f.code == "FATAL_DEPENDENCY_PROPAGATION" for f in findings))

    def test_finite_prime_comb_plugin_still_demotes_typed_claim(self):
        raw = json.loads((ROOT / "examples" / "claim_arithmetic_no_go.json").read_text(encoding="utf-8"))
        raw["manifest_version"] = "0.3.0"
        raw["draft"] = False
        raw["claim"].pop("epistemic_status", None)
        raw["claim"]["evidence_maturity"] = "declared"
        raw["preservation"] = {"known_failures": ["exact finite realization is structurally impossible"]}
        raw["admission"]["gate_results"][0] = {
            "id": "exact_distributional_equality",
            "state": "unrun",
            "fatal": True,
            "evidence": [],
        }
        findings = audit_claim(raw)
        self.assertTrue(any(f.code == "FINITE_PRIME_COMB_NO_GO" and f.severity.value == "DEMOTION" for f in findings))

    def test_wrong_top_level_type_is_a_finding(self):
        raw = {field: {} for field in ("claim", "system", "observation", "representation", "target", "experiment", "admission", "demotion", "preservation")}
        raw.update({"manifest_version": "0.3.0", "draft": False})
        raw["claim"] = []
        findings = lint_manifest(raw)
        self.assertTrue(any(f.code == "MANIFEST_OBJECT_TYPE" for f in findings))


if __name__ == "__main__":
    unittest.main()
