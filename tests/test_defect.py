import json
import unittest
from fractions import Fraction
from pathlib import Path

from bsc_audit.defect import AffineDefect, audit_defect_composition


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


if __name__ == "__main__":
    unittest.main()
