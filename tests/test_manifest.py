import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import bsc_audit.manifest as manifest_module
from bsc_audit.cli import audit_claim
from bsc_audit.findings import decision
from bsc_audit.gates import audit_gate_product
from bsc_audit.manifest import (
    MAX_THEOREM_ARTIFACTS_PER_AUDIT,
    MAX_THEOREM_REPLAYS_PER_AUDIT,
    lint_manifest,
    replayed_theorem_evidence,
)
from bsc_audit.provenance import sha256_bytes
from bsc_audit.theorem import (
    FORMAL_ONLY_SCOPE,
    MAX_CERTIFICATE_BYTES,
    canonical_formal_title,
    canonical_formal_statement,
)


ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def make_polynomial_manifest(self, root: Path) -> dict:
        raw = json.loads(
            (ROOT / "examples" / "claim_polynomial_identity.json").read_text(
                encoding="utf-8"
            )
        )
        certificate = (
            ROOT / "examples" / "theorem_binomial_identity.json"
        ).read_bytes()
        (root / "theorem_binomial_identity.json").write_bytes(certificate)
        raw["evidence"][0]["sha256"] = sha256_bytes(certificate)
        raw["claim"]["title"] = canonical_formal_title(
            raw["claim"]["formal_statement"]
        )
        raw["claim"]["statement"] = canonical_formal_statement(
            raw["claim"]["formal_statement"]
        )
        raw["claim"]["scope"] = FORMAL_ONLY_SCOPE
        return raw

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

    def test_hash_verified_generic_result_is_provenance_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            findings = audit_claim(self.make_manifest(root), root)
        maturity = next(
            finding
            for finding in findings
            if finding.code == "EVIDENCE_MATURITY_UNSUPPORTED"
        )
        self.assertEqual(
            maturity.witness,
            {
                "verified_artifact_evidence": ["evidence:proof"],
                "registered_semantic_passes": [],
            },
        )
        gate = next(
            finding
            for finding in findings
            if finding.code == "GATE_RESULT_UNVERIFIED"
        )
        self.assertEqual(gate.witness["computed_state"], "unrun")
        self.assertEqual(
            gate.witness["nonsemantic_evidence"],
            ["evidence:proof"],
        )
        self.assertFalse(
            any(
                finding.code == "MANIFEST_STRUCTURALLY_VALID"
                for finding in findings
            )
        )

    def test_v04_scientific_title_laundering_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            raw["claim"]["title"] = (
                "Every cancer treatment is safe and effective for every patient"
            )
            findings = audit_claim(raw, root)

        title = next(
            finding
            for finding in findings
            if finding.code == "THEOREM_TITLE_NOT_CANONICAL"
        )
        self.assertEqual(title.path, "claim.title")
        self.assertEqual(
            title.witness["canonical_formal_title"],
            "Exact polynomial identity in Q[x,y]",
        )
        self.assertEqual(title.witness["scientific_truth"], "not_established")
        self.assertFalse(
            any(
                finding.code == "MANIFEST_STRUCTURALLY_VALID"
                for finding in findings
            )
        )

    def test_hash_matched_empirical_pass_cannot_admit_a_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["claim"]["type"] = "empirical_claim"
            raw["claim"]["evidence_maturity"] = "empirically_passed"
            raw["claim"]["deployment_status"] = "admitted"
            raw["evidence"][0]["kind"] = "experimental_record"
            findings = audit_claim(raw, root)

        codes = {finding.code for finding in findings}
        self.assertTrue(
            {
                "EVIDENCE_MATURITY_UNSUPPORTED",
                "EMPIRICAL_EVIDENCE_MISSING",
                "GATE_RESULT_UNVERIFIED",
                "ADMISSION_WITHOUT_FATAL_PASSES",
            }.issubset(codes)
        )
        gate = next(
            finding
            for finding in findings
            if finding.code == "GATE_RESULT_UNVERIFIED"
        )
        self.assertEqual(gate.witness["computed_state"], "unrun")
        self.assertEqual(
            gate.witness["nonsemantic_evidence"],
            ["evidence:proof"],
        )
        self.assertEqual(
            gate.witness["nonsemantic_declared_results"],
            {"evidence:proof": "pass"},
        )
        self.assertEqual(raw["evidence"][0]["result"], "pass")
        self.assertFalse(
            any(
                finding.code == "MANIFEST_STRUCTURALLY_VALID"
                for finding in findings
            )
        )

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

    def test_v04_exact_polynomial_theorem_replays_into_its_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            findings = audit_claim(self.make_polynomial_manifest(root), root)
        self.assertFalse(
            any(
                finding.severity.value in {"ERROR", "BLOCKED", "DEMOTION"}
                for finding in findings
            )
        )
        replay = next(
            finding
            for finding in findings
            if finding.code == "THEOREM_IDENTITY_REPLAYED"
        )
        self.assertEqual(
            replay.witness["evidence_id"],
            "evidence:binomial-normal-form",
        )
        self.assertFalse(
            any(
                finding.code
                in {"THEOREM_CERTIFICATE_MISSING", "GATE_RESULT_UNVERIFIED"}
                for finding in findings
            )
        )

    def test_v04_medical_gloss_status_and_replication_laundering_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            raw["claim"]["statement"] = (
                "Every cancer treatment described by this project is safe "
                "and effective for every patient."
            )
            raw["claim"]["scope"] = "all patients and all future deployment"
            raw["claim"]["evidence_maturity"] = "externally_replicated"
            raw["claim"]["deployment_status"] = "admitted"
            theorem_evidence = raw["evidence"][0]
            raw["evidence"].append(
                {
                    "id": "evidence:medical-replication",
                    "kind": "independent_replication",
                    "status": "verified",
                    "result": "pass",
                    "artifact": theorem_evidence["artifact"],
                    "sha256": theorem_evidence["sha256"],
                    "verifies_gates": [],
                    "verifies_claims": [raw["claim"]["id"]],
                }
            )
            findings = audit_claim(raw, root)

        codes = {finding.code for finding in findings}
        self.assertTrue(
            {
                "THEOREM_STATEMENT_NOT_CANONICAL",
                "THEOREM_SCOPE_NOT_FORMAL_ONLY",
                "THEOREM_MATURITY_OUT_OF_SCOPE",
                "THEOREM_DEPLOYMENT_OUT_OF_SCOPE",
                "EMPIRICAL_EVIDENCE_MISSING",
                "REPLICATION_EVIDENCE_MISSING",
            }.issubset(codes)
        )
        replay = next(
            finding
            for finding in findings
            if finding.code == "THEOREM_IDENTITY_REPLAYED"
        )
        self.assertEqual(
            replay.witness["replay_witness"]["scientific_truth"],
            "not_established",
        )
        self.assertEqual(
            replay.witness["replay_witness"]["authority_scope"],
            "canonical_formal_statement_only",
        )
        self.assertFalse(
            any(
                finding.code == "MANIFEST_STRUCTURALLY_VALID"
                for finding in findings
            )
        )

    def test_v04_forged_residual_is_not_semantically_admissible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            certificate_path = root / "theorem_binomial_identity.json"
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["residual"] = [{"powers": [0, 0], "coefficient": 1}]
            payload = (
                json.dumps(certificate, indent=2, ensure_ascii=False).encode("utf-8")
                + b"\n"
            )
            certificate_path.write_bytes(payload)
            raw["evidence"][0]["sha256"] = sha256_bytes(payload)
            findings = audit_claim(raw, root)
        self.assertTrue(
            any(
                finding.code == "THEOREM_CERTIFICATE_RESIDUAL_MISMATCH"
                for finding in findings
            )
        )
        self.assertTrue(
            any(
                finding.code == "THEOREM_CERTIFICATE_MISSING"
                for finding in findings
            )
        )
        self.assertFalse(
            any(
                finding.code == "MANIFEST_STRUCTURALLY_VALID"
                for finding in findings
            )
        )

    def test_v04_certificate_must_match_authoritative_statement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            raw["claim"]["formal_statement"]["relation"]["right"] = {
                "op": "const",
                "value": 0,
            }
            findings = audit_claim(raw, root)
        self.assertTrue(
            any(
                finding.code == "THEOREM_CERTIFICATE_STATEMENT_MISMATCH"
                for finding in findings
            )
        )

    def test_v04_declared_result_must_match_exact_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            raw["evidence"][0]["result"] = "fail"
            raw["admission"]["gate_results"][0]["state"] = "fail"
            findings = audit_claim(raw, root)
        mismatch = next(
            finding
            for finding in findings
            if finding.code == "THEOREM_EVIDENCE_RESULT_MISMATCH"
        )
        self.assertEqual(
            mismatch.witness,
            {
                "evidence_id": "evidence:binomial-normal-form",
                "declared": "fail",
                "computed": "pass",
                "formal_statement_sha256": "sha256:d13e48cd90e7990a5b176ec6d573c2462aa9022874cf737fb0dfde7d17318586",
            },
        )

    def test_v04_theorem_gate_rejects_nonsemantic_evidence_laundering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            raw["evidence"][0]["verifies_gates"] = []
            review = b'{"review":"looks good"}\n'
            (root / "review.json").write_bytes(review)
            raw["evidence"].append(
                {
                    "id": "evidence:informal-review",
                    "kind": "audit_report",
                    "status": "verified",
                    "result": "pass",
                    "artifact": "review.json",
                    "sha256": sha256_bytes(review),
                    "verifies_gates": ["exact_polynomial_identity"],
                    "verifies_claims": ["bsc:example:binomial-square"],
                }
            )
            raw["admission"]["gate_results"][0]["evidence"] = [
                "evidence:informal-review"
            ]
            findings = audit_claim(raw, root)
        gate = next(
            finding
            for finding in findings
            if finding.code == "GATE_RESULT_UNVERIFIED"
        )
        self.assertEqual(gate.witness["computed_state"], "unrun")
        self.assertEqual(
            gate.witness["nonsemantic_theorem_evidence"],
            ["evidence:informal-review"],
        )

    def test_v04_duplicate_certificate_aliases_verify_and_replay_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            template = raw["evidence"][0]
            raw["evidence"] = []
            for index in range(100):
                item = deepcopy(template)
                item["id"] = f"evidence:duplicate-{index:03d}"
                item["verifies_gates"] = (
                    ["exact_polynomial_identity"] if index == 0 else []
                )
                raw["evidence"].append(item)
            raw["admission"]["gate_results"][0]["evidence"] = [
                "evidence:duplicate-000"
            ]
            with (
                patch(
                    "bsc_audit.manifest.verify_local_artifact",
                    wraps=manifest_module.verify_local_artifact,
                ) as verify,
                patch(
                    "bsc_audit.manifest.load_and_replay_theorem_certificate",
                    wraps=manifest_module.load_and_replay_theorem_certificate,
                ) as replay,
            ):
                findings = audit_claim(raw, root)
        self.assertFalse(
            any(
                finding.severity.value in {"ERROR", "BLOCKED", "DEMOTION"}
                for finding in findings
            )
        )
        self.assertEqual(verify.call_count, 1)
        self.assertEqual(replay.call_count, 1)

    def test_v04_exact_certificate_hashing_uses_the_replay_size_ceiling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            payload = b" " * (MAX_CERTIFICATE_BYTES + 1)
            (root / "theorem_binomial_identity.json").write_bytes(payload)
            raw["evidence"][0]["sha256"] = sha256_bytes(payload)
            findings = lint_manifest(raw, root)
        unverified = next(
            finding
            for finding in findings
            if finding.code == "EVIDENCE_ARTIFACT_UNVERIFIED"
        )
        self.assertEqual(unverified.witness["reason"], "artifact_too_large")

    def test_v04_same_digest_across_paths_replays_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            template = raw["evidence"][0]
            payload = (root / template["artifact"]).read_bytes()
            raw["evidence"] = []
            for index in range(MAX_THEOREM_REPLAYS_PER_AUDIT):
                name = f"theorem-alias-{index:02d}.json"
                (root / name).write_bytes(payload)
                item = deepcopy(template)
                item["id"] = f"evidence:path-alias-{index:02d}"
                item["artifact"] = name
                item["verifies_gates"] = (
                    ["exact_polynomial_identity"] if index == 0 else []
                )
                raw["evidence"].append(item)
            raw["admission"]["gate_results"][0]["evidence"] = [
                "evidence:path-alias-00"
            ]
            with patch(
                "bsc_audit.manifest.load_and_replay_theorem_certificate",
                wraps=manifest_module.load_and_replay_theorem_certificate,
            ) as replay:
                findings = audit_claim(raw, root)
        self.assertFalse(
            any(
                finding.severity.value in {"ERROR", "BLOCKED", "DEMOTION"}
                for finding in findings
            )
        )
        self.assertEqual(replay.call_count, 1)

    def test_v04_unique_theorem_artifact_limit_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            template = raw["evidence"][0]
            payload = (root / template["artifact"]).read_bytes()
            raw["evidence"] = []
            for index in range(MAX_THEOREM_ARTIFACTS_PER_AUDIT + 1):
                name = f"theorem-path-{index:02d}.json"
                (root / name).write_bytes(payload)
                item = deepcopy(template)
                item["id"] = f"evidence:artifact-limit-{index:02d}"
                item["artifact"] = name
                item["verifies_gates"] = (
                    ["exact_polynomial_identity"] if index == 0 else []
                )
                raw["evidence"].append(item)
            raw["admission"]["gate_results"][0]["evidence"] = [
                "evidence:artifact-limit-00"
            ]
            findings = audit_claim(raw, root)
        limit = next(
            finding
            for finding in findings
            if finding.code == "THEOREM_RESOURCE_LIMIT"
            and finding.witness.get("reason") == "theorem_artifact_limit"
        )
        self.assertEqual(
            limit.witness["max_unique_artifacts"],
            MAX_THEOREM_ARTIFACTS_PER_AUDIT,
        )

    def test_v04_unique_theorem_replay_limit_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            template = raw["evidence"][0]
            certificate = json.loads(
                (root / template["artifact"]).read_text(encoding="utf-8")
            )
            raw["evidence"] = []
            for index in range(MAX_THEOREM_REPLAYS_PER_AUDIT + 1):
                name = f"theorem-variant-{index:02d}.json"
                payload = json.dumps(certificate).encode("utf-8") + b" " * index
                (root / name).write_bytes(payload)
                item = deepcopy(template)
                item["id"] = f"evidence:replay-limit-{index:02d}"
                item["artifact"] = name
                item["sha256"] = sha256_bytes(payload)
                item["verifies_gates"] = (
                    ["exact_polynomial_identity"] if index == 0 else []
                )
                raw["evidence"].append(item)
            raw["admission"]["gate_results"][0]["evidence"] = [
                "evidence:replay-limit-00"
            ]
            with patch(
                "bsc_audit.manifest.load_and_replay_theorem_certificate",
                wraps=manifest_module.load_and_replay_theorem_certificate,
            ) as replay:
                findings = audit_claim(raw, root)
        limit = next(
            finding
            for finding in findings
            if finding.code == "THEOREM_RESOURCE_LIMIT"
            and finding.witness.get("max_unique_certificate_digests")
            == MAX_THEOREM_REPLAYS_PER_AUDIT
        )
        self.assertEqual(
            limit.witness["max_unique_certificate_digests"],
            MAX_THEOREM_REPLAYS_PER_AUDIT,
        )
        self.assertEqual(replay.call_count, MAX_THEOREM_REPLAYS_PER_AUDIT)

    def test_v04_theorem_schema_cannot_relabel_its_exact_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            raw["admission"]["hard_gates"] = ["scientific_truth"]
            raw["admission"]["gate_results"][0]["id"] = "scientific_truth"
            raw["evidence"][0]["verifies_gates"] = ["scientific_truth"]
            findings = audit_claim(raw, root)
        self.assertTrue(
            any(finding.code == "SCHEMA_VALIDATION" for finding in findings)
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

    def test_hash_verified_fatal_failure_is_preserved_but_not_propagated(self):
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
        self.assertFalse(
            any(
                finding.code
                in {"FATAL_GATE_FAILED", "FATAL_DEPENDENCY_PROPAGATION"}
                for finding in findings
            )
        )
        gate = next(
            finding
            for finding in findings
            if finding.code == "GATE_RESULT_UNVERIFIED"
        )
        self.assertEqual(gate.witness["computed_state"], "unrun")
        self.assertEqual(
            gate.witness["nonsemantic_evidence"],
            ["evidence:failure"],
        )
        self.assertEqual(
            gate.witness["nonsemantic_declared_results"],
            {"evidence:failure": "fail"},
        )
        self.assertEqual(raw["evidence"][1]["result"], "fail")

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

    def test_arithmetic_obligations_reject_hash_only_pass_laundering(self):
        raw = json.loads(
            (ROOT / "examples" / "claim_arithmetic_no_go.json").read_text(
                encoding="utf-8"
            )
        )
        raw["claim"]["evidence_maturity"] = "declared"
        raw["claim"]["deployment_status"] = "research_only"
        raw["admission"]["gate_results"][0]["state"] = "unrun"
        raw["admission"]["gate_results"][0]["evidence"] = []
        evidence_id = raw["evidence"][0]["id"]
        raw["evidence"][0]["result"] = "pass"
        raw["evidence"][0]["verifies_gates"] = []
        config = raw["domain_checks"]["arithmetic_trace"]
        config["model_dimension"] = "infinite"
        config["target"] = "distributional_prime_increment"
        obligations = [
            "self_adjointness",
            "trace_class_resolvent",
            "exact_prime_increment",
            "joint_trace_norm_cauchy",
            "atomic_rigidity",
        ]
        config["certified_obligations"] = obligations
        config["obligation_evidence"] = {
            obligation: [evidence_id] for obligation in obligations
        }

        findings = audit_claim(raw, ROOT / "examples")

        rejected = [
            finding
            for finding in findings
            if finding.code == "TRACE_OBLIGATION_EVIDENCE_UNVERIFIED"
        ]
        self.assertEqual(len(rejected), len(obligations))
        self.assertEqual(
            {finding.path.rsplit(".", 1)[-1] for finding in rejected},
            set(obligations),
        )
        self.assertTrue(
            all(finding.witness == [evidence_id] for finding in rejected)
        )
        self.assertEqual(decision(findings), "blocked")

    def test_registered_theorem_result_is_a_typed_judgment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            findings = lint_manifest(raw, root)
            judgments, replay_findings = replayed_theorem_evidence(raw, root)

        self.assertFalse(
            any(finding.code == "THEOREM_CERTIFICATE_MISSING" for finding in findings)
        )
        self.assertTrue(
            any(
                finding.code == "THEOREM_IDENTITY_REPLAYED"
                for finding in replay_findings
            )
        )
        judgment = judgments[raw["evidence"][0]["id"]]
        self.assertEqual(judgment.subject_id, raw["claim"]["id"])
        self.assertEqual(judgment.predicate, "exact_polynomial_identity")
        self.assertEqual(judgment.scope, "canonical_formal_statement_only")
        self.assertEqual(judgment.method_id, "q-polynomial-identity-v0.1")
        self.assertEqual(judgment.authority, "bsc_internal_exact_replay")
        self.assertEqual(judgment.result, "pass")

    def test_public_audit_entrypoints_reject_preloaded_cache_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_polynomial_manifest(root)
            with self.assertRaises(TypeError):
                lint_manifest(raw, root, audit_cache=object())  # type: ignore[call-arg]
            with self.assertRaises(TypeError):
                audit_gate_product(raw, root, audit_cache=object())  # type: ignore[call-arg]

    def test_unknown_domain_check_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["domain_checks"] = {"misspelled_checker": {}}
            findings = lint_manifest(raw, root)

        self.assertTrue(
            any(
                finding.code == "DOMAIN_CHECK_UNREGISTERED"
                and finding.path == "domain_checks.misspelled_checker"
                for finding in findings
            )
        )

    def test_unknown_nested_domain_field_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["domain_checks"] = {
                "global_recovery": {
                    "local_nondegenerate": True,
                    "claims_global_recoveri": True,
                }
            }
            findings = lint_manifest(raw, root)

        self.assertTrue(
            any(
                finding.code == "DOMAIN_CHECK_FIELD_UNREGISTERED"
                and finding.path
                == "domain_checks.global_recovery.claims_global_recoveri"
                for finding in findings
            )
        )

    def test_unknown_arithmetic_obligation_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["claim"]["family"] = "arithmetic_trace"
            raw["domain_checks"] = {
                "arithmetic_trace": {
                    "model_dimension": "infinite",
                    "target": "distributional_prime_increment",
                    "uses_zero_ordinates": False,
                    "primary_gram_uses_zero_table": False,
                    "counterterm_singular_support": ["origin"],
                    "certified_obligations": [],
                    "obligation_evidence": {"atomic_rigidty": ["evidence:x"]},
                }
            }
            findings = lint_manifest(raw, root)

        self.assertTrue(
            any(
                finding.code == "DOMAIN_CHECK_FIELD_UNREGISTERED"
                and finding.path
                == "domain_checks.arithmetic_trace.obligation_evidence.atomic_rigidty"
                for finding in findings
            )
        )

    def test_unknown_certified_obligation_is_rejected_by_lint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["claim"]["family"] = "arithmetic_trace"
            raw["domain_checks"] = {
                "arithmetic_trace": {
                    "model_dimension": "infinite",
                    "target": "distributional_prime_increment",
                    "uses_zero_ordinates": False,
                    "primary_gram_uses_zero_table": False,
                    "counterterm_singular_support": ["origin"],
                    "certified_obligations": ["unknown_obligation"],
                    "obligation_evidence": {},
                }
            }
            findings = lint_manifest(raw, root)

        self.assertTrue(
            any(
                finding.code == "DOMAIN_CHECK_VALUE_UNREGISTERED"
                and finding.path.endswith(".certified_obligations.0")
                and finding.witness == "unknown_obligation"
                for finding in findings
            )
        )

    def test_public_gate_wrapper_rejects_malformed_gate_bindings(self):
        for malformed in (
            "exact_polynomial_identity",
            17,
            {"exact_polynomial_identity": True},
            ["exact_polynomial_identity", 17],
        ):
            with self.subTest(malformed=malformed):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    raw = self.make_polynomial_manifest(root)
                    raw["evidence"][0]["verifies_gates"] = malformed
                    findings = audit_gate_product(raw, root)

                blocked = [
                    finding
                    for finding in findings
                    if finding.code == "GATE_RESULT_UNVERIFIED"
                ]
                self.assertEqual(len(blocked), 1)
                self.assertEqual(
                    blocked[0].witness["malformed_gate_bindings"],
                    [raw["evidence"][0]["id"]],
                )

    def test_arithmetic_check_on_wrong_claim_family_is_not_applicable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.make_manifest(root)
            raw["claim"]["family"] = "theorem"
            raw["domain_checks"] = {
                "arithmetic_trace": {
                    "model_dimension": "finite",
                    "target": "finite_truncation",
                    "uses_zero_ordinates": False,
                    "primary_gram_uses_zero_table": False,
                    "counterterm_singular_support": [],
                    "certified_obligations": [],
                    "obligation_evidence": {},
                }
            }
            findings = audit_claim(raw, root)

        self.assertTrue(
            any(
                finding.code == "DOMAIN_CHECK_NOT_APPLICABLE"
                and finding.path == "domain_checks.arithmetic_trace"
                for finding in findings
            )
        )
        self.assertEqual(decision(findings), "prohibited")

    def test_wrong_top_level_type_is_a_finding(self):
        raw = {field: {} for field in ("claim", "system", "observation", "representation", "target", "experiment", "admission", "demotion", "preservation")}
        raw.update({"manifest_version": "0.3.0", "draft": False})
        raw["claim"] = []
        findings = lint_manifest(raw)
        self.assertTrue(any(f.code == "MANIFEST_OBJECT_TYPE" for f in findings))


if __name__ == "__main__":
    unittest.main()
