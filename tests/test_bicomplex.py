import json
import unittest
from pathlib import Path

from bsc_audit.bicomplex import audit_complex_document


ROOT = Path(__file__).resolve().parents[1]


class BicomplexTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))

    def test_valid_transport_is_natural(self):
        findings = audit_complex_document(self.load("complex_valid_transport.json"))
        self.assertTrue(any(f.code == "CERTIFICATE_NATURAL" for f in findings))
        self.assertFalse(any(f.code == "CERTIFICATE_INTERCHANGE_DEFECT" for f in findings))

    def test_broken_transport_emits_exact_witness(self):
        findings = audit_complex_document(self.load("complex_broken_transport.json"))
        defect = next(f for f in findings if f.code == "CERTIFICATE_INTERCHANGE_DEFECT")
        self.assertEqual(defect.witness, {"basis_index": 0, "residual": [-1], "degree": 1})

    def test_negative_degrees_are_rejected(self):
        findings = audit_complex_document(
            {"contexts": {"c": {"groups": {"0": 1, "-1": 1}, "differentials": {"0": [[1]]}}}}
        )
        self.assertTrue(any(f.code == "CONTEXT_TYPE" for f in findings))

    def test_undeclared_transport_degree_is_rejected(self):
        raw = self.load("complex_valid_transport.json")
        raw["transports"]["coarse_grain"]["maps"]["2"] = [[1]]
        findings = audit_complex_document(raw)
        self.assertTrue(any(f.code == "TRANSPORT_TYPE" for f in findings))

    def test_malformed_context_is_finding_not_exception(self):
        findings = audit_complex_document({"contexts": {"c": {}}})
        self.assertTrue(any(f.code == "CONTEXT_TYPE" for f in findings))

    def test_unknown_square_transport_is_rejected(self):
        raw = self.load("complex_valid_transport.json")
        raw["squares"] = {
            "bad": {
                "left_first": "coarse_grain",
                "left_second": "missing",
                "right_first": "coarse_grain",
                "right_second": "missing",
            }
        }
        findings = audit_complex_document(raw)
        self.assertTrue(any(f.code == "SQUARE_TRANSPORT_REFERENCE" for f in findings))

    def test_malformed_transport_endpoint_is_finding_not_exception(self):
        raw = self.load("complex_valid_transport.json")
        raw["transports"]["coarse_grain"]["source"] = ["fine"]
        findings = audit_complex_document(raw)
        self.assertTrue(any(f.code == "TRANSPORT_TYPE" for f in findings))


if __name__ == "__main__":
    unittest.main()
