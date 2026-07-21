import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bsc_audit.cli import main
from bsc_audit.provenance import ZERO_SHA256, sha256_bytes


class AdapterReceiptTests(unittest.TestCase):
    def invoke(self, path: Path) -> tuple[int, dict]:
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["adapter", str(path)])
        return status, json.loads(output.getvalue())

    def make_receipt(self, root: Path, kind: str = "lean4") -> dict:
        contents = {
            "job.json": b'{"obligation":"fixture"}\n',
            "subject.txt": b"fixture theorem\n",
            "environment.json": b'{"toolchain":"pinned"}\n',
            "certificate.txt": b"checked certificate\n",
            "stdout.txt": b"accepted\n",
            "stderr.txt": b"",
        }
        for name, content in contents.items():
            (root / name).write_bytes(content)

        formats = {"lean4": "lean4-kernel-check", "smtlib2": "alethe", "interval": "exact-interval-replay"}
        tokens = {"lean4": "accepted", "smtlib2": "unsat", "interval": "enclosed"}
        relation = "same_kernel" if kind == "lean4" else "independent_checker"

        def artifact(name: str) -> dict:
            return {"artifact": name, "sha256": sha256_bytes(contents[name])}

        return {
            "receipt_version": "0.1.0",
            "authority": "non_admissive_preview",
            "receipt_id": f"bsc:adapter:test:{kind}",
            "claim_id": "bsc:claim:test",
            "adapter": {
                "kind": kind,
                "name": f"fixture-{kind}",
                "version": "1.0.0",
                "executable_sha256": sha256_bytes(f"{kind}-adapter".encode()),
            },
            "job": artifact("job.json"),
            "subject": artifact("subject.txt"),
            "environment": artifact("environment.json"),
            "execution": {
                "argv": [f"fixture-{kind}", "subject.txt"],
                "exit_code": 0,
                "transcript": {"stdout": artifact("stdout.txt"), "stderr": artifact("stderr.txt")},
            },
            "certificate": {**artifact("certificate.txt"), "format": formats[kind]},
            "verification": {
                "checker": {
                    "name": f"fixture-{kind}-checker",
                    "version": "1.0.0",
                    "executable_sha256": sha256_bytes(f"{kind}-checker".encode()),
                },
                "checker_relation": relation,
                "replay_verified": True,
                "assumption_policy": {"allowed": [], "observed": []},
            },
            "result_token": tokens[kind],
            "outcome": "pass",
        }

    def write_receipt(self, root: Path, receipt: dict) -> Path:
        path = root / "receipt.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return path

    def test_each_registered_kind_can_bind_a_nonadmissive_receipt(self):
        for kind in ("lean4", "smtlib2", "interval"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                status, payload = self.invoke(self.write_receipt(root, self.make_receipt(root, kind)))
            codes = {finding["code"] for finding in payload["findings"]}
            self.assertEqual(status, 0)
            self.assertEqual(payload["decision"], "no_blocking_findings_with_warnings")
            self.assertIn("ADAPTER_RECEIPT_BOUND", codes)
            self.assertIn("ADAPTER_RECEIPT_NON_ADMISSIVE", codes)

    def test_hash_substitution_blocks_the_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_receipt(root)
            receipt["certificate"]["sha256"] = sha256_bytes(b"different")
            status, payload = self.invoke(self.write_receipt(root, receipt))
        self.assertEqual(status, 1)
        self.assertIn("ADAPTER_ARTIFACT_UNVERIFIED", {finding["code"] for finding in payload["findings"]})

    def test_pass_consistency_gates_fail_closed(self):
        mutations = (
            ("nonzero exit", lambda value: value["execution"].update(exit_code=1), "ADAPTER_PASS_EXIT_MISMATCH"),
            ("wrong token", lambda value: value.update(result_token="unknown"), "ADAPTER_PASS_TOKEN_MISMATCH"),
            ("missing replay", lambda value: value["verification"].update(replay_verified=False), "ADAPTER_REPLAY_MISSING"),
            (
                "undeclared assumption",
                lambda value: value["verification"]["assumption_policy"].update(observed=["Fixture.axiom"]),
                "ADAPTER_UNDECLARED_ASSUMPTION",
            ),
        )
        for name, mutate, code in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                receipt = self.make_receipt(root)
                mutate(receipt)
                status, payload = self.invoke(self.write_receipt(root, receipt))
            self.assertEqual(status, 1)
            self.assertIn(code, {finding["code"] for finding in payload["findings"]})

    def test_smt_and_interval_passes_require_independent_checkers(self):
        for kind in ("smtlib2", "interval"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                receipt = self.make_receipt(root, kind)
                receipt["verification"]["checker_relation"] = "same_kernel"
                status, payload = self.invoke(self.write_receipt(root, receipt))
            self.assertEqual(status, 1)
            self.assertIn("ADAPTER_INDEPENDENT_CHECKER_REQUIRED", {finding["code"] for finding in payload["findings"]})

    def test_cross_kind_result_token_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_receipt(root, "lean4")
            receipt["result_token"] = "unsat"
            status, payload = self.invoke(self.write_receipt(root, receipt))
        self.assertEqual(status, 1)
        self.assertIn("ADAPTER_RESULT_TOKEN_KIND_MISMATCH", {finding["code"] for finding in payload["findings"]})

    def test_tool_hash_placeholders_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_receipt(root)
            receipt["adapter"]["executable_sha256"] = ZERO_SHA256
            status, payload = self.invoke(self.write_receipt(root, receipt))
        self.assertEqual(status, 1)
        self.assertIn("ADAPTER_TOOL_HASH_PLACEHOLDER", {finding["code"] for finding in payload["findings"]})

    def test_preview_authority_cannot_be_elevated_by_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_receipt(root)
            receipt["authority"] = "theorem_gate"
            status, payload = self.invoke(self.write_receipt(root, receipt))
        self.assertEqual(status, 2)
        self.assertEqual(payload["decision"], "prohibited")
        self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

    def test_parent_path_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_receipt(root)
            receipt["subject"]["artifact"] = "../subject.txt"
            status, payload = self.invoke(self.write_receipt(root, receipt))
        self.assertEqual(status, 1)
        self.assertIn("ADAPTER_ARTIFACT_UNVERIFIED", {finding["code"] for finding in payload["findings"]})


if __name__ == "__main__":
    unittest.main()
