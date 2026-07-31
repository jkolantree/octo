import json
import unittest
from fractions import Fraction
from pathlib import Path

from bsc_audit.defect import AffineDefect, audit_defect_composition
from bsc_audit.schema_validation import validate_route_schema


ROOT = Path(__file__).resolve().parents[1]


class DefectTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))

    def test_affine_composition_is_associative(self):
        a = AffineDefect(Fraction(2), Fraction(1, 10), Fraction(1, 100))
        b = AffineDefect(Fraction(3), Fraction(1, 20), Fraction(1, 200))
        c = AffineDefect(Fraction(1, 2), Fraction(1, 50), Fraction(1, 1000))
        self.assertEqual(a.then(b).then(c), a.then(b.then(c)))

    def test_exact_composite_passes(self):
        findings = audit_defect_composition(self.load("defect_composition_valid.json"))
        self.assertTrue(any(f.code == "DEFECT_COMPOSITE_VALID" for f in findings))

    def test_understatement_is_demoted(self):
        findings = audit_defect_composition(self.load("defect_composition_understated.json"))
        finding = next(f for f in findings if f.code == "DEFECT_UNDERSTATED")
        self.assertEqual(finding.witness["required"]["epsilon"], "1/25")

    def test_f10_examples_replay_every_exact_prefix(self):
        expected_prefixes = {
            "HOST-A": [
                "1/100",
                "3/200",
                "7/400",
                "3/160",
                "31/1600",
                "63/3200",
                "127/6400",
                "51/2560",
                "511/25600",
                "1023/51200",
            ],
            "HOST-B": [
                "1/100",
                "19/1000",
                "271/10000",
                "3439/100000",
                "40951/1000000",
                "468559/10000000",
                "5217031/100000000",
                "56953279/1000000000",
                "612579511/10000000000",
                "6513215599/100000000000",
            ],
        }
        filenames = {
            "HOST-A": "defect_f10_host_a.json",
            "HOST-B": "defect_f10_host_b.json",
        }
        for host, filename in filenames.items():
            with self.subTest(host=host):
                document = self.load(filename)
                self.assertEqual(validate_route_schema("defect", document), [])
                composite = AffineDefect(Fraction(1), Fraction(0), Fraction(0))
                prefixes = []
                for raw_step in document["steps"]:
                    step = AffineDefect(
                        Fraction(raw_step["lipschitz"]),
                        Fraction(raw_step["epsilon"]),
                        Fraction(raw_step["failure_probability"]),
                    )
                    composite = composite.then(step)
                    prefixes.append(str(composite.epsilon))
                self.assertEqual(prefixes, expected_prefixes[host])
                declared = document["declared_composite"]
                self.assertEqual(str(composite.lipschitz), declared["lipschitz"])
                self.assertEqual(str(composite.epsilon), declared["epsilon"])
                self.assertEqual(composite.failure_probability, 0)
                findings = audit_defect_composition(document)
                self.assertEqual([finding.code for finding in findings], ["DEFECT_COMPOSITE_VALID"])

    def test_f10_crosswalk_keeps_bound_and_actual_violation_authorities_separate(self):
        record = self.load("f10_coupled_surrogate_crosswalk.json")
        upstream = record["upstream_evidence"]
        self.assertEqual(upstream["tag"], "v1.2.0")
        self.assertEqual(
            upstream["commit"],
            "5fdcb3e1de15b04ed037da135717d316e45f28b1",
        )
        self.assertEqual(
            upstream["tree"],
            "7328eee577c7595c5381e129c62d5c0b1fe78e30",
        )
        self.assertEqual(upstream["version_doi"], "10.5281/zenodo.21711341")
        self.assertEqual(
            upstream["dependency_slice"]["simulation_profile"]["sha256"],
            "2f6ebf949995cf4e3b955cea2d4e52612d08b27668a46d9177767e9b9b5ed7ac",
        )
        self.assertEqual(
            upstream["dependency_slice"]["f10_input"]["sha256"],
            "cb8ffa494ace2cc204d02f3060eaf04783abb89b0c66c161c42415b8538f9497",
        )
        self.assertEqual(
            upstream["dependency_slice"]["f10_receipt"]["sha256"],
            "7296f8aa486c52669eee34b83889cae177d51c059696a52646f3135e86d630b8",
        )
        self.assertEqual(
            record["octo_projection"]["authority"],
            "exact_propagation_of_supplied_affine_upper_bounds_only",
        )
        self.assertEqual(
            record["external_f10_dispositions"]["HOST-B"]["violation_basis"],
            "exact_actual_error_above_tolerance",
        )
        self.assertEqual(
            record["authority_boundary"]["deployment_authority"],
            "not_granted",
        )
        self.assertEqual(
            upstream["not_a_dependency"],
            "framework/Normalized_Scale_Profiles.md",
        )
        self.assertEqual(
            upstream["release_context"]["paper"]["sha256"],
            "106631826fc417549d68927418759b856e5610c7c0c27ab53c33665994a60b8c",
        )

        tolerance = Fraction(record["external_f10_dispositions"]["tolerance"])
        host_a = record["external_f10_dispositions"]["HOST-A"]
        host_b = record["external_f10_dispositions"]["HOST-B"]
        self.assertEqual(
            tolerance - Fraction(host_a["endpoint_error"]),
            Fraction("1537/51200"),
        )
        self.assertLess(Fraction(host_b["step_6_error"]), tolerance)
        self.assertEqual(
            Fraction(host_b["step_7_margin_above_tolerance"]),
            Fraction("217031/100000000"),
        )
        self.assertEqual(
            Fraction(host_b["endpoint_error"]) - tolerance,
            Fraction("1513215599/100000000000"),
        )


if __name__ == "__main__":
    unittest.main()
