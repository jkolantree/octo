import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.check_research_packet import PACKET, verify_packet


class ResearchPacketTests(unittest.TestCase):
    def update_ledger(self, packet: Path, replacements: dict[str, str]) -> None:
        ledger = packet / "DIGESTS.sha256"
        lines = []
        for line in ledger.read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            lines.append(f"{replacements.get(name, digest)}  {name}")
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    def test_preserved_packet_and_internal_records_verify(self):
        self.assertEqual(verify_packet(), [])

    def test_packet_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "packet"
            shutil.copytree(PACKET, copy)
            target = copy / "verification" / "derived_holonomy_report.json"
            target.write_bytes(target.read_bytes() + b" ")
            failures = verify_packet(copy)
        self.assertTrue(any("digest mismatch" in failure for failure in failures))

    def test_semantic_certificate_tampering_fails_with_updated_digests(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "packet"
            shutil.copytree(PACKET, copy)
            report_path = copy / "verification" / "derived_holonomy_report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["cases"][0]["certificate"]["x"] = ["2"]
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()

            provenance_path = copy / "PROVENANCE.json"
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            for record in provenance["imports"]:
                if record["path"] == "verification/derived_holonomy_report.json":
                    record["sha256"] = report_hash
            provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            provenance_hash = hashlib.sha256(provenance_path.read_bytes()).hexdigest()
            self.update_ledger(
                copy,
                {
                    "PROVENANCE.json": provenance_hash,
                    "verification/derived_holonomy_report.json": report_hash,
                },
            )
            failures = verify_packet(copy)
        self.assertIn("derived report certificate replay failed at case 0", failures)


if __name__ == "__main__":
    unittest.main()
