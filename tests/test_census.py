from __future__ import annotations

import itertools
import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from bsc_audit.census import (
    CENSUS_AUTHORITY,
    CENSUS_AUTHORITY_SCOPE,
    CENSUS_GATE_ID,
    CENSUS_PROFILE_SCOPE,
    canonical_formal_statement,
    canonical_formal_title,
    load_and_replay_census_certificate,
    replay_census_certificate,
)
from bsc_audit.provenance import sha256_bytes, sha256_json


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "census_affine_bound.json"


class CensusReplayTests(unittest.TestCase):
    def example(self) -> dict[str, object]:
        return json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_synthetic_example_replays_exact_conditional_pass(self) -> None:
        certificate = self.example()
        replay = replay_census_certificate(certificate)

        self.assertTrue(replay.valid)
        self.assertEqual(replay.result, "pass")
        self.assertEqual(
            replay.bounds_json(),
            [
                {"unit_id": "unit-01", "lower": 3, "upper": 5},
                {"unit_id": "unit-02", "lower": 5, "upper": 7},
            ],
        )
        witness = replay.findings[0].witness
        self.assertEqual(witness["observational_truth"], "established_conditionally")
        self.assertEqual(witness["scope"], CENSUS_PROFILE_SCOPE)
        self.assertEqual(witness["method"]["id"], CENSUS_GATE_ID)
        self.assertEqual(witness["authority"]["id"], CENSUS_AUTHORITY)
        self.assertEqual(
            witness["authority"]["scope"],
            CENSUS_AUTHORITY_SCOPE,
        )
        self.assertEqual(witness["causal_truth"], "not_granted")
        self.assertEqual(witness["generalization_beyond_frame"], "not_granted")
        self.assertEqual(witness["deployment_authority"], "not_granted")
        self.assertEqual(
            canonical_formal_title(certificate["formal_statement"]),
            "Finite-census affine upper bound in Q",
        )
        self.assertEqual(
            witness["canonical_formal_statement"],
            canonical_formal_statement(certificate["formal_statement"]),
        )

    def test_evidence_identity_distinguishes_observation_mutations(self) -> None:
        passing = replay_census_certificate(self.example())
        failing_certificate = self.example()
        failing_certificate["observations"][1]["intervals"]["mass"] = {
            "lower": 20,
            "upper": 20,
        }
        failing_certificate["declared_result"] = "fail"
        failing = replay_census_certificate(failing_certificate)

        self.assertTrue(passing.valid)
        self.assertTrue(failing.valid)
        self.assertEqual(passing.formal_statement_sha256, failing.formal_statement_sha256)
        self.assertEqual(passing.frame_sha256, failing.frame_sha256)
        self.assertNotEqual(
            passing.certificate_semantic_sha256,
            failing.certificate_semantic_sha256,
        )
        self.assertNotEqual(
            passing.observations_sha256,
            failing.observations_sha256,
        )
        pass_identity = passing.findings[0].witness["evidence_identity"]
        fail_identity = failing.findings[0].witness["evidence_identity"]
        self.assertNotEqual(pass_identity, fail_identity)
        self.assertEqual(
            pass_identity["certificate_semantic_sha256"],
            passing.certificate_semantic_sha256,
        )
        self.assertEqual(
            fail_identity["observations_sha256"],
            failing.observations_sha256,
        )

    def test_definite_counterexample_and_boundary_are_separate(self) -> None:
        failing = self.example()
        failing["formal_statement"]["relation"]["bound"] = 4
        failing["declared_result"] = "fail"
        failed = replay_census_certificate(failing)
        self.assertTrue(failed.valid)
        self.assertEqual(failed.result, "fail")
        self.assertEqual(
            failed.findings[0].witness["first_counterexample"]["unit_id"],
            "unit-02",
        )
        self.assertEqual(
            failed.findings[0].witness["observational_truth"],
            "refuted_conditionally",
        )

        boundary = self.example()
        boundary["formal_statement"]["relation"]["bound"] = 7
        boundary["declared_result"] = "inconclusive"
        unresolved = replay_census_certificate(boundary)
        self.assertTrue(unresolved.valid)
        self.assertEqual(unresolved.result, "inconclusive")
        self.assertEqual(
            unresolved.findings[0].witness["first_unresolved"],
            {
                "unit_id": "unit-02",
                "lower": 5,
                "upper": 7,
                "upper_plus_guard_band": 8,
                "bound": 7,
            },
        )
        self.assertEqual(
            unresolved.findings[0].witness["observational_truth"],
            "not_established",
        )

    def test_complete_sorted_roster_and_exact_result_are_mandatory(self) -> None:
        for mutation, code in (
            (
                lambda document: document["observations"].pop(),
                "CENSUS_CERTIFICATE_INVALID",
            ),
            (
                lambda document: document["observations"].reverse(),
                "CENSUS_CERTIFICATE_INVALID",
            ),
            (
                lambda document: document.update(declared_result="fail"),
                "CENSUS_CERTIFICATE_RESULT_MISMATCH",
            ),
        ):
            certificate = self.example()
            mutation(certificate)
            replay = replay_census_certificate(certificate)
            self.assertFalse(replay.valid)
            self.assertEqual(replay.findings[0].code, code)

    def test_frame_statement_premises_and_canonical_rationals_are_bound(self) -> None:
        mutations = (
            lambda document: document["population"]["unit_ids"].append("unit-03"),
            lambda document: document["formal_statement"]["external_premises"].update(
                measurement_enclosures_sound="sha256:" + "0" * 64
            ),
            lambda document: document["formal_statement"].update(
                required_guard_band=0
            ),
            lambda document: document["formal_statement"]["coefficients"].update(
                mass="2/2"
            ),
            lambda document: document["observations"][0]["intervals"]["mass"].update(
                lower=True
            ),
        )
        for mutation in mutations:
            certificate = self.example()
            mutation(certificate)
            replay = replay_census_certificate(certificate)
            self.assertFalse(replay.valid)
            self.assertIn(
                replay.findings[0].code,
                {
                    "CENSUS_CERTIFICATE_INVALID",
                    "CENSUS_FRAME_HASH_MISMATCH",
                },
            )

    def test_interval_extrema_match_independent_endpoint_enumeration(self) -> None:
        population = {
            "coverage": "census",
            "declared_size": 1,
            "unit_ids": ["u"],
        }
        premises = {
            "frame_denotes_target_population": "sha256:" + "1" * 64,
            "unit_identity_authentic": "sha256:" + "2" * 64,
            "measurement_enclosures_sound": "sha256:" + "3" * 64,
            "guard_band_scientifically_adequate": "sha256:" + "4" * 64,
        }
        intervals = {
            "x": {"lower": -2, "upper": 3},
            "y": {"lower": 1, "upper": 5},
        }
        for x_coefficient, y_coefficient in itertools.product(
            (-3, -1, 0, 2, 5),
            repeat=2,
        ):
            certificate = {
                "certificate_version": "0.1.0",
                "claim_id": "synthetic.exhaustive-endpoints",
                "formal_statement": {
                    "language": "finite-census-affine-bound-v0.1",
                    "field": "Q",
                    "frame_sha256": sha256_json(population),
                    "observables": ["x", "y"],
                    "coefficients": {
                        "x": x_coefficient,
                        "y": y_coefficient,
                    },
                    "relation": {"op": "le", "bound": 1000},
                    "required_guard_band": 1,
                    "external_premises": premises,
                },
                "population": population,
                "observations": [{"unit_id": "u", "intervals": intervals}],
                "declared_result": "pass",
            }
            replay = replay_census_certificate(certificate)
            self.assertTrue(replay.valid, replay.findings)
            endpoint_values = [
                Fraction(x_coefficient) * x
                + Fraction(y_coefficient) * y
                for x, y in itertools.product((-2, 3), (1, 5))
            ]
            self.assertEqual(
                replay.bounds[0][1:],
                (min(endpoint_values), max(endpoint_values)),
            )

    def test_loader_hashes_and_parses_one_strict_bounded_buffer(self) -> None:
        payload = EXAMPLE.read_bytes()
        with tempfile.TemporaryDirectory(prefix="bsc-census-") as directory:
            root = Path(directory)
            path = root / "certificate.json"
            path.write_bytes(payload)

            replay = load_and_replay_census_certificate(
                root,
                "certificate.json",
                expected_sha256=sha256_bytes(payload),
                expected_claim_id="synthetic.census.affine-bound",
                expected_formal_statement=self.example()["formal_statement"],
            )
            self.assertTrue(replay.valid)
            self.assertEqual(replay.result, "pass")

            changed = load_and_replay_census_certificate(
                root,
                "certificate.json",
                expected_sha256="sha256:" + "f" * 64,
            )
            self.assertFalse(changed.valid)
            self.assertEqual(
                changed.findings[0].code,
                "CENSUS_CERTIFICATE_BYTES_CHANGED",
            )

            duplicate = payload.decode("utf-8").replace(
                '"certificate_version": "0.1.0",',
                '"certificate_version": "0.1.0",\n'
                '  "certificate_version": "0.1.0",',
                1,
            )
            path.write_text(duplicate, encoding="utf-8", newline="\n")
            rejected = load_and_replay_census_certificate(
                root,
                "certificate.json",
            )
            self.assertFalse(rejected.valid)
            self.assertEqual(
                rejected.findings[0].code,
                "CENSUS_CERTIFICATE_INVALID",
            )

            escaped = load_and_replay_census_certificate(root, "../certificate.json")
            self.assertFalse(escaped.valid)
            self.assertEqual(
                escaped.findings[0].code,
                "CENSUS_CERTIFICATE_PATH_UNSAFE",
            )


if __name__ == "__main__":
    unittest.main()
