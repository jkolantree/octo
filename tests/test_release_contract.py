from __future__ import annotations

import copy
import unittest

from scripts.release_contract import (
    REQUIRED_ARTIFACT_ROLES,
    STAGE_IDS,
    expected_artifact_names,
    release_subject,
    role_for_artifact_name,
    sha256_identity,
    stage_judgment,
    validate_verification_receipt,
    verification_receipt,
)


COMMIT = "1" * 40
TREE = "2" * 40
TAG = "v0.3.0-alpha.20"
ENGINE_VERSION = "0.3.0a20"
PUBLIC_VERSION = "0.3.0-alpha.20"


class ReleaseContractTests(unittest.TestCase):
    def artifacts(self) -> list[dict[str, object]]:
        names = expected_artifact_names(
            engine_version=ENGINE_VERSION,
            public_version=PUBLIC_VERSION,
        )
        return [
            {
                "role": role,
                "name": name,
                "bytes": index + 1,
                "sha256": f"{index + 1:064x}",
            }
            for index, (role, name) in enumerate(sorted(names.items()))
        ]

    def stage_evidence(
        self,
        stage_id: str,
        subject: dict[str, str],
        artifacts: list[dict[str, object]],
    ) -> dict[str, object]:
        by_role = {item["role"]: item for item in artifacts}

        def refs(roles: set[str]) -> list[dict[str, str]]:
            return sorted(
                [
                    {
                        "name": str(by_role[role]["name"]),
                        "sha256": str(by_role[role]["sha256"]),
                    }
                    for role in roles
                ],
                key=lambda item: item["name"].encode("utf-8"),
            )

        publication_roles = {
            "orientation_text",
            "copy_paste_protocol",
            "upload_protocol",
            "system_prompt_protocol",
            "canonical_protocol",
            "claim_manifest_schema",
            "worked_examples",
            "publication_metadata",
        }
        evidence_by_stage: dict[str, dict[str, object]] = {
            "exact-release-identity": {
                **subject,
                "worktree_status": "clean",
            },
            "toolchain-binding": {
                "python": "3.12.13",
                "node": "22.23.1",
                "setuptools": "82.0.1",
                "source_date_epoch": 1784505600,
                "toolchain_lock_sha256": "f" * 64,
            },
            "candidate-profile": {"profile": "candidate", "exit_code": 0},
            "distribution-build": {
                "exit_code": 0,
                "artifacts": refs({"python_wheel", "python_sdist"}),
            },
            "reproducible-distributions": {
                "comparison": "exact_filename_sha256_map",
                "artifacts": refs({"python_wheel", "python_sdist"}),
            },
            "tracked-source-archive": {
                **refs({"tracked_source_archive"})[0],
                "tracked_entries": 1,
            },
            "conformance-bundle": refs({"conformance_bundle"})[0],
            "publication-assets": {"artifacts": refs(publication_roles)},
            "custom-gpt-package": refs({"custom_gpt_package"})[0],
            "software-bill-of-materials": {
                **refs({"software_bill_of_materials"})[0],
                "wheel_sha256": by_role["python_wheel"]["sha256"],
            },
            "tracked-tree-recheck": {
                "commit": subject["commit"],
                "tree": subject["tree"],
                "expected_source_entries": 1,
                "tracked_source_state": "unchanged",
            },
            "artifact-payload-privacy": {
                "exit_code": 0,
                "scan_scope": "role_artifact_payloads_before_manifest",
                "artifacts": refs(set(REQUIRED_ARTIFACT_ROLES)),
            },
        }
        return evidence_by_stage[stage_id]

    def receipt(self) -> dict[str, object]:
        subject = release_subject(COMMIT, TREE, TAG)
        artifacts = self.artifacts()
        judgments = [
            stage_judgment(
                stage_id,
                subject=subject,
                evidence=self.stage_evidence(stage_id, subject, artifacts),
            )
            for stage_id in STAGE_IDS
        ]
        return verification_receipt(subject, judgments)

    def failures(self, receipt: object) -> list[str]:
        return validate_verification_receipt(
            receipt,
            expected_subject=release_subject(COMMIT, TREE, TAG),
            expected_toolchain_evidence=self.stage_evidence(
                "toolchain-binding",
                release_subject(COMMIT, TREE, TAG),
                self.artifacts(),
            ),
            expected_artifacts=self.artifacts(),
        )

    def test_deterministic_complete_receipt_passes(self) -> None:
        first = self.receipt()
        second = self.receipt()
        self.assertEqual(first, second)
        self.assertEqual(self.failures(first), [])

    def test_stale_subject_is_rejected(self) -> None:
        receipt = self.receipt()
        receipt["subject"]["commit"] = "3" * 40
        self.assertTrue(any("subject differs" in item for item in self.failures(receipt)))

    def test_missing_duplicate_and_unknown_stage_are_rejected(self) -> None:
        mutations = []
        missing = self.receipt()
        missing["judgments"].pop()
        mutations.append(missing)
        duplicate = self.receipt()
        duplicate["judgments"][-1] = copy.deepcopy(duplicate["judgments"][0])
        mutations.append(duplicate)
        unknown = self.receipt()
        unknown["judgments"][0]["stage_id"] = "unknown"
        mutations.append(unknown)
        for receipt in mutations:
            with self.subTest(receipt=receipt):
                self.assertTrue(self.failures(receipt))

    def test_method_authority_result_and_evidence_digest_are_replayed(self) -> None:
        mutations = {
            "method_id": "unknown-method",
            "scope": "untyped-global-pass",
            "authority": "untrusted-authority",
            "result": "fail",
            "evidence_record_sha256": "sha256:" + "0" * 64,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                receipt = self.receipt()
                receipt["judgments"][0][field] = value
                self.assertTrue(self.failures(receipt))

    def test_artifact_names_have_one_exact_semantic_role(self) -> None:
        names = expected_artifact_names(
            engine_version=ENGINE_VERSION,
            public_version=PUBLIC_VERSION,
        )
        self.assertEqual(set(names), REQUIRED_ARTIFACT_ROLES)
        self.assertNotIn("bsc-audit-complete.zip", names.values())
        for role, name in names.items():
            with self.subTest(role=role):
                self.assertEqual(
                    role_for_artifact_name(
                        name,
                        engine_version=ENGINE_VERSION,
                        public_version=PUBLIC_VERSION,
                    ),
                    role,
                )

    def test_receipt_artifacts_must_match_release_roster(self) -> None:
        artifacts = self.artifacts()
        artifacts[0]["sha256"] = "e" * 64
        failures = validate_verification_receipt(
            self.receipt(),
            expected_subject=release_subject(COMMIT, TREE, TAG),
            expected_toolchain_evidence=self.stage_evidence(
                "toolchain-binding",
                release_subject(COMMIT, TREE, TAG),
                self.artifacts(),
            ),
            expected_artifacts=artifacts,
        )
        self.assertTrue(
            any("differ from the semantic release roster" in item for item in failures)
        )

    def test_correctly_hashed_casefold_order_is_still_rejected(self) -> None:
        receipt = self.receipt()
        judgment = next(
            item
            for item in receipt["judgments"]
            if item["stage_id"] == "artifact-payload-privacy"
        )
        references = judgment["evidence"]["artifacts"]
        references.sort(key=lambda item: item["name"].casefold())
        judgment["evidence_record_sha256"] = sha256_identity(
            judgment["evidence"]
        )
        self.assertTrue(
            any(
                "must be sorted by artifact name" in failure
                for failure in self.failures(receipt)
            )
        )

    def test_toolchain_evidence_is_bound_to_authoritative_lock(self) -> None:
        for field, value in {
            "python": "0.0.0",
            "node": {},
            "toolchain_lock_sha256": "0" * 64,
        }.items():
            with self.subTest(field=field):
                receipt = self.receipt()
                judgment = next(
                    item
                    for item in receipt["judgments"]
                    if item["stage_id"] == "toolchain-binding"
                )
                judgment["evidence"][field] = value
                judgment["evidence_record_sha256"] = sha256_identity(
                    judgment["evidence"]
                )
                self.assertTrue(
                    any(
                        "authoritative toolchain lock" in failure
                        for failure in self.failures(receipt)
                    )
                )

    def test_source_archive_and_recheck_counts_must_agree(self) -> None:
        receipt = self.receipt()
        judgment = next(
            item
            for item in receipt["judgments"]
            if item["stage_id"] == "tracked-source-archive"
        )
        judgment["evidence"]["tracked_entries"] = 999
        judgment["evidence_record_sha256"] = sha256_identity(
            judgment["evidence"]
        )
        self.assertTrue(
            any(
                "entry counts must be positive and identical" in failure
                for failure in self.failures(receipt)
            )
        )


if __name__ == "__main__":
    unittest.main()
