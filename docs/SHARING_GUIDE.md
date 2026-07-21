# Sharing and Release Guide

The v0.3.0-alpha.4 release is a research preview. Every public description should preserve that status and link to a worked positive and negative example.

## Two public surfaces

1. **GitHub is the living workshop.** Source history, issues, pull requests, fixtures, and active releases live there.
2. **Zenodo is the immutable archive.** Frozen software releases and foundations papers receive separate citable records linked in both directions.

## GitHub release contents

Create tag `v0.3.0-alpha.4` and attach:

- `START_HERE.txt`, `BSC_AUDIT_COPY_PASTE.txt`, `BSC_AUDIT_UPLOAD_TO_LLM.txt`, and `BSC_AUDIT_SYSTEM_PROMPT.txt`;
- the canonical LLM packet, schema, example archive, and `BSC_AUDIT_PUBLICATION.json`;
- `bsc-audit-complete.zip` and `bsc-audit-engine-0.3.0-alpha.4.zip`;
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

Do not manually zip a working directory containing caches or untracked files. Build from the tagged tree. Preserve the prior `v0.2.1` tag rather than moving it.

Permanent release links:

```text
https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.4
https://raw.githubusercontent.com/jkolantree/octo/v0.3.0-alpha.4/BSC_AUDIT_LLM_PACKET.md
https://jkolantree.github.io/octo/
```

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

### Curious reader

Share [START_HERE.md](../START_HERE.md) and one small worked audit. Do not begin with the full mathematical framework.

### Programmer

Share the tagged repository and [PROGRAMMER_TUTORIAL.md](PROGRAMMER_TUTORIAL.md). Ask for the exact manifest, JSON output, version, and minimal counterexample in any report.

### LLM user

Share the versioned [BSC_AUDIT_LLM_PACKET.md](../BSC_AUDIT_LLM_PACKET.md) together with its privacy warning. Never invite a user to upload confidential material casually.

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
- [ ] LLM packet covers prompt injection, privacy, source coverage, and fabricated execution.
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
