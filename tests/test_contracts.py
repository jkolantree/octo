from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bsc_audit  # noqa: E402
from bsc_audit.contracts import (  # noqa: E402
    COMPONENT_CONTRACT,
    PROTOCOL_SHA256,
    PROTOCOL_SHA256_HEX,
    PROTOCOL_VERSION,
    parse_component_contract,
    verify_repository_component_contract,
)
from bsc_audit.census import (  # noqa: E402
    CENSUS_AUTHORITY,
    CENSUS_AUTHORITY_SCOPE,
    CENSUS_GATE_ID,
    CERTIFICATE_VERSION as CENSUS_CERTIFICATE_VERSION,
    LANGUAGE as CENSUS_LANGUAGE,
)
from bsc_audit.theorem import (  # noqa: E402
    CERTIFICATE_VERSION,
    LANGUAGE,
    THEOREM_AUTHORITY,
    THEOREM_AUTHORITY_SCOPE,
    THEOREM_GATE_ID,
)
import build_publication_assets as publication  # noqa: E402
from build_publication_assets import public_version  # noqa: E402


class ComponentContractTests(unittest.TestCase):
    def test_repository_bytes_match_the_package_owned_contract(self) -> None:
        self.assertEqual(verify_repository_component_contract(ROOT), [])
        protocol = (ROOT / COMPONENT_CONTRACT.protocol.source_path).read_bytes()
        self.assertEqual(hashlib.sha256(protocol).hexdigest(), PROTOCOL_SHA256_HEX)
        self.assertEqual(PROTOCOL_SHA256, f"sha256:{PROTOCOL_SHA256_HEX}")

    def test_protocol_identity_is_independent_of_distribution_identity(self) -> None:
        self.assertEqual(PROTOCOL_VERSION, "0.3.0-alpha.13")
        self.assertEqual(public_version(), PROTOCOL_VERSION)
        with mock.patch.object(bsc_audit, "__version__", "99.0.0"):
            self.assertEqual(public_version(), PROTOCOL_VERSION)
        source = (ROOT / "src" / "bsc_audit" / "contracts.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("__version__", source)

    def test_runtime_theorem_identity_matches_component_contract(self) -> None:
        theorem = COMPONENT_CONTRACT.theorem_kernel
        self.assertEqual(CERTIFICATE_VERSION, theorem.certificate_version)
        self.assertEqual(LANGUAGE, theorem.language)
        self.assertEqual(THEOREM_GATE_ID, theorem.gate_id)
        self.assertEqual(THEOREM_AUTHORITY, theorem.authority)
        self.assertEqual(THEOREM_AUTHORITY_SCOPE, theorem.authority_scope)

    def test_runtime_census_identity_matches_component_contract(self) -> None:
        census = COMPONENT_CONTRACT.census_kernel
        self.assertEqual(CENSUS_CERTIFICATE_VERSION, census.certificate_version)
        self.assertEqual(CENSUS_LANGUAGE, census.language)
        self.assertEqual(CENSUS_GATE_ID, census.gate_id)
        self.assertEqual(CENSUS_AUTHORITY, census.authority)
        self.assertEqual(CENSUS_AUTHORITY_SCOPE, census.authority_scope)

    def test_publication_builder_refuses_protocol_byte_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory) / "BSC_AUDIT_LLM_PACKET.md"
            packet.write_bytes(b"drifted protocol\n")
            with mock.patch.object(publication, "PROTOCOL", packet):
                with self.assertRaisesRegex(ValueError, "component contract"):
                    publication.protocol_bytes()

    def test_release_record_contains_components_not_release_identity(self) -> None:
        record = COMPONENT_CONTRACT.release_record()
        self.assertEqual(
            set(record),
            {
                "contract_schema",
                "contract_sha256",
                "census_kernel",
                "protocol",
                "return_contract",
                "theorem_kernel",
            },
        )
        encoded = json.dumps(record, sort_keys=True)
        for forbidden in ("engine_version", "release", "git_tag", "commit"):
            self.assertNotIn(forbidden, encoded)

    def test_contract_parser_rejects_duplicate_and_noncanonical_json(self) -> None:
        canonical = (
            ROOT / "src" / "bsc_audit" / "component_contract.json"
        ).read_bytes()
        duplicate = canonical.replace(
            b'  "contract_schema": "bsc-component-contract/v2",\n',
            (
                b'  "contract_schema": "bsc-component-contract/v2",\n'
                b'  "contract_schema": "bsc-component-contract/v2",\n'
            ),
            1,
        )
        with self.assertRaisesRegex(ValueError, "duplicate component-contract key"):
            parse_component_contract(duplicate)
        with self.assertRaisesRegex(ValueError, "canonical sorted JSON"):
            parse_component_contract(canonical.rstrip(b"\n"))


if __name__ == "__main__":
    unittest.main()
