# Sharing and Release Guide

The v0.3.0-alpha.7 release is a research preview. Every public description should preserve that status and link to a worked positive and negative example.

## Public surfaces

1. **The official Custom GPT is the direct audit interface.** It is already built and link-shared; its runtime identity and Preview-validation state are reported separately.
2. **GitHub Pages is the local browser interface.** The English Packet Builder and Return Desk are deployed. The Japanese route is a candidate pending public deployment and must not be described as live until its post-deploy smoke check passes.
3. **GitHub is the reproducible workshop.** Source history, issues, pull requests, fixtures, configuration packages, and active releases live there.
4. **Zenodo is the immutable archive.** Frozen software releases and foundations papers receive separate citable records linked in both directions.

## Existing v0.3.0-alpha.7 release contents

The immutable `v0.3.0-alpha.7` tag already exists. Its release contains:

- `START_HERE.txt`, `BSC_AUDIT_COPY_PASTE.txt`, `BSC_AUDIT_UPLOAD_TO_LLM.txt`, and `BSC_AUDIT_SYSTEM_PROMPT.txt`;
- the canonical LLM packet, schema, example archive, and `BSC_AUDIT_PUBLICATION.json`;
- `BSC_CUSTOM_GPT_PACKAGE_0.3.0-alpha.7.zip`, the deterministic Custom GPT editor, Knowledge, evaluation, manifest, and checksum package;
- `bsc-audit-complete.zip` and `bsc-audit-engine-0.3.0-alpha.7.zip`;
- the wheel and source distribution;
- the conformance packet;
- `RELEASE_MANIFEST.json` and `SBOM.spdx.json`;
- `SHA256SUMS`;
- GitHub's automatically generated source archives.

Do not place the research PDF or its DOCX source inside the Apache-2.0 software bundle. Archive them as a separate CC BY 4.0 publication using `research/zenodo.json`.

GitHub generates `Source code (zip)` and `Source code (tar.gz)` from the
complete tagged tree. Unlike the custom software bundle, those automatic
archives include the tracked `research/` PDF and DOCX. Their
`research/LICENSE` applies to those paths; the root Apache-2.0 license does not
replace it.

Do not manually zip a working directory containing caches or untracked files. Build from the tagged tree. Preserve the existing `v0.2.1` and `v0.3.0-alpha.7` tags rather than moving either one.

Permanent release links:

```text
https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.7
https://raw.githubusercontent.com/jkolantree/octo/v0.3.0-alpha.7/BSC_AUDIT_LLM_PACKET.md
https://jkolantree.github.io/octo/
https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor
```

The planned Japanese Pages URL is `https://jkolantree.github.io/octo/ja.html`. It is not a permanent public route until the candidate is deployed and the English page, Japanese page, and protocol metadata all pass the post-deploy smoke check.

The repository release publishes a reproducible package, not proof of the authenticated Custom GPT state. The official GPT's availability, exact observed binding, Preview validation, GitHub release, and Pages deployment are recorded separately in [CUSTOM_GPT_STATUS.md](CUSTOM_GPT_STATUS.md). Lead with the existing official service; present the package as its reproducible source and optional fork/update path. Never infer live or validated state from a release ZIP. A changed package remains an **unvalidated candidate** until its own complete Preview gate passes. The package contains no GPT Action, hosted API, account, analytics, or cloud-storage service.

## Reproduce the Custom GPT package

From the exact clean tagged tree, regenerate and verify the committed package before building the release archive:

```bash
python scripts/build_gpt_package.py
python scripts/build_gpt_package.py --check
python scripts/check_gpt_package.py
python scripts/check_localization.py
python scripts/build_release.py --output release
```

The generator uses the repository's reproducible `SOURCE_DATE_EPOCH` convention, sorted archive members, normalized timestamps, fixed file modes, strict manifests, and SHA-256 ledgers. On the exact clean tag, the official release builder injects the Git commit, tree, and tag into the standalone GPT archive's inner manifest, then binds the archive again in `RELEASE_MANIFEST.json` and the outer `SHA256SUMS`. Compare the final archive hash with that ledger before upload; do not substitute a manually zipped working directory.

## Zenodo records

Use separate related records:

- **Software:** the frozen GitHub release, Apache-2.0.
- **Publication or preprint:** the mathematical foundations paper under its declared document license.

Add reciprocal `isSupplementTo`/`isSupplementedBy` or equivalent relations and include the final repository URL in both `CITATION.cff` and `.zenodo.json`.

The creator identity remains **J. Tree** unless the maintainer deliberately updates it. Do not invent an ORCID, institution, or endorsement.

