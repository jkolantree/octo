import json
import unittest
from pathlib import Path

from bsc_audit.observation import audit_observation_document, kernel_of_queries


ROOT = Path(__file__).resolve().parents[1]


class ObservationTests(unittest.TestCase):
    def test_descent_witness(self):
        raw = json.loads((ROOT / "examples" / "observation_failure.json").read_text(encoding="utf-8"))
        findings = audit_observation_document(raw)
        self.assertTrue(any(f.code == "QUERY_DESCENDS" and f.path == "queries.observed_output" for f in findings))
        failure = next(f for f in findings if f.code == "QUERY_DESCENT_FAILURE")
        self.assertIn(failure.witness["left"], {"p0", "p+", "p-"})

    def test_kernel_of_query_family(self):
        states = [0, 1, 2]
        queries = [{0: "a", 1: "a", 2: "b"}]
        kernel = kernel_of_queries(states, queries)
        self.assertIn((0, 1), kernel)
        self.assertNotIn((0, 2), kernel)

    def test_query_must_be_total(self):
        findings = audit_observation_document(
            {"states": ["a", "b"], "relation": [["a", "b"]], "queries": {"q": {}}}
        )
        self.assertTrue(any(f.code == "OBS_QUERY_NOT_TOTAL" for f in findings))
        self.assertFalse(any(f.code == "QUERY_DESCENDS" for f in findings))

    def test_query_family_must_be_nonempty(self):
        findings = audit_observation_document(
            {"states": ["a", "b"], "relation": [["a", "b"]], "queries": {}}
        )
        self.assertTrue(any(f.code == "OBS_QUERIES_MISSING" for f in findings))

    def test_malformed_relation_is_finding_not_exception(self):
        findings = audit_observation_document(
            {"states": ["a"], "relation": [["a"]], "queries": {"q": {"a": 1}}}
        )
        self.assertTrue(any(f.code == "OBS_RELATION_PAIR" for f in findings))

    def test_optional_equivalence_validation(self):
        findings = audit_observation_document(
            {
                "states": ["a", "b"],
                "relation_kind": "equivalence",
                "relation": [["a", "b"]],
                "queries": {"q": {"a": 0, "b": 0}},
            }
        )
        self.assertTrue(any(f.code == "OBS_RELATION_NOT_EQUIVALENCE" for f in findings))

    def test_kernel_rejects_partial_queries(self):
        with self.assertRaises(ValueError):
            kernel_of_queries([0, 1], [{0: "a"}])


if __name__ == "__main__":
    unittest.main()
