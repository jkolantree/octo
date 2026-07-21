import json
import unittest
from pathlib import Path

from bsc_audit.atomic import audit_atomic_modulus


ROOT = Path(__file__).resolve().parents[1]


class AtomicRigidityTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))

    def test_valid_record(self):
        findings = audit_atomic_modulus(self.load("atomic_modulus_valid.json"))
        self.assertTrue(any(f.code == "ATOMIC_MODULUS_RECORD_VALID" for f in findings))

    def test_concentrating_family_demoted(self):
        findings = audit_atomic_modulus(self.load("atomic_modulus_evasion.json"))
        finding = next(f for f in findings if f.code == "ATOMIC_CONCENTRATION_EVASION")
        self.assertEqual(finding.witness["allowed"], "1/10")

    def test_each_compact_requires_samples(self):
        findings = audit_atomic_modulus(
            {
                "modulus": {"constant": 1, "exponent": 1, "proof_id": "proof:test"},
                "compacts": [{"distance_from_origin": 1, "samples": []}],
            }
        )
        self.assertTrue(any(f.code == "ATOMIC_SAMPLES_MISSING" for f in findings))

    def test_exponent_resource_limit(self):
        raw = self.load("atomic_modulus_valid.json")
        raw["modulus"]["exponent"] = 65
        findings = audit_atomic_modulus(raw)
        self.assertTrue(any(f.code == "ATOMIC_EXPONENT_LIMIT" for f in findings))
        self.assertFalse(any(f.code == "ATOMIC_MODULUS_RECORD_VALID" for f in findings))

    def test_proof_identifier_is_required(self):
        raw = self.load("atomic_modulus_valid.json")
        raw["modulus"].pop("proof_id")
        findings = audit_atomic_modulus(raw)
        self.assertTrue(any(f.code == "ATOMIC_MODULUS_PROOF_MISSING" for f in findings))

    def test_malformed_compact_is_finding_not_exception(self):
        findings = audit_atomic_modulus(
            {
                "modulus": {"constant": 1, "exponent": 1, "proof_id": "proof:test"},
                "compacts": ["not-an-object"],
            }
        )
        self.assertTrue(any(f.code == "ATOMIC_COMPACT_TYPE" for f in findings))


if __name__ == "__main__":
    unittest.main()
