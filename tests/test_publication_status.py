from __future__ import annotations

import hashlib
import json
import re
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "PUBLICATION_STATUS.json"
PROFILE_PATH = ROOT / "gpt" / "_source" / "GPT_PROFILE.json"
PROTOCOL_META_PATH = ROOT / "pages" / "protocol" / "meta.js"
HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
OFFICIAL_GPT_URL = "https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor"


class PublicationStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))

    def test_snapshot_has_closed_top_level_contract(self) -> None:
        self.assertEqual(
            set(self.status),
            {
                "schema",
                "observed_at_utc",
                "status_is_a_timestamped_snapshot",
                "official_custom_gpt",
                "github_main",
                "github_pages",
                "latest_github_release",
                "next_repository_candidate",
                "interpretation",
            },
        )
        self.assertEqual(self.status["schema"], "bsc-publication-status-v1")
        self.assertIs(self.status["status_is_a_timestamped_snapshot"], True)
        datetime.strptime(self.status["observed_at_utc"], "%Y-%m-%dT%H:%M:%SZ")

    def test_hashes_and_urls_are_well_formed(self) -> None:
        gpt = self.status["official_custom_gpt"]
        main = self.status["github_main"]
        pages = self.status["github_pages"]
        release = self.status["latest_github_release"]
        self.assertRegex(gpt["observed_profile_sha256"], HEX_64)
        for value in (main["commit"], main["tree"], pages["deployed_commit"], release["commit"]):
            self.assertRegex(value, HEX_40)
        for value in (
            gpt["url"],
            main["merged_pull_request"],
            main["exact_audit"]["run"],
            pages["url"],
            pages["japanese_route"]["url"],
            pages["publish_workflow"]["run"],
            release["url"],
        ):
            parsed = urlparse(value)
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(parsed.netloc)

        self.assertEqual(gpt["url"], OFFICIAL_GPT_URL)
        self.assertEqual(urlparse(gpt["url"]).netloc, "chatgpt.com")

    def test_snapshot_timestamp_covers_every_nested_observation(self) -> None:
        snapshot = datetime.strptime(self.status["observed_at_utc"], "%Y-%m-%dT%H:%M:%SZ")

        def observed_times(value: object) -> list[datetime]:
            if isinstance(value, dict):
                times: list[datetime] = []
                for key, nested in value.items():
                    if key == "observed_at_utc" and isinstance(nested, str):
                        times.append(datetime.strptime(nested, "%Y-%m-%dT%H:%M:%SZ"))
                    else:
                        times.extend(observed_times(nested))
                return times
            if isinstance(value, list):
                return [item for nested in value for item in observed_times(nested)]
            return []

        for observed in observed_times(self.status):
            self.assertLessEqual(observed, snapshot)

    def test_live_availability_is_not_conflated_with_validation(self) -> None:
        gpt = self.status["official_custom_gpt"]
        self.assertEqual(gpt["availability"], "live")
        self.assertEqual(gpt["runtime_identity_smoke"], "pass")
        self.assertIn(
            gpt["complete_preview_gate_for_observed_version"],
            {"not_completed", "pass_39_of_39"},
        )
        self.assertIs(self.status["interpretation"]["live_does_not_mean_preview_validated"], True)
        self.assertIs(self.status["interpretation"]["source_ci_does_not_mean_custom_gpt_preview_validated"], True)

    def test_candidate_and_observed_live_identities_follow_the_validation_state(self) -> None:
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        candidate_version = self.status["next_repository_candidate"]["version"]
        self.assertEqual(candidate_version, profile["product"]["canonical_protocol_version"])
        metadata = PROTOCOL_META_PATH.read_text(encoding="utf-8")
        self.assertIn(f'"version":"{candidate_version}"', metadata)
        observed = self.status["official_custom_gpt"]
        gate = observed["complete_preview_gate_for_observed_version"]
        if gate == "pass_39_of_39":
            self.assertEqual(observed["observed_controller_version"], candidate_version)
            self.assertEqual(
                observed["observed_profile_sha256"],
                hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest(),
            )

    def test_japanese_pages_state_is_internally_consistent(self) -> None:
        route = self.status["github_pages"]["japanese_route"]
        self.assertEqual(route["url"], "https://jkolantree.github.io/octo/ja.html")
        datetime.strptime(route["observed_at_utc"], "%Y-%m-%dT%H:%M:%SZ")
        deployment = self.status["next_repository_candidate"]["japanese_pages_deployment"]
        self.assertIn(route["state"], {"candidate_not_deployed", "deployed"})
        if route["state"] == "candidate_not_deployed":
            self.assertEqual(route["observed_http_status"], 404)
            self.assertEqual(deployment, "pending")
        else:
            self.assertEqual(route["observed_http_status"], 200)
            self.assertEqual(deployment, "deployed")
            self.assertEqual(
                self.status["github_pages"]["deployed_commit"],
                self.status["github_main"]["commit"],
            )
        self.assertIs(self.status["interpretation"]["candidate_source_does_not_mean_pages_deployed"], True)

    def test_public_docs_lead_with_official_gpt_and_link_status(self) -> None:
        public_url = self.status["official_custom_gpt"]["url"]
        reproduction_markers = {
            "README.md": "The repository contains the deterministic package lineage",
            "START_HERE.md": "The repository's [Custom GPT package]",
            "docs/index.md": "The repository also contains the deterministic package",
            "docs/CUSTOM_GPT_STATUS.md": "This repository is the reproducible source",
        }
        for relative, reproduction_marker in reproduction_markers.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(public_url, text, relative)
            self.assertLess(text.index(public_url), text.index(reproduction_marker), relative)
        self.assertIn("docs/PUBLICATION_STATUS.json", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("PUBLICATION_STATUS.json", (ROOT / "docs" / "CUSTOM_GPT_STATUS.md").read_text(encoding="utf-8"))

        required_positioning = {
            "README.md": "The repository contains the deterministic package lineage used to configure and evaluate the official GPT",
            "START_HERE.md": "It is already built and link-shared as a research preview",
            "docs/index.md": "is built and link-shared",
            "docs/CUSTOM_GPT_STATUS.md": "is built and link-shared as a research preview",
            "SHARE_THIS.md": "Lead with the existing official GPT for a direct audit",
        }
        for relative, phrase in required_positioning.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(public_url, text, relative)
            self.assertIn(phrase, text, relative)

    def test_public_docs_match_the_observed_japanese_pages_state(self) -> None:
        route = self.status["github_pages"]["japanese_route"]
        if route["state"] == "deployed":
            for relative in (
                "README.md",
                "START_HERE.md",
                "docs/index.md",
                "docs/CUSTOM_GPT_STATUS.md",
                "docs/SHARING_GUIDE.md",
                "SHARE_THIS.md",
            ):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn(route["url"], text, relative)
                self.assertNotIn("candidate pending public deployment", text, relative)
            return

        required_pending_language = {
            "README.md": "pending public deployment",
            "START_HERE.md": "pending public deployment",
            "docs/index.md": "pending public deployment",
            "docs/CUSTOM_GPT_STATUS.md": "candidate; not deployed",
            "docs/SHARING_GUIDE.md": "candidate pending public deployment",
            "SHARE_THIS.md": "candidate pending public deployment",
        }
        for relative, phrase in required_pending_language.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(phrase, text, relative)


if __name__ == "__main__":
    unittest.main()