Run `python scripts/check_privacy.py --protected-history HEAD` before publication. The
checker rejects personal contact information, unapproved document authors,
local paths, secrets, unsafe archives, detailed publication-tool fingerprints,
and non-noreply commit addresses.

## What a trustworthy audit release contains

```text
audit-name/
  README.md
  target/
  claim.json
  source-coverage.json
  human-report.md
  checker-output.json
  counterexamples/
  environment.txt
  SHA256SUMS
```

The README states:

- exact frozen claim;
- research verdict and reviewer;
- evidence maturity and deployment status;
- engine and schema version;
- commands and expected exit codes;
- checks run and not run;
- unresolved evidence;
- first demotion condition.

## Audience routes

The three product entry points have different trust and privacy boundaries:

1. **Official Custom GPT - direct ChatGPT audit:** the link-shared GPT is live and reports alpha.8.dev0, while its complete post-update Preview gate remains pending. Uploads go through ChatGPT under the user's applicable settings and terms.
2. **Local browser Packet Builder and Audit Return Desk:** the deployed English interface constructs packets and inspects returned envelopes and selected hashes locally. The Japanese interface remains a candidate pending public deployment. Sending a packet to a model is a separate action.
3. **Repository and Python engine - exact checker route:** runs the versioned finite checker and preserves structured output; it does not turn an interpretive GPT audit into mechanical evidence retroactively.

### Curious reader

Share [START_HERE.md](../START_HERE.md) and one small worked audit. Do not begin with the full mathematical framework.

### Programmer

Share the tagged repository and [PROGRAMMER_TUTORIAL.md](PROGRAMMER_TUTORIAL.md). Ask for the exact manifest, JSON output, version, and minimal counterexample in any report.

### LLM user

Share the official URL with its exact [status record](CUSTOM_GPT_STATUS.md). The current GPT is available but must not be described as alpha.8 Preview-validated. Share the [deterministic package](../gpt/README.md) as the open-source reproduction, evaluation, update, and fork route, or share the versioned [BSC_AUDIT_LLM_PACKET.md](../BSC_AUDIT_LLM_PACKET.md) for manual cross-model use. Never invent a GPT URL or invite a user to upload confidential material casually. ChatGPT uploads are not local-only.

### Scientific reviewer

Share a frozen target, source-coverage ledger, manifest, actual checker output, certificates, hashes, and human report. Do not ask the reviewer to reconstruct which branch or prompt produced the claim.

## Release checklist

- [ ] A clean checkout passes documented commands on supported Python versions.
- [ ] `bsc-audit --version`, package metadata, citation metadata, and release notes agree.
- [ ] Manifest schema and compatibility table are present.
- [ ] All CLI failures remain structured JSON with documented exit codes.
- [ ] Positive and adversarial fixtures have documented expected outcomes.
- [ ] Links and evidence identifiers resolve.
- [ ] No placeholder owners, hashes, repository URLs, or proof identifiers remain in release examples presented as complete.
- [ ] Full license text and contribution-license statement are present.
- [ ] Accessibility checks cover language, heading order, keyboard focus, narrow view, and 200% zoom.
- [ ] Japanese translations and locale catalogs pass their source-hash freshness manifest; canonical machine tokens remain unchanged.
- [ ] LLM packet covers prompt injection, privacy, source coverage, and fabricated execution.
- [ ] The version-matched `BSC_CUSTOM_GPT_PACKAGE_<VERSION>.zip` regenerates byte-for-byte, passes the package checker, and matches that release's checksum ledger.
- [ ] A changed Custom GPT package is labeled as an unvalidated candidate until its authenticated setup and complete Preview gate pass; live URL, observed binding, and validation status are recorded separately.
- [ ] Apps and Actions remain absent, and the package does not imply a hosted checker API.
- [ ] `SECURITY.md`, governance, issue forms, and conduct policy are linked.
- [ ] SHA-256 sums are generated from final assets.
- [ ] A negative result or known limitation is visible in release notes.

## Public wording

Preferred:

> BSC Audit Engine is experimental research software that checks selected structural obligations and emits finite witnesses. It does not certify arbitrary scientific truth or authorize deployment.

Avoid:

- “truth engine”;
- “automated peer review”;
- “formally verified science” unless a named formal system actually supplies the proof;
- “BSC compliant”;
- claims that an LLM ran the Python checker without actual output.

The Audit Return Desk is implemented in the alpha.8 release candidate for non-admissive inspection of returned output and receipts. It is not part of the immutable alpha.7 release; its presence in a Pages or GPT interface does not turn a returned draft into admissible evidence.
