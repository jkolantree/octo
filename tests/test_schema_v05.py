from __future__ import annotations

import copy
import unittest
from pathlib import Path

from bsc_audit.census import replay_census_certificate
from bsc_audit.provenance import sha256_json
from bsc_audit.schema_validation import validate_route_schema


ROOT = Path(__file__).resolve().parents[1]
HASHES = {
    name: f"sha256:{digit * 64}"
    for name, digit in {
        "frame": "1",
        "population": "2",
        "identity": "3",
        "measurement": "4",
        "guard": "5",
    }.items()
}


def common_manifest() -> dict[str, object]:
    return {
        "manifest_version": "0.5.0",
        "draft": False,
        "system": {
            "domain": "identified finite population",
            "state_type": "exact rational measurement enclosures",
        },
        "observation": {
            "kernel_or_instrument": "declared bounded measurement process",
            "legal_filtration": {},
        },
        "representation": {"kind": "finite census frame"},
        "target": {
            "outcome": "closed affine upper bound",
            "horizon": "identified frame only",
            "loss_or_score": "exact rational order",
        },
        "experiment": {
            "baseline_model": "complete submitted census",
            "search_budget": "one bounded exact replay",
        },
        "admission": {"hard_gates": [], "gate_results": []},
        "demotion": {
            "owner": "maintainer",
            "rules": [{"if": "counterexample", "then": "retire"}],
            "negative_result_destination": "negative-results/",
        },
        "preservation": {},
    }


def theorem_manifest() -> dict[str, object]:
    manifest = common_manifest()
    manifest["claim"] = {
        "id": "bsc:test:theorem-v05",
        "title": "Exact identity over Q",
        "type": "theorem_schema",
        "evidence_maturity": "structurally_checked",
        "deployment_status": "research_only",
        "statement": "The exact polynomial identity x equals x.",
        "scope": "formal equality over Q only",
        "family": "q-polynomial-identity-v0.1",
        "formal_statement": {
            "language": "q-polynomial-identity-v0.1",
            "field": "Q",
            "variables": ["x"],
            "relation": {
                "op": "eq",
                "left": {"op": "var", "name": "x"},
                "right": {"op": "var", "name": "x"},
            },
        },
    }
    manifest["admission"] = {
        "hard_gates": ["exact_polynomial_identity"],
        "gate_results": [],
    }
    return manifest


def census_manifest() -> dict[str, object]:
    manifest = common_manifest()
    manifest["claim"] = {
        "id": "bsc:test:census-v05",
        "title": "Finite census affine bound",
        "type": "empirical_claim",
        "evidence_maturity": "empirically_passed",
        "deployment_status": "research_only",
        "statement": "The identified submitted census satisfies its closed affine bound.",
        "scope": "identified frame and supplied measurement enclosures only",
        "family": "finite-census-affine-bound-v0.1",
        "formal_statement": {
            "language": "finite-census-affine-bound-v0.1",
            "field": "Q",
            "frame_sha256": HASHES["frame"],
            "observables": ["x"],
            "coefficients": {"x": 1},
            "relation": {"op": "le", "bound": 10},
            "required_guard_band": 1,
            "external_premises": {
                "frame_denotes_target_population": HASHES["population"],
                "unit_identity_authentic": HASHES["identity"],
                "measurement_enclosures_sound": HASHES["measurement"],
                "guard_band_scientifically_adequate": HASHES["guard"],
            },
        },
    }
    manifest["admission"] = {
        "hard_gates": ["finite_census_affine_bound"],
        "gate_results": [],
    }
    manifest["evidence"] = [
        {
            "id": "evidence:census-certificate",
            "kind": "empirical_certificate",
            "status": "declared",
            "result": "pass",
            "verifies_gates": ["finite_census_affine_bound"],
            "verifies_claims": ["bsc:test:census-v05"],
        }
    ]
    return manifest


def census_certificate() -> dict[str, object]:
    population = {
        "coverage": "census",
        "declared_size": 1,
        "unit_ids": ["u1"],
    }
    formal_statement = copy.deepcopy(
        census_manifest()["claim"]["formal_statement"]
    )
    formal_statement["frame_sha256"] = sha256_json(population)
    return {
        "certificate_version": "0.1.0",
        "claim_id": "bsc:test:census-v05",
        "formal_statement": formal_statement,
        "population": population,
        "observations": [
            {
                "unit_id": "u1",
                "intervals": {"x": {"lower": 1, "upper": 1}},
            }
        ],
        "declared_result": "pass",
    }


class ClaimManifestV05SchemaTests(unittest.TestCase):
    def test_canonical_and_packaged_schemas_are_byte_identical(self) -> None:
        canonical = (ROOT / "schemas" / "claim-manifest-v0.5.schema.json").read_bytes()
        packaged = (
            ROOT
            / "src"
            / "bsc_audit"
            / "schema_data"
            / "claim-manifest-v0.5.schema.json"
        ).read_bytes()
        self.assertEqual(packaged, canonical)

    def test_minimal_theorem_profile_is_valid(self) -> None:
        self.assertEqual(validate_route_schema("lint", theorem_manifest()), [])

    def test_minimal_census_profile_is_valid(self) -> None:
        self.assertEqual(validate_route_schema("lint", census_manifest()), [])

    def test_census_profile_rejects_open_or_mismatched_shapes(self) -> None:
        missing_premise = census_manifest()
        del missing_premise["claim"]["formal_statement"]["external_premises"][
            "measurement_enclosures_sound"
        ]

        extra_premise = census_manifest()
        extra_premise["claim"]["formal_statement"]["external_premises"][
            "study_conclusion"
        ] = HASHES["measurement"]

        wrong_gate = census_manifest()
        wrong_gate["admission"]["hard_gates"] = ["exact_polynomial_identity"]

        wrong_maturity = census_manifest()
        wrong_maturity["claim"]["evidence_maturity"] = "structurally_checked"

        wrong_deployment = census_manifest()
        wrong_deployment["claim"]["deployment_status"] = "admitted"

        for label, manifest in {
            "missing premise": missing_premise,
            "extra premise": extra_premise,
            "wrong hard gate": wrong_gate,
            "wrong maturity": wrong_maturity,
            "wrong deployment": wrong_deployment,
        }.items():
            with self.subTest(label=label):
                self.assertTrue(validate_route_schema("lint", manifest))

    def test_v04_theorem_remains_dispatch_valid(self) -> None:
        legacy = copy.deepcopy(theorem_manifest())
        legacy["manifest_version"] = "0.4.0"
        self.assertEqual(validate_route_schema("lint", legacy), [])

    def test_census_observable_grammar_matches_manifest_schema_and_kernel(self) -> None:
        for length, accepted in ((64, True), (65, False)):
            observable = "x" * length
            manifest = census_manifest()
            manifest_statement = manifest["claim"]["formal_statement"]
            manifest_statement["observables"] = [observable]
            manifest_statement["coefficients"] = {observable: 1}

            certificate = census_certificate()
            certificate_statement = certificate["formal_statement"]
            certificate_statement["observables"] = [observable]
            certificate_statement["coefficients"] = {observable: 1}
            certificate["observations"][0]["intervals"] = {
                observable: {"lower": 1, "upper": 1}
            }

            with self.subTest(length=length):
                manifest_findings = validate_route_schema("lint", manifest)
                certificate_findings = validate_route_schema(
                    "census",
                    certificate,
                )
                replay = replay_census_certificate(certificate)
                self.assertEqual(not manifest_findings, accepted)
                self.assertEqual(not certificate_findings, accepted)
                self.assertEqual(replay.valid, accepted)


if __name__ == "__main__":
    unittest.main()
